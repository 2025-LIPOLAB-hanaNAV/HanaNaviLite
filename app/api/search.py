from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging

from app.search.hybrid_engine import get_hybrid_search_engine, HybridSearchResult, HybridSearchEngine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search/hybrid", response_model=List[HybridSearchResult])
async def hybrid_search(
    query: str = Query(..., description="검색할 쿼리 문자열"),
    top_k: int = Query(20, description="반환할 결과의 최대 개수"),
    filters: Optional[Dict[str, Any]] = None,
    engine: HybridSearchEngine = Depends(get_hybrid_search_engine)
):
    """
    하이브리드 검색을 수행합니다.
    - **query**: 검색어
    - **top_k**: 반환할 결과 수
    - **filters**: 검색 필터 (JSON 형식)
    """
    try:
        results = await engine.search(query, top_k, filters)
        return results
    except Exception as e:
        logger.error(f"Hybrid search API error: {e}")
        raise HTTPException(status_code=500, detail="검색 중 오류가 발생했습니다.")


@router.get("/search/stats", response_model=Dict[str, Any])
async def get_search_stats(engine: HybridSearchEngine = Depends(get_hybrid_search_engine)):
    """
    검색 엔진의 현재 통계 정보를 반환합니다.
    """
    try:
        return engine.get_stats()
    except Exception as e:
        logger.error(f"Failed to get search stats: {e}")
        raise HTTPException(status_code=500, detail="통계 정보 조회 중 오류가 발생했습니다.")
