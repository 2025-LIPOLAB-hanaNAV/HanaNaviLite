import logging
from typing import List, Optional, Dict, Any
import asyncio

from app.search.faiss_engine import get_faiss_engine, VectorSearchResult
from app.search.ir_engine import get_ir_engine, IRSearchResult
from app.search.rrf import get_rrf_algorithm, HybridSearchResult
from app.llm.embedding import get_text_embedding
from app.utils.text_processor import get_text_processor
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HybridSearchEngine:
    """
    IR, Vector 검색을 결합한 하이브리드 검색 엔진
    """
    
    def __init__(self):
        self.ir_engine = get_ir_engine()
        self.vector_engine = get_faiss_engine()
        self.rrf_algorithm = get_rrf_algorithm()
        self.text_processor = get_text_processor()
        
        logger.info("Hybrid Search Engine initialized")
    
    async def search(self, query: str, top_k: int = 20, filters: Optional[Dict[str, Any]] = None) -> List[HybridSearchResult]:
        """
        하이브리드 검색 수행
        - 쿼리 정규화
        - IR, Vector 병렬 검색
        - RRF 융합
        """
        try:
            # 1. 쿼리 정규화 및 임베딩 생성
            cleaned_query = self.text_processor.clean_query(query)
            query_embedding = get_text_embedding(query)
            
            # 2. 병렬 검색 실행
            ir_task = asyncio.to_thread(self.ir_engine.search, cleaned_query, top_k * 2, filters=filters)
            vector_task = asyncio.to_thread(self.vector_engine.search, query_embedding, top_k * 2, filter_metadata=filters)
            
            ir_results, vector_results = await asyncio.gather(ir_task, vector_task)
            
            logger.info(f"IR search found {len(ir_results)} results, Vector search found {len(vector_results)} results")
            
            # 3. RRF 융합
            fused_results = self.rrf_algorithm.fuse_results(vector_results, ir_results, top_k)
            
            # 4. (선택적) 다양성 필터링
            # final_results = self.rrf_algorithm.get_diversity_filtered_results(fused_results)
            final_results = fused_results
            
            logger.info(f"Hybrid search completed with {len(final_results)} results for query: '{query}'")
            return final_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed for query '{query}': {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """검색 엔진 통계 정보 반환"""
        return {
            "ir_engine_stats": self.ir_engine.get_stats(),
            "vector_engine_stats": self.vector_engine.get_stats(),
            "rrf_stats": self.rrf_algorithm.get_stats()
        }


# 전역 인스턴스 (싱글톤 패턴)
_hybrid_engine: Optional[HybridSearchEngine] = None


def get_hybrid_search_engine() -> HybridSearchEngine:
    """하이브리드 검색 엔진 싱글톤 인스턴스 반환"""
    global _hybrid_engine
    if _hybrid_engine is None:
        _hybrid_engine = HybridSearchEngine()
    return _hybrid_engine
