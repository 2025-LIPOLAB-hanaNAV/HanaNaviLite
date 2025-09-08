from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import logging
import json

from app.llm.rag_pipeline import get_rag_pipeline, RAGPipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/rag/query")
async def rag_query(
    query: str = Query(..., description="사용자 질문"),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> Dict[str, Any]:
    """
    RAG 파이프라인을 통해 사용자 질문에 답변합니다 (스트리밍 미사용).
    """
    try:
        result = await pipeline.query(query)
        return result
    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="답변 생성 중 오류가 발생했습니다.")


async def stream_generator(query: str, pipeline: RAGPipeline):
    """스트리밍 응답을 위한 비동기 제너레이터"""
    try:
        async for chunk in pipeline.stream_query(query):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"RAG stream failed: {e}", exc_info=True)
        error_chunk = {
            "type": "error",
            "data": {"detail": "스트리밍 중 서버 오류 발생"}
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"


@router.post("/rag/stream_query")
async def rag_stream_query(
    query: str = Query(..., description="사용자 질문"),
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """
    RAG 파이프라인을 통해 사용자 질문에 답변합니다 (스트리밍 사용).
    Server-Sent Events (SSE) 형식으로 응답합니다.
    """
    return StreamingResponse(
        stream_generator(query, pipeline),
        media_type="text/event-stream"
    )
