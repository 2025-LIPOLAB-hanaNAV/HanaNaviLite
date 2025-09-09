#!/usr/bin/env python3
"""
관리자 도구 API
문서 재색인, 시스템 관리 기능 등을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import Dict, Any, List, Optional
import logging

from app.core.database import get_db_manager
from app.etl.pipeline import ETLPipeline, get_etl_pipeline
from app.search.faiss_engine import get_faiss_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reindex_documents")
async def reindex_documents(
    background_tasks: BackgroundTasks,
    document_ids: Optional[List[int]] = Query(None, description="재색인할 문서 ID 목록 (없으면 모든 문서)"),
    etl_pipeline: ETLPipeline = Depends(get_etl_pipeline)
):
    """
    문서를 재색인합니다. (백그라운드 작업)
    지정된 문서 ID에 해당하는 문서를 다시 파싱, 임베딩, 인덱싱합니다.
    document_ids가 제공되지 않으면 모든 문서를 재색인합니다.
    """
    try:
        # 비동기적으로 재색인 작업 시작
        background_tasks.add_task(etl_pipeline.reindex_documents, document_ids)
        
        message = "모든 문서 재색인 작업이 시작되었습니다." if not document_ids \
            else f"{len(document_ids)}개 문서 재색인 작업이 시작되었습니다."
        
        return {"message": message, "status": "processing"}
    except Exception as e:
        logger.error(f"Failed to start reindexing: {e}")
        raise HTTPException(status_code=500, detail=f"재색인 시작 중 오류 발생: {e}")


@router.post("/clear_cache")
async def clear_cache():
    """
    검색 캐시 및 FAISS 인덱스 캐시를 지웁니다.
    시스템의 캐시된 데이터를 초기화하여 최신 정보를 반영하도록 합니다.
    """
    db_manager = get_db_manager()
    faiss_engine = get_faiss_engine()
    
    try:
        # 데이터베이스 검색 캐시 삭제
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM search_cache")
            conn.commit()
        
        # FAISS 인메모리 캐시 삭제
        faiss_engine.clear_cache()
        
        logger.info("All caches cleared successfully.")
        return {"message": "모든 캐시가 성공적으로 지워졌습니다.", "status": "success"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"캐시 삭제 중 오류 발생: {e}")


@router.get("/system_status", response_model=Dict[str, Any])
async def get_system_status():
    """
    시스템의 현재 상태를 조회합니다.
    데이터베이스 상태, FAISS 인덱스 상태 등 주요 시스템 컴포넌트의 헬스체크 정보를 반환합니다.
    """
    db_manager = get_db_manager()
    faiss_engine = get_faiss_engine()
    
    try:
        db_status = db_manager.health_check()
        faiss_status = faiss_engine.get_stats()
        
        return {
            "database_status": db_status,
            "faiss_status": faiss_status,
            "message": "시스템 상태 조회 성공"
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=f"시스템 상태 조회 중 오류 발생: {e}")


from app.utils.answer_enhancement import AnswerStyleAdjuster, AnswerStyle

@router.post("/summarize", response_model=Dict[str, str])
async def summarize_text(
    text: str = Query(..., description="요약할 텍스트"),
    style: str = Query("executive", description="요약 스타일 (executive, simple 등)")
):
    """
    텍스트를 요약합니다.
    긴 텍스트를 지정된 스타일에 따라 간결하게 요약하여 반환합니다.
    """
    try:
        adjuster = AnswerStyleAdjuster()
        
        if style == "executive":
            styled_answer = adjuster.adjust_answer_style(text, AnswerStyle.EXECUTIVE)
            summary = styled_answer.styled_answer
        elif style == "simple":
            styled_answer = adjuster.adjust_answer_style(text, AnswerStyle.SIMPLE)
            summary = styled_answer.styled_answer
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 요약 스타일입니다. 'executive' 또는 'simple'을 사용하세요.")
        
        return {"summary": summary}
    except Exception as e:
        logger.error(f"Failed to summarize text: {e}")
        raise HTTPException(status_code=500, detail=f"텍스트 요약 중 오류 발생: {e}")


from app.llm.question_generator import get_question_generator, QuestionGenerator

@router.post("/generate_questions", response_model=Dict[str, List[str]])
async def generate_questions(
    text: str = Query(..., description="질문을 생성할 텍스트"),
    num_questions: int = Query(3, ge=1, le=10, description="생성할 질문의 개수"),
    question_generator: QuestionGenerator = Depends(get_question_generator)
):
    """
    주어진 텍스트에서 질문을 자동 생성합니다.
    주어진 텍스트의 내용을 바탕으로 LLM을 사용하여 관련 질문 목록을 생성합니다.
    """
    try:
        questions = await question_generator.generate_questions(text, num_questions)
        return {"questions": questions}
    except Exception as e:
        logger.error(f"Failed to generate questions: {e}")
        raise HTTPException(status_code=500, detail=f"질문 생성 중 오류 발생: {e}")
