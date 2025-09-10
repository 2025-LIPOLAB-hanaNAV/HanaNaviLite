import logging
import asyncio
import time
from typing import List, Optional, Dict, Any

from app.search.faiss_engine import get_faiss_engine
from app.search.ir_engine import get_ir_engine
from app.search.rrf import get_rrf_algorithm, HybridSearchResult
from app.search.recommendation_engine import get_recommendation_engine
from app.search.planner import get_search_planner
from app.llm.embedding import get_text_embedding
from app.utils.text_processor import get_text_processor
from app.core.performance_tuner import get_performance_tuner

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    IR, Vector 검색을 결합한 하이브리드 검색 엔진
    """
    
    def __init__(self):
        self.ir_engine = get_ir_engine()
        self.vector_engine = get_faiss_engine()
        self.rrf_algorithm = get_rrf_algorithm()
        self.text_processor = get_text_processor()
        self.performance_tuner = get_performance_tuner()
        self.recommendation_engine = get_recommendation_engine()
        self.search_planner = get_search_planner()
        
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

            # 2. 검색 전략 수립
            plan = self.search_planner.plan(query, filters)
            latencies: Dict[str, float] = {}

            async def run_ir():
                start = time.perf_counter()
                result = await asyncio.to_thread(
                    self.ir_engine.search, cleaned_query, top_k * 2, filters=filters
                )
                latencies["ir"] = time.perf_counter() - start
                return result

            async def run_vector():
                start = time.perf_counter()
                result = await asyncio.to_thread(
                    self.vector_engine.search, query_embedding, top_k * 2, filter_metadata=filters
                )
                latencies["vector"] = time.perf_counter() - start
                return result

            tasks = []
            if plan.use_ir:
                tasks.append(run_ir())
            if plan.use_vector:
                tasks.append(run_vector())

            results = await asyncio.gather(*tasks)

            # 결과 매핑
            idx = 0
            ir_results = results[idx] if plan.use_ir else []
            if plan.use_ir:
                idx += 1
            vector_results = results[idx] if plan.use_vector else []

            if plan.use_ir:
                logger.info(
                    f"IR search found {len(ir_results)} results in {latencies.get('ir', 0):.3f}s"
                )
            if plan.use_vector:
                logger.info(
                    f"Vector search found {len(vector_results)} results in {latencies.get('vector', 0):.3f}s"
                )

            # 3. RRF 융합 (가중치는 플래너 결정 사용)
            self.rrf_algorithm.vector_weight = plan.vector_weight
            self.rrf_algorithm.ir_weight = plan.ir_weight
            fused_results = self.rrf_algorithm.fuse_results(
                vector_results,
                ir_results,
                top_k,
                vector_weight=plan.vector_weight,
                ir_weight=plan.ir_weight,
            )

            # 4. 추천 엔진 결과 결합
            recommendation_results: List[HybridSearchResult] = []
            if plan.use_recommendation:
                rec_start = time.perf_counter()
                rec = self.recommendation_engine.get_recommendations(
                    document_id=filters.get("document_id") if filters else None,
                    user_id=filters.get("user_id") if filters else None,
                    recommendation_type="hybrid",
                    top_k=top_k,
                )
                latencies["recommendation"] = time.perf_counter() - rec_start
                for r in rec.recommendations:
                    recommendation_results.append(
                        HybridSearchResult(
                            chunk_id=f"rec-{r.document_id}",
                            document_id=r.document_id,
                            title=r.title,
                            content="",
                            snippet="",
                            vector_score=0.0,
                            ir_score=0.0,
                            fusion_score=r.similarity_score * plan.recommendation_weight,
                            rank=0,
                            metadata={"reason": r.similarity_type},
                            source_types=["recommendation"],
                        )
                    )
                logger.info(
                    f"Recommendation engine returned {len(recommendation_results)} results in {latencies.get('recommendation', 0):.3f}s"
                )

            final_results = fused_results
            if recommendation_results:
                final_results.extend(recommendation_results)
                final_results.sort(key=lambda x: x.fusion_score, reverse=True)
                final_results = final_results[:top_k]

            logger.info(
                f"Hybrid search completed with {len(final_results)} results for query: '{query}'"
            )
            logger.info(f"Search latencies: {latencies}")
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
