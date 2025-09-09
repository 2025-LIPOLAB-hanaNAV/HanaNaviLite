import logging
import math
from typing import List, Dict, Any, Union, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

from app.search.faiss_engine import VectorSearchResult
from app.search.ir_engine import IRSearchResult
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class HybridSearchResult:
    """하이브리드 검색 결과"""
    chunk_id: str
    document_id: Optional[int]
    title: str
    content: str
    snippet: str
    vector_score: float
    ir_score: float
    fusion_score: float
    rank: int
    metadata: Optional[Dict[str, Any]] = None
    source_types: List[str] = None  # ['vector', 'ir'] 등


class RRFAlgorithm:
    """
    Reciprocal Rank Fusion (RRF) 알고리즘 구현
    IR과 Vector 검색 결과를 효과적으로 융합
    """
    
    def __init__(self, k: int = 60):
        """
        Args:
            k: RRF 파라미터 (일반적으로 60 사용)
        """
        self.k = k
        self.vector_weight = settings.vector_weight  # 0.6
        self.ir_weight = settings.ir_weight  # 0.4
        
        logger.info(f"RRF Algorithm initialized - k={k}, vector_weight={self.vector_weight}, ir_weight={self.ir_weight}")
    
    def fuse_results(
        self,
        vector_results: List[VectorSearchResult],
        ir_results: List[IRSearchResult],
        top_k: int = 20,
        vector_weight: float = 0.6,
        ir_weight: float = 0.4
    ) -> List[HybridSearchResult]:
        """
        RRF를 사용하여 벡터와 IR 검색 결과 융합
        """
        if not vector_results and not ir_results:
            return []
        
        # 결과를 chunk_id 기반으로 그룹화
        all_chunks = self._group_results_by_chunk(vector_results, ir_results)
        
        # RRF 점수 계산
        fusion_scores = self._calculate_rrf_scores(vector_results, ir_results)
        
        # 하이브리드 결과 구성
        hybrid_results = []
        for chunk_id, chunk_data in all_chunks.items():
            fusion_score = fusion_scores.get(chunk_id, 0.0)
            
            # 메타데이터 및 기본 정보 추출
            vector_result = chunk_data.get('vector')
            ir_result = chunk_data.get('ir')
            
            # 기본 정보 결정 (IR 우선, Vector 보완)
            if ir_result:
                title = ir_result.title
                content = ir_result.content
                snippet = ir_result.snippet
                document_id = ir_result.document_id
                metadata = ir_result.metadata
            else:
                # Vector만 있는 경우
                title = ""
                content = ""
                snippet = ""
                document_id = None
                metadata = vector_result.metadata if vector_result else None
            
            # 점수 추출
            vector_score = vector_result.score if vector_result else 0.0
            ir_score = ir_result.score if ir_result else 0.0
            
            # 소스 타입 결정
            source_types = []
            if vector_result:
                source_types.append('vector')
            if ir_result:
                source_types.append('ir')
            
            hybrid_results.append(HybridSearchResult(
                chunk_id=chunk_id,
                document_id=document_id,
                title=title,
                content=content,
                snippet=snippet,
                vector_score=vector_score,
                ir_score=ir_score,
                fusion_score=fusion_score,
                rank=0,  # 나중에 설정
                metadata=metadata,
                source_types=source_types
            ))
        
        # 융합 점수로 정렬
        hybrid_results.sort(key=lambda x: x.fusion_score, reverse=True)
        
        # 순위 설정
        for i, result in enumerate(hybrid_results):
            result.rank = i + 1
        
        # 상위 결과 반환
        final_results = hybrid_results[:top_k]
        
        logger.info(f"RRF fusion returned {len(final_results)} results from {len(vector_results)} vector + {len(ir_results)} IR results")
        return final_results
    
    def _group_results_by_chunk(
        self,
        vector_results: List[VectorSearchResult],
        ir_results: List[IRSearchResult]
    ) -> Dict[str, Dict[str, Union[VectorSearchResult, IRSearchResult]]]:
        """결과를 chunk_id 기준으로 그룹화"""
        all_chunks = {}
        
        # Vector 결과 추가
        for result in vector_results:
            chunk_id = result.chunk_id
            if chunk_id not in all_chunks:
                all_chunks[chunk_id] = {}
            all_chunks[chunk_id]['vector'] = result
        
        # IR 결과 추가
        for result in ir_results:
            chunk_id = result.chunk_id
            if chunk_id not in all_chunks:
                all_chunks[chunk_id] = {}
            all_chunks[chunk_id]['ir'] = result
        
        return all_chunks
    
    def _calculate_rrf_scores(
        self,
        vector_results: List[VectorSearchResult],
        ir_results: List[IRSearchResult]
    ) -> Dict[str, float]:
        """RRF 점수 계산"""
        fusion_scores = defaultdict(float)
        
        # Vector 검색 결과의 RRF 점수
        for rank, result in enumerate(vector_results, 1):
            rrf_score = 1.0 / (self.k + rank)
            fusion_scores[result.chunk_id] += self.vector_weight * rrf_score
        
        # IR 검색 결과의 RRF 점수
        for rank, result in enumerate(ir_results, 1):
            rrf_score = 1.0 / (self.k + rank)
            fusion_scores[result.chunk_id] += self.ir_weight * rrf_score
        
        return dict(fusion_scores)
    
    def calculate_weighted_score(
        self,
        vector_score: float,
        ir_score: float,
        method: str = "linear"
    ) -> float:
        """
        가중 점수 계산 (RRF 대안)
        
        Args:
            vector_score: 벡터 검색 점수 (0-1)
            ir_score: IR 검색 점수 (0-1)  
            method: 융합 방법 ('linear', 'harmonic', 'geometric')
        """
        if method == "linear":
            return self.vector_weight * vector_score + self.ir_weight * ir_score
        
        elif method == "harmonic":
            if vector_score == 0 or ir_score == 0:
                return 0.0
            return 2 / (1/vector_score + 1/ir_score)
        
        elif method == "geometric":
            return math.sqrt(vector_score * ir_score)
        
        else:
            # 기본값: linear
            return self.vector_weight * vector_score + self.ir_weight * ir_score
    
    def fuse_with_weighted_scores(
        self,
        vector_results: List[VectorSearchResult],
        ir_results: List[IRSearchResult],
        method: str = "linear",
        top_k: int = 20
    ) -> List[HybridSearchResult]:
        """
        가중 점수를 사용한 결과 융합 (RRF 대안)
        """
        if not vector_results and not ir_results:
            return []
        
        # 결과를 chunk_id 기반으로 그룹화
        all_chunks = self._group_results_by_chunk(vector_results, ir_results)
        
        hybrid_results = []
        for chunk_id, chunk_data in all_chunks.items():
            vector_result = chunk_data.get('vector')
            ir_result = chunk_data.get('ir')
            
            # 점수 추출 (없으면 0.0)
            vector_score = vector_result.score if vector_result else 0.0
            ir_score = ir_result.score if ir_result else 0.0
            
            # 융합 점수 계산
            fusion_score = self.calculate_weighted_score(vector_score, ir_score, method)
            
            # 기본 정보 결정
            if ir_result:
                title = ir_result.title
                content = ir_result.content
                snippet = ir_result.snippet
                document_id = ir_result.document_id
                metadata = ir_result.metadata
            else:
                title = ""
                content = ""
                snippet = ""
                document_id = None
                metadata = vector_result.metadata if vector_result else None
            
            # 소스 타입 결정
            source_types = []
            if vector_result:
                source_types.append('vector')
            if ir_result:
                source_types.append('ir')
            
            hybrid_results.append(HybridSearchResult(
                chunk_id=chunk_id,
                document_id=document_id,
                title=title,
                content=content,
                snippet=snippet,
                vector_score=vector_score,
                ir_score=ir_score,
                fusion_score=fusion_score,
                rank=0,
                metadata=metadata,
                source_types=source_types
            ))
        
        # 융합 점수로 정렬
        hybrid_results.sort(key=lambda x: x.fusion_score, reverse=True)
        
        # 순위 설정
        for i, result in enumerate(hybrid_results):
            result.rank = i + 1
        
        return hybrid_results[:top_k]
    
    def rerank_results(
        self,
        results: List[HybridSearchResult],
        boost_factors: Optional[Dict[str, float]] = None
    ) -> List[HybridSearchResult]:
        """
        추가적인 재랭킹 수행
        
        Args:
            results: 초기 융합 결과
            boost_factors: 부스팅 팩터 (예: {'recent': 1.2, 'important': 1.5})
        """
        if not boost_factors:
            return results
        
        reranked_results = []
        for result in results:
            boosted_score = result.fusion_score
            
            # 메타데이터 기반 부스팅
            if result.metadata:
                for factor_name, factor_value in boost_factors.items():
                    if factor_name in result.metadata:
                        boosted_score *= factor_value
            
            # 소스 타입 기반 부스팅
            if 'both_sources' in boost_factors and len(result.source_types) > 1:
                boosted_score *= boost_factors['both_sources']
            
            # 새로운 결과 객체 생성
            new_result = HybridSearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                title=result.title,
                content=result.content,
                snippet=result.snippet,
                vector_score=result.vector_score,
                ir_score=result.ir_score,
                fusion_score=boosted_score,
                rank=0,  # 재설정됨
                metadata=result.metadata,
                source_types=result.source_types
            )
            
            reranked_results.append(new_result)
        
        # 부스팅된 점수로 재정렬
        reranked_results.sort(key=lambda x: x.fusion_score, reverse=True)
        
        # 순위 재설정
        for i, result in enumerate(reranked_results):
            result.rank = i + 1
        
        logger.info(f"Reranked {len(results)} results with boost factors: {boost_factors}")
        return reranked_results
    
    def get_diversity_filtered_results(
        self,
        results: List[HybridSearchResult],
        max_per_document: int = 3,
        diversity_threshold: float = 0.8
    ) -> List[HybridSearchResult]:
        """
        다양성을 고려한 결과 필터링
        
        Args:
            results: 입력 결과
            max_per_document: 문서당 최대 결과 수
            diversity_threshold: 다양성 임계값
        """
        if not results:
            return []
        
        filtered_results = []
        document_counts = defaultdict(int)
        seen_contents = set()
        
        for result in results:
            # 문서당 개수 제한
            if result.document_id is not None:
                if document_counts[result.document_id] >= max_per_document:
                    continue
                document_counts[result.document_id] += 1
            
            # 콘텐츠 유사성 체크 (간단한 버전)
            content_words = set(result.content.lower().split()[:10])  # 처음 10단어
            
            is_similar = False
            for seen_words in seen_contents:
                similarity = len(content_words & seen_words) / len(content_words | seen_words)
                if similarity > diversity_threshold:
                    is_similar = True
                    break
            
            if not is_similar:
                filtered_results.append(result)
                seen_contents.add(frozenset(content_words))
        
        logger.info(f"Diversity filtering: {len(results)} -> {len(filtered_results)} results")
        return filtered_results
    
    def get_stats(self) -> Dict[str, Any]:
        """RRF 알고리즘 통계"""
        return {
            "algorithm": "RRF",
            "k_parameter": self.k,
            "vector_weight": self.vector_weight,
            "ir_weight": self.ir_weight,
            "total_weight": self.vector_weight + self.ir_weight
        }


# 전역 인스턴스 (싱글톤 패턴)
_rrf_algorithm: Optional[RRFAlgorithm] = None


def get_rrf_algorithm() -> RRFAlgorithm:
    """RRF 알고리즘 싱글톤 인스턴스 반환"""
    global _rrf_algorithm
    if _rrf_algorithm is None:
        rrf_k = settings.rrf_k if hasattr(settings, 'rrf_k') else 60
        _rrf_algorithm = RRFAlgorithm(k=rrf_k)
    return _rrf_algorithm