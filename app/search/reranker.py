import logging
from typing import List, Optional, Dict

from app.search.rrf import HybridSearchResult
from app.utils.text_processor import get_text_processor

logger = logging.getLogger(__name__)


class Reranker:
    """Simple reranker that scores candidates using lexical overlap."""

    def __init__(self, fusion_weight: float = 0.7):
        # fusion_weight: weight given to original fusion score when combining
        self.fusion_weight = fusion_weight
        self.text_processor = get_text_processor()
        logger.info("Reranker initialized with fusion_weight=%s", fusion_weight)

    def _tokenize(self, text: str) -> set:
        keywords = self.text_processor.extract_keywords(text or "", max_keywords=100)
        return set(keywords)

    def _similarity(self, query: str, text: str) -> float:
        q_tokens = self._tokenize(query)
        t_tokens = self._tokenize(text)
        if not q_tokens or not t_tokens:
            return 0.0
        return len(q_tokens & t_tokens) / len(q_tokens | t_tokens)

    def rerank(
        self,
        query: str,
        results: List[HybridSearchResult],
        top_k: Optional[int] = None,
        ground_truth: Optional[Dict[str, int]] = None,
    ) -> List[HybridSearchResult]:
        if not results:
            return []

        for result in results:
            sim = self._similarity(query, result.content or result.snippet)
            result.rerank_score = (
                self.fusion_weight * result.fusion_score + (1 - self.fusion_weight) * sim
            )
            logger.debug(
                "chunk_id=%s fusion=%.4f sim=%.4f rerank=%.4f",
                result.chunk_id,
                result.fusion_score,
                sim,
                result.rerank_score,
            )

        results.sort(key=lambda x: x.rerank_score, reverse=True)
        if top_k is not None:
            results = results[:top_k]

        for i, r in enumerate(results):
            r.rank = i + 1

        if ground_truth:
            ndcg = self._calculate_ndcg(results, ground_truth)
            logger.info("nDCG@%d: %.4f", len(results), ndcg)
        logger.info("Reranked %d results", len(results))
        return results

    def _calculate_ndcg(
        self, results: List[HybridSearchResult], ground_truth: Dict[str, int]
    ) -> float:
        import math

        dcg = 0.0
        for i, res in enumerate(results, 1):
            rel = ground_truth.get(res.chunk_id, 0)
            dcg += (2**rel - 1) / math.log2(i + 1)

        ideal_rels = sorted(ground_truth.values(), reverse=True)[: len(results)]
        idcg = 0.0
        for i, rel in enumerate(ideal_rels, 1):
            idcg += (2**rel - 1) / math.log2(i + 1)
        if idcg == 0:
            return 0.0
        return dcg / idcg


# Singleton pattern
_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker

