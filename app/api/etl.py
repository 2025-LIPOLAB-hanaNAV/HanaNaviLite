import logging
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks

from app.core.config import get_upload_dir
from app.etl.pipeline import get_etl_pipeline, ETLPipeline

logger = logging.getLogger(__name__)
router = APIRouter()


def run_etl_background(file_path: str, file_name: str):
    """백그라운드에서 ETL 파이프라인 실행"""
    pipeline = get_etl_pipeline() # 각 백그라운드 태스크에서 새로운 인스턴스 얻기
    logger.info(f"Starting ETL in background for {file_name}")
    try:
        result = pipeline.process_file(file_path, file_name)
        logger.info(f"ETL background task finished for {file_name} with status: {result['status']}")
    except Exception as e:
        logger.error(f"ETL background task failed for {file_name}: {e}", exc_info=True)


@router.post("/etl/upload", status_code=202)
async def upload_and_process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    # pipeline: ETLPipeline = Depends(get_etl_pipeline) # pipeline 인자 제거
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

        # 백그라운드에서 ETL 실행
        background_tasks.add_task(run_etl_background, file_path, file.filename)

        return {
            "message": "File uploaded successfully. Processing started in the background.",
            "file_name": file.filename,
            "file_path": file_path
        }

    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")
