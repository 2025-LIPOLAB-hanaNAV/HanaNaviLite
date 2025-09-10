import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel
from app.core.database import get_db_manager
from app.llm.llm_judge import LLMJudge, get_llm_judge
import structlog

logger = structlog.get_logger()

# 평가 데이터 저장 경로 (임시)
# 업로드된 평가 데이터 파일이 저장될 디렉토리입니다.
EVAL_DATA_DIR = "./eval_data"
os.makedirs(EVAL_DATA_DIR, exist_ok=True)

router = APIRouter()


class EvaluationRunResult(BaseModel):
    """단일 평가 실행 결과"""
    evaluation_id: str
    status: str
    total_items: int
    evaluated_items: int
    overall_score: float
    details_file: Optional[str]
    created_at: str


@router.post("/upload_data", response_model=Dict[str, str])
async def upload_evaluation_data(
    file: UploadFile = File(..., description="평가 데이터 파일 (JSONL 또는 CSV)")
):
    """
    평가 데이터를 업로드합니다.
    """
    try:
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in [".jsonl", ".csv"]:
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. JSONL 또는 CSV 파일을 업로드해주세요.")

        file_id = str(uuid.uuid4())
        file_path = os.path.join(EVAL_DATA_DIR, f"{file_id}{file_extension}")

        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024):
                buffer.write(chunk)
        
        # 데이터베이스에 파일 정보 저장 (선택적)
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_settings (key, value, description)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value, description = EXCLUDED.description
            """, (f"eval_data_{file_id}", file_path, f"Uploaded evaluation data: {file.filename}"))
            conn.commit()

        logger.info(f"Evaluation data uploaded: {file.filename} to {file_path}")
        return {"message": "파일이 성공적으로 업로드되었습니다.", "file_id": file_id, "file_path": file_path}
    except Exception as e:
        logger.error(f"Failed to upload evaluation data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"평가 데이터 업로드 중 오류 발생: {e}")


@router.post("/run_evaluation", response_model=EvaluationRunResult)
async def run_evaluation(
    background_tasks: BackgroundTasks,
    file_id: str = Query(..., description="업로드된 평가 데이터의 파일 ID"),
    judge: LLMJudge = Depends(get_llm_judge)
):
    """
    업로드된 평가 데이터에 대해 LLM Judge 평가를 실행합니다.
    """
    db_manager = get_db_manager()
    
    # 파일 경로 조회
    file_path = db_manager.get_setting(f"eval_data_{file_id}")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="평가 데이터 파일을 찾을 수 없습니다.")

    evaluation_id = str(uuid.uuid4())
    details_file_path = os.path.join(EVAL_DATA_DIR, f"results_{evaluation_id}.jsonl")

    # 평가 실행 정보를 DB에 저장
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_settings (key, value, description)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value, description = EXCLUDED.description
        """, (f"evaluation_run_{evaluation_id}", json.dumps({
            "file_id": file_id,
            "file_path": file_path,
            "status": "pending",
            "total_items": 0,
            "evaluated_items": 0,
            "overall_score": 0.0,
            "details_file": details_file_path,
            "created_at": datetime.now().isoformat()
        }), f"LLM Judge Evaluation Run: {evaluation_id}"))
        conn.commit()

    # 백그라운드에서 평가 실행
    background_tasks.add_task(
        _perform_evaluation_task,
        file_path,
        details_file_path,
        evaluation_id,
        judge,
        db_manager
    )

    return EvaluationRunResult({
        "evaluation_id": evaluation_id,
        "status": "pending",
        "total_items": 0,
        "evaluated_items": 0,
        "overall_score": 0.0,
        "details_file": details_file_path,
        "created_at": datetime.now().isoformat()
    })


@router.get("/results", response_model=List[EvaluationRunResult])
async def get_evaluation_results():
    """
    모든 평가 실행 결과를 조회합니다.
    """
    db_manager = get_db_manager()
    results = []
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'evaluation_run_%'")
        for row in cursor.fetchall():
            run_data = json.loads(row[1])
            results.append(EvaluationRunResult(run_data))
    return results


@router.get("/results/{evaluation_id}", response_model=EvaluationRunResult)
async def get_evaluation_details(evaluation_id: str):
    """
    특정 평가 실행의 상세 결과를 조회합니다.
    """
    db_manager = get_db_manager()
    run_data_str = db_manager.get_setting(f"evaluation_run_{evaluation_id}")
    if not run_data_str:
        raise HTTPException(status_code=404, detail="평가 실행을 찾을 수 없습니다.")
    
    run_data = json.loads(run_data_str)
    return EvaluationRunResult(run_data)


async def _perform_evaluation_task(
    file_path: str,
    details_file_path: str,
    evaluation_id: str,
    judge: LLMJudge,
    db_manager
):
    """
    백그라운드에서 실제 평가를 수행하는 함수.
    업로드된 평가 데이터 파일을 읽어 각 항목에 대해 LLM Judge 평가를 실행하고 결과를 저장합니다.
    """
    logger.info(f"Starting background evaluation task for {evaluation_id}")
    total_items = 0
    evaluated_items = 0
    sum_scores = 0.0
    
    try:
        # 평가 데이터 로드 (JSONL 또는 CSV 형식 지원)
        data_to_evaluate = []
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == ".jsonl":
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    data_to_evaluate.append(json.loads(line))
        elif file_extension == ".csv":
            import pandas as pd
            df = pd.read_csv(file_path)
            data_to_evaluate = df.to_dict(orient="records")
        
        total_items = len(data_to_evaluate)
        
        # 상세 평가 결과를 저장할 파일 열기
        with open(details_file_path, "w", encoding="utf-8") as details_f:
            for item in data_to_evaluate:
                user_query = item.get("query", "")
                llm_answer = item.get("answer", "")
                context = item.get("context", [])
                ground_truth = item.get("ground_truth")
                
                evaluation_result = await judge.evaluate_answer(
                    user_query, llm_answer, context, ground_truth
                )
                
                details_f.write(json.dumps(evaluation_result, ensure_ascii=False) + "\n")
                
                evaluated_items += 1
                sum_scores += evaluation_result.get("overall_score", 0.0)
                
                # 진행 상황 업데이트
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE system_settings
                        SET value = ?
                        WHERE key = ?
                    """, (json.dumps({
                        "file_id": os.path.basename(file_path).split('.')[0],
                        "file_path": file_path,
                        "status": "in_progress",
                        "total_items": total_items,
                        "evaluated_items": evaluated_items,
                        "overall_score": sum_scores / evaluated_items if evaluated_items > 0 else 0.0,
                        "details_file": details_file_path,
                        "created_at": datetime.now().isoformat()
                    }), f"evaluation_run_{evaluation_id}"))
                    conn.commit()
        
        # 최종 상태 업데이트
        final_status = "completed"
        overall_score = sum_scores / evaluated_items if evaluated_items > 0 else 0.0
        
    except Exception as e:
        logger.error(f"Background evaluation task failed for {evaluation_id}: {e}", exc_info=True)
        final_status = "failed"
        overall_score = 0.0
        
    finally:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE system_settings
                SET value = ?
                WHERE key = ?
            """, (json.dumps({
                "file_id": os.path.basename(file_path).split('.')[0],
                "file_path": file_path,
                "status": final_status,
                "total_items": total_items,
                "evaluated_items": evaluated_items,
                "overall_score": overall_score,
                "details_file": details_file_path,
                "created_at": datetime.now().isoformat()
            }), f"evaluation_run_{evaluation_id}"))
            conn.commit()
        logger.info(f"Background evaluation task {evaluation_id} finished with status: {final_status}")
