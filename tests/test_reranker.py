from app.search.reranker import Reranker
from app.search.rrf import HybridSearchResult


def make_result(chunk_id: str, text: str) -> HybridSearchResult:
    return HybridSearchResult(
        chunk_id=chunk_id,
        document_id=None,
        title="",
        content=text,
        snippet=text,
        vector_score=0.0,
        ir_score=0.0,
        fusion_score=0.0,
    )


def test_rerank_orders_by_similarity():
    reranker = Reranker(fusion_weight=0.0)
    query = "금리 안내"
    r1 = make_result("1", "금리 안내 정보")
    r2 = make_result("2", "대출 한도")
    results = [r2, r1]
    reranked = reranker.rerank(query, results)
    assert reranked[0].chunk_id == "1"
    assert reranked[0].rank == 1


def test_ndcg_computation():
    reranker = Reranker(fusion_weight=0.0)
    query = "금리 안내"
    r1 = make_result("1", "금리 안내 정보")
    r2 = make_result("2", "대출 한도")
    results = [r1, r2]
    ground_truth = {"1": 3, "2": 2}
    reranked = reranker.rerank(query, results, ground_truth=ground_truth)
    # ideal ranking => nDCG should be 1.0
    ndcg = reranker._calculate_ndcg(reranked, ground_truth)
    assert ndcg > 0.99
