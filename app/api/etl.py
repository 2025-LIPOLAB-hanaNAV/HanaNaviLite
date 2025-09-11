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
