import logging
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request, Query

from app.core.config import get_upload_dir, get_writable_upload_dir, get_settings
from app.etl.pipeline import get_etl_pipeline, ETLPipeline

logger = logging.getLogger(__name__)
router = APIRouter()


def run_etl_background(file_path: str, file_name: str, upload_token: str | None = None, uploader_session_id: str | None = None, uploader_user_id: str | None = None):
    """백그라운드에서 ETL 파이프라인 실행"""
    pipeline = get_etl_pipeline() # 각 백그라운드 태스크에서 새로운 인스턴스 얻기
    logger.info(f"Starting ETL in background for {file_name}")
    try:
        result = pipeline.process_file(file_path, file_name, upload_token=upload_token,
                                       uploader_session_id=uploader_session_id,
                                       uploader_user_id=uploader_user_id)
        logger.info(f"ETL background task finished for {file_name} with status: {result['status']}")
    except Exception as e:
        logger.error(f"ETL background task failed for {file_name}: {e}", exc_info=True)


@router.post("/etl/upload", status_code=202)
async def upload_and_process_file(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    upload_token: str | None = Query(default=None, description="클라이언트 업로드 토큰 (내 문서 필터링용)"),
    uploader_session_id: str | None = Query(default=None),
    uploader_user_id: str | None = Query(default=None),
):
    """
    파일을 업로드하고 백그라운드에서 ETL 처리를 시작합니다.
    """
    # 안정성: 쓰기 가능한 업로드 디렉토리 확보 (여러 후보 시도)
    upload_dir = get_writable_upload_dir()

    # 파일명 정규화 (경로 분리자 제거, 과도한 공백/특수문자 치환)
    import re, uuid
    original_name = os.path.basename(file.filename or 'uploaded')
    # 유지: 확장자
    base, ext = os.path.splitext(original_name)
    safe_base = re.sub(r"[^\w.-]+", "_", base).strip("._") or "file"
    safe_ext = re.sub(r"[^A-Za-z0-9.]+", "", ext)[:10]
    candidate = f"{safe_base}{safe_ext}"
    file_path = os.path.join(upload_dir, candidate)
    # 충돌 시 유니크 보장
    if os.path.exists(file_path):
        candidate = f"{safe_base}_{uuid.uuid4().hex[:8]}{safe_ext}"
        file_path = os.path.join(upload_dir, candidate)

    try:
        # 파일 저장 (사이즈 제한 및 퍼미션 오류 폴백)
        settings = get_settings()
        max_bytes = int(settings.max_file_size_mb * 1024 * 1024)
        written = 0
        try:
            with open(file_path, "wb") as buffer:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise HTTPException(status_code=413, detail="파일이 최대 크기를 초과했습니다.")
                    buffer.write(chunk)
        except PermissionError:
            # 권한 문제 폴백: /tmp 경로로 재시도
            fallback_dir = "/tmp/hananavi_uploads"
            os.makedirs(fallback_dir, exist_ok=True)
            file_path = os.path.join(fallback_dir, candidate)
            with open(file_path, "wb") as buffer:
                await file.seek(0)
                written = 0
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise HTTPException(status_code=413, detail="파일이 최대 크기를 초과했습니다.")
                    buffer.write(chunk)
        logger.info(f"File '{original_name}' uploaded to '{file_path}' ({written} bytes)")

        # 업로드 토큰: 쿼리, 헤더 중 택1
        token = upload_token or request.headers.get('X-Upload-Token')

        # 백그라운드에서 ETL 실행
        background_tasks.add_task(run_etl_background, file_path, file.filename, token, uploader_session_id, uploader_user_id)

        return {
            "message": "File uploaded successfully. Processing started in the background.",
            "file_name": candidate,
            "file_path": file_path,
            "upload_token": token
        }

    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")


@router.get("/etl/status")
async def etl_status(
    upload_token: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200)
):
    """
    최근 업로드/처리 상태 조회. 업로드 토큰으로 내 문서만 필터링 가능.
    """
    from app.core.database import get_db_manager
    dbm = get_db_manager()
    try:
        with dbm.get_connection() as conn:
            cur = conn.cursor()
            sql = """
                SELECT id, file_name, file_type, status, created_at, updated_at, processed_at, upload_token
                  FROM documents
            """
            params: list = []
            if upload_token:
                sql += " WHERE upload_token = ?"
                params.append(upload_token)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            cur.execute(sql, params)
            rows = cur.fetchall()
            data = []
            for r in rows:
                data.append({
                    "id": r[0],
                    "file_name": r[1],
                    "file_type": r[2],
                    "status": r[3],
                    "created_at": r[4],
                    "updated_at": r[5],
                    "processed_at": r[6],
                    "upload_token": r[7],
                })
            return {"items": data}
    except Exception as e:
        logger.error(f"Failed to fetch ETL status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="상태 조회 실패")


@router.get("/etl/documents")
async def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, description="상태 필터: processed, failed, processing")
):
    """
    등록된 문서 목록 조회
    """
    from app.core.database import get_db_manager
    dbm = get_db_manager()
    try:
        with dbm.get_connection() as conn:
            cur = conn.cursor()
            
            # 기본 쿼리
            sql = """
                SELECT id, file_name, file_type, file_size, status, created_at, updated_at, 
                       processed_at, keywords, upload_token, LENGTH(content) as content_length
                FROM documents
            """
            params: list = []
            
            # 상태 필터
            if status_filter:
                sql += " WHERE status = ?"
                params.append(status_filter)
            
            # 정렬 및 페이징
            sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cur.execute(sql, params)
            rows = cur.fetchall()
            
            # 총 개수 조회
            count_sql = "SELECT COUNT(*) FROM documents"
            count_params: list = []
            if status_filter:
                count_sql += " WHERE status = ?"
                count_params.append(status_filter)
            
            cur.execute(count_sql, count_params)
            total_count = cur.fetchone()[0]
            
            documents = []
            for r in rows:
                documents.append({
                    "id": r[0],
                    "file_name": r[1],
                    "file_type": r[2],
                    "file_size": r[3],
                    "status": r[4],
                    "created_at": r[5],
                    "updated_at": r[6],
                    "processed_at": r[7],
                    "keywords": r[8],
                    "upload_token": r[9],
                    "content_length": r[10]
                })
            
            return {
                "documents": documents,
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            }
    except Exception as e:
        logger.error(f"Failed to fetch documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="문서 목록 조회 실패")


@router.get("/etl/documents/{document_id}")
async def get_document_detail(document_id: int):
    """
    특정 문서의 상세 정보 조회
    """
    from app.core.database import get_db_manager
    dbm = get_db_manager()
    try:
        with dbm.get_connection() as conn:
            cur = conn.cursor()
            
            # 문서 정보 조회
            cur.execute("""
                SELECT id, file_name, file_type, file_size, status, created_at, updated_at,
                       processed_at, keywords, upload_token, content, file_path
                FROM documents WHERE id = ?
            """, (document_id,))
            doc_row = cur.fetchone()
            
            if not doc_row:
                raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
            
            # 청크 정보 조회
            cur.execute("""
                SELECT id, chunk_index, LENGTH(content) as chunk_length, created_at
                FROM chunks WHERE document_id = ? ORDER BY chunk_index
            """, (document_id,))
            chunk_rows = cur.fetchall()
            
            chunks = []
            for chunk in chunk_rows:
                chunks.append({
                    "id": chunk[0],
                    "chunk_index": chunk[1],
                    "chunk_length": chunk[2],
                    "created_at": chunk[3]
                })
            
            document = {
                "id": doc_row[0],
                "file_name": doc_row[1],
                "file_type": doc_row[2],
                "file_size": doc_row[3],
                "status": doc_row[4],
                "created_at": doc_row[5],
                "updated_at": doc_row[6],
                "processed_at": doc_row[7],
                "keywords": doc_row[8],
                "upload_token": doc_row[9],
                "content_length": len(doc_row[10]) if doc_row[10] else 0,
                "file_path": doc_row[11],
                "chunks": chunks,
                "chunk_count": len(chunks)
            }
            
            return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="문서 조회 실패")


@router.delete("/etl/documents/{document_id}")
async def delete_document(document_id: int):
    """
    문서 삭제 (DB와 벡터 인덱스에서 제거)
    """
    from app.core.database import get_db_manager
    from app.search.faiss_engine import get_faiss_engine
    
    dbm = get_db_manager()
    faiss_engine = get_faiss_engine()
    
    try:
        with dbm.get_connection() as conn:
            cur = conn.cursor()
            
            # 문서 존재 확인
            cur.execute("SELECT id, file_name FROM documents WHERE id = ?", (document_id,))
            doc_row = cur.fetchone()
            if not doc_row:
                raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
            
            # 청크 ID 목록 조회 (FAISS에서 제거용)
            cur.execute("SELECT chunk_index FROM chunks WHERE document_id = ?", (document_id,))
            chunk_indices = [f"{document_id}_{row[0]}" for row in cur.fetchall()]
            
            # 데이터베이스에서 삭제
            cur.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            cur.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            
            # FAISS 인덱스에서 벡터 제거 (가능한 경우)
            try:
                if chunk_indices:
                    faiss_engine.remove_vectors(chunk_indices)
                    faiss_engine.save_index()
            except Exception as e:
                logger.warning(f"Failed to remove vectors from FAISS: {e}")
            
            return {
                "message": f"Document '{doc_row[1]}' deleted successfully",
                "document_id": document_id,
                "chunks_removed": len(chunk_indices)
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="문서 삭제 실패")


@router.post("/etl/documents/{document_id}/reprocess")
async def reprocess_document(document_id: int, background_tasks: BackgroundTasks):
    """
    문서 재처리
    """
    from app.core.database import get_db_manager
    dbm = get_db_manager()
    
    try:
        with dbm.get_connection() as conn:
            cur = conn.cursor()
            
            # 문서 정보 조회
            cur.execute("""
                SELECT id, file_name, file_path, upload_token, uploader_session_id, uploader_user_id
                FROM documents WHERE id = ?
            """, (document_id,))
            doc_row = cur.fetchone()
            
            if not doc_row:
                raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
            
            # 파일 존재 확인
            file_path = doc_row[2]
            if not os.path.exists(file_path):
                raise HTTPException(status_code=400, detail="원본 파일을 찾을 수 없습니다")
            
            # 기존 데이터 삭제
            cur.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            cur.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            
            # 백그라운드에서 재처리
            background_tasks.add_task(
                run_etl_background, 
                file_path, 
                doc_row[1], 
                doc_row[3],  # upload_token
                doc_row[4],  # uploader_session_id  
                doc_row[5]   # uploader_user_id
            )
            
            return {
                "message": f"Document '{doc_row[1]}' queued for reprocessing",
                "document_id": document_id
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reprocess document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="문서 재처리 실패")
