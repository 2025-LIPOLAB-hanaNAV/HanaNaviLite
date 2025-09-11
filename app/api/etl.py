import logging
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request, Query

from app.core.config import get_upload_dir
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
    upload_dir = get_upload_dir()
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    file_path = os.path.join(upload_dir, file.filename)

    try:
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File '{file.filename}' uploaded to '{file_path}'")

        # 업로드 토큰: 쿼리, 헤더 중 택1
        token = upload_token or request.headers.get('X-Upload-Token')

        # 백그라운드에서 ETL 실행
        background_tasks.add_task(run_etl_background, file_path, file.filename, token, uploader_session_id, uploader_user_id)

        return {
            "message": "File uploaded successfully. Processing started in the background.",
            "file_name": file.filename,
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
