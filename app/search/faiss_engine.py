import faiss
import numpy as np
import os
import logging
import pickle
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from contextlib import contextmanager
import gc

from app.core.config import get_settings, get_faiss_index_path

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class VectorSearchResult:
    """벡터 검색 결과"""
    chunk_id: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class FAISSVectorEngine:
    """
    FAISS 기반 벡터 검색 엔진
    메모리 최적화 및 성능 최적화를 위한 기능 포함
    """
    
    def __init__(self):
        self.dimension = settings.faiss_dimension
        self.index_path = get_faiss_index_path()
        self.index: Optional[faiss.Index] = None
        self.id_mapping: Dict[int, str] = {}  # faiss_id -> chunk_id
        self.reverse_mapping: Dict[str, int] = {}  # chunk_id -> faiss_id
        self.metadata_cache: Dict[str, Dict[str, Any]] = {}
        self.is_loaded = False
        
        # 메모리 최적화 설정
        self.max_cache_size = 10000  # 최대 캐시 항목 수
        self.enable_gpu = faiss.get_num_gpus() > 0
        
        logger.info(f"FAISS Engine initialized - Dimension: {self.dimension}, GPU: {self.enable_gpu}")
    
    def _ensure_index_directory(self):
        """인덱스 디렉토리 생성"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
    
    def _create_index(self) -> faiss.Index:
        """
        FAISS 인덱스 생성
        메모리 최적화를 위해 IndexFlatIP 사용 (Inner Product)
        """
        if self.enable_gpu and self.dimension <= 2048:
            # GPU 사용 가능하고 차원이 적당한 경우
            index = faiss.IndexFlatIP(self.dimension)
            gpu_res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(gpu_res, 0, index)
            logger.info("Created GPU-accelerated FAISS index")
        else:
            # CPU 인덱스 사용
            index = faiss.IndexFlatIP(self.dimension)
            logger.info("Created CPU FAISS index")
        
        return index
    
    def load_index(self) -> bool:
        """
        저장된 인덱스 로드
        메모리 사용량 모니터링 포함
        """
        try:
            if not os.path.exists(f"{self.index_path}.faiss"):
                logger.info("No existing FAISS index found, creating new one")
                self.index = self._create_index()
                self.is_loaded = True
                return True
            
            # 인덱스 파일 로드
            self.index = faiss.read_index(f"{self.index_path}.faiss")
            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            
            # 메타데이터 로드
            metadata_path = f"{self.index_path}_metadata.pkl"
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.id_mapping = data.get('id_mapping', {})
                    self.reverse_mapping = data.get('reverse_mapping', {})
                    self.metadata_cache = data.get('metadata_cache', {})
                
                logger.info(f"Loaded {len(self.id_mapping)} ID mappings")
            
            # 메모리 사용량 체크
            self._check_memory_usage()
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            # 실패 시 새 인덱스 생성
            self.index = self._create_index()
            self.is_loaded = True
            return False
    
    def save_index(self) -> bool:
        """인덱스 저장"""
        try:
            if self.index is None:
                logger.warning("No index to save")
                return False
            
            self._ensure_index_directory()
            
            # 인덱스 저장
            faiss.write_index(self.index, f"{self.index_path}.faiss")
            
            # 메타데이터 저장
            metadata = {
                'id_mapping': self.id_mapping,
                'reverse_mapping': self.reverse_mapping,
                'metadata_cache': self.metadata_cache
            }
            
            with open(f"{self.index_path}_metadata.pkl", 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            return False
    
    def add_vectors(self, chunk_ids: List[str], vectors: np.ndarray, 
                   metadata: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        벡터 추가
        메모리 최적화를 위한 배치 처리
        """
        try:
            if not self.is_loaded:
                self.load_index()
            
            if self.index is None:
                raise ValueError("Index not initialized")
            
            if len(chunk_ids) != vectors.shape[0]:
                raise ValueError("Number of chunk_ids must match number of vectors")
            
            # L2 정규화 (코사인 유사도를 위해)
            vectors = vectors.astype(np.float32)
            faiss.normalize_L2(vectors)
            
            # 시작 인덱스
            start_idx = self.index.ntotal
            
            # 벡터 추가
            self.index.add(vectors)
            
            # ID 매핑 업데이트
            for i, chunk_id in enumerate(chunk_ids):
                faiss_id = start_idx + i
                self.id_mapping[faiss_id] = chunk_id
                self.reverse_mapping[chunk_id] = faiss_id
                
                # 메타데이터 캐시 업데이트
                if metadata and i < len(metadata):
                    self.metadata_cache[chunk_id] = metadata[i]
            
            # 메모리 정리
            del vectors
            gc.collect()
            
            # 메모리 사용량 체크
            self._check_memory_usage()
            
            logger.info(f"Added {len(chunk_ids)} vectors to FAISS index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            return False
    
    def search(self, query_vector: np.ndarray, top_k: int = 10, 
              filter_metadata: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        """
        벡터 검색
        메모리 효율적인 검색 수행
        """
        try:
            if not self.is_loaded:
                self.load_index()
            
            if self.index is None or self.index.ntotal == 0:
                logger.warning("No vectors in index")
                return []
            
            # 쿼리 벡터 정규화
            query_vector = query_vector.astype(np.float32).reshape(1, -1)
            faiss.normalize_L2(query_vector)
            
            # 검색 수행
            scores, indices = self.index.search(query_vector, top_k)
            
            results = []
            for i in range(len(scores[0])):
                faiss_id = indices[0][i]
                score = float(scores[0][i])
                
                # 유효한 인덱스인지 확인
                if faiss_id < 0:
                    continue
                
                chunk_id = self.id_mapping.get(faiss_id)
                if not chunk_id:
                    continue
                
                metadata = self.metadata_cache.get(chunk_id)
                
                # 필터링 적용
                if filter_metadata and metadata:
                    should_include = True
                    for key, value in filter_metadata.items():
                        meta_val = metadata.get(key)
                        if isinstance(value, list):
                            if not meta_val:
                                should_include = False
                                break
                            if isinstance(meta_val, list):
                                if not any(v in meta_val for v in value):
                                    should_include = False
                                    break
                            else:
                                if meta_val not in value:
                                    should_include = False
                                    break
                        else:
                            if meta_val != value:
                                should_include = False
                                break
                    if not should_include:
                        continue
                
                results.append(VectorSearchResult(
                    chunk_id=chunk_id,
                    score=score,
                    metadata=metadata
                ))
            
            logger.info(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def remove_vectors(self, chunk_ids: List[str]) -> bool:
        """
        벡터 제거 (재구축 방식)
        FAISS는 직접 삭제를 지원하지 않으므로 인덱스 재구축
        """
        try:
            if not self.is_loaded or self.index is None:
                logger.warning("Index not loaded")
                return False
            
            # 제거할 chunk_id 집합 생성
            remove_set = set(chunk_ids)
            
            # 남길 벡터들 수집
            remaining_vectors = []
            remaining_chunk_ids = []
            remaining_metadata = []
            
            for faiss_id, chunk_id in self.id_mapping.items():
                if chunk_id not in remove_set and faiss_id < self.index.ntotal:
                    # 벡터 추출
                    vector = self.index.reconstruct(faiss_id)
                    remaining_vectors.append(vector)
                    remaining_chunk_ids.append(chunk_id)
                    
                    # 메타데이터 추가
                    metadata = self.metadata_cache.get(chunk_id)
                    remaining_metadata.append(metadata)
            
            if not remaining_vectors:
                # 모든 벡터가 제거된 경우
                self.index = self._create_index()
                self.id_mapping.clear()
                self.reverse_mapping.clear()
                self.metadata_cache.clear()
                logger.info("All vectors removed, created new empty index")
                return True
            
            # 새 인덱스 생성 및 벡터 추가
            self.index = self._create_index()
            self.id_mapping.clear()
            self.reverse_mapping.clear()
            self.metadata_cache.clear()
            
            vectors_array = np.array(remaining_vectors)
            success = self.add_vectors(remaining_chunk_ids, vectors_array, remaining_metadata)
            
            # 메모리 정리
            del remaining_vectors, vectors_array
            gc.collect()
            
            logger.info(f"Removed {len(chunk_ids)} vectors, {len(remaining_chunk_ids)} remaining")
            return success
            
        except Exception as e:
            logger.error(f"Failed to remove vectors: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보"""
        if not self.is_loaded or self.index is None:
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_type": type(self.index).__name__,
            "gpu_enabled": self.enable_gpu,
            "mapping_count": len(self.id_mapping),
            "metadata_count": len(self.metadata_cache)
        }
    
    def _check_memory_usage(self):
        """메모리 사용량 체크 및 경고"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            memory_used_gb = memory.used / (1024**3)
            memory_limit = settings.max_memory_gb * 0.5  # FAISS는 전체 메모리의 50% 이하
            
            if memory_used_gb > memory_limit:
                logger.warning(
                    f"FAISS memory usage high: {memory_used_gb:.1f}GB > {memory_limit:.1f}GB"
                )
                # 캐시 정리
                self._cleanup_cache()
            
        except ImportError:
            logger.debug("psutil not available for memory monitoring")
    
    def _cleanup_cache(self):
        """메타데이터 캐시 정리 (LRU 방식)"""
        if len(self.metadata_cache) > self.max_cache_size:
            # 간단한 LRU 구현: 절반 제거
            items_to_remove = len(self.metadata_cache) - (self.max_cache_size // 2)
            keys_to_remove = list(self.metadata_cache.keys())[:items_to_remove]
            
            for key in keys_to_remove:
                del self.metadata_cache[key]
            
            logger.info(f"Cleaned up {items_to_remove} cache entries")
            gc.collect()
    
    @contextmanager
    def batch_mode(self):
        """배치 모드 컨텍스트 매니저"""
        logger.info("Entering batch mode")
        try:
            yield self
        finally:
            # 배치 작업 후 정리
            gc.collect()
            self._check_memory_usage()
            logger.info("Exiting batch mode")
    
    def close(self):
        """리소스 정리"""
        if self.index is not None:
            self.save_index()
            del self.index
            self.index = None
        
        self.id_mapping.clear()
        self.reverse_mapping.clear()
        self.metadata_cache.clear()
        self.is_loaded = False
        
        gc.collect()
        logger.info("FAISS engine closed and cleaned up")


# 전역 인스턴스 (싱글톤 패턴)
_faiss_engine: Optional[FAISSVectorEngine] = None


def get_faiss_engine() -> FAISSVectorEngine:
    """FAISS 엔진 싱글톤 인스턴스 반환"""
    global _faiss_engine
    if _faiss_engine is None:
        _faiss_engine = FAISSVectorEngine()
    return _faiss_engine


def cleanup_faiss_engine():
    """FAISS 엔진 정리 (애플리케이션 종료 시 호출)"""
    global _faiss_engine
    if _faiss_engine is not None:
        _faiss_engine.close()
        _faiss_engine = None