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

        # IVF 설정
        self.ivf_threshold = settings.faiss_ivf_threshold
        self.use_ivfpq = settings.faiss_ivf_use_pq
        self.ivf_nlist = settings.faiss_ivf_nlist
        self.ivfpq_m = settings.faiss_ivfpq_m

        logger.info(f"FAISS Engine initialized - Dimension: {self.dimension}, GPU: {self.enable_gpu}")
    
    def _ensure_index_directory(self):
        """인덱스 디렉토리 생성"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
    
    def _create_index(self, use_ivf: bool = False, nlist: Optional[int] = None,
                      pq_m: Optional[int] = None, pq_nbits: int = 8,
                      to_gpu: bool = True, use_pq: Optional[bool] = None) -> faiss.Index:
        """
        FAISS 인덱스 생성
        use_ivf가 True이면 IVF 기반 인덱스를 생성한다.
        """
        nlist = nlist or self.ivf_nlist
        use_pq = self.use_ivfpq if use_pq is None else use_pq

        if use_ivf:
            quantizer = faiss.IndexFlatIP(self.dimension)
            if use_pq:
                pq_m = pq_m or self.ivfpq_m
                index = faiss.IndexIVFPQ(
                    quantizer, self.dimension, nlist, pq_m, pq_nbits, faiss.METRIC_INNER_PRODUCT
                )
            else:
                index = faiss.IndexIVFFlat(
                    quantizer, self.dimension, nlist, faiss.METRIC_INNER_PRODUCT
                )
            logger.info(
                f"Created {'IVFPQ' if use_pq else 'IVFFlat'} index with nlist={nlist}"
            )
        else:
            index = faiss.IndexFlatIP(self.dimension)
            logger.info("Created Flat index")

        if self.enable_gpu and self.dimension <= 2048 and to_gpu:
            gpu_res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(gpu_res, 0, index)
            logger.info("Moved index to GPU")

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
            if self.enable_gpu and self.dimension <= 2048 and not faiss.index_is_gpu(self.index):
                gpu_res = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(gpu_res, 0, self.index)
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
            
            # 인덱스 저장 (GPU 인덱스는 CPU로 변환 후 저장)
            index_to_save = self.index
            if faiss.index_is_gpu(self.index):
                index_to_save = faiss.index_gpu_to_cpu(self.index)
            faiss.write_index(index_to_save, f"{self.index_path}.faiss")
            
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

    def rebuild_index(self, use_pq: Optional[bool] = None, nlist: Optional[int] = None,
                      pq_m: Optional[int] = None, pq_nbits: int = 8) -> bool:
        """현재 벡터들로 IVF 인덱스를 재구축"""
        try:
            if self.index is None or self.index.ntotal == 0:
                logger.warning("No vectors to rebuild")
                return False

            # 기존 벡터 및 메타데이터 수집
            vectors = []
            chunk_ids = []
            metadata = []
            for i in range(self.index.ntotal):
                vectors.append(self.index.reconstruct(i))
                cid = self.id_mapping.get(i)
                chunk_ids.append(cid)
                metadata.append(self.metadata_cache.get(cid))

            vectors_array = np.array(vectors, dtype=np.float32)
            faiss.normalize_L2(vectors_array)

            nlist = nlist or int(np.sqrt(len(vectors_array))) or 1

            new_index = self._create_index(
                use_ivf=True, nlist=nlist, pq_m=pq_m, pq_nbits=pq_nbits,
                to_gpu=False, use_pq=use_pq
            )
            new_index.train(vectors_array)
            if self.enable_gpu and self.dimension <= 2048:
                gpu_res = faiss.StandardGpuResources()
                new_index = faiss.index_cpu_to_gpu(gpu_res, 0, new_index)
            new_index.add(vectors_array)

            # 매핑 재구성
            self.index = new_index
            self.id_mapping = {i: cid for i, cid in enumerate(chunk_ids)}
            self.reverse_mapping = {cid: i for i, cid in enumerate(chunk_ids)}
            self.metadata_cache = {cid: md for cid, md in zip(chunk_ids, metadata)}

            gc.collect()
            logger.info("Rebuilt FAISS index using IVF")
            return True

        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
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

            # 필요 시 훈련 수행
            if isinstance(self.index, faiss.IndexIVF) and not self.index.is_trained:
                self.index.train(vectors)

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

            # IVF 인덱스로 전환 조건 확인
            total_vectors = self.index.ntotal
            if total_vectors > self.ivf_threshold and not isinstance(self.index, faiss.IndexIVF):
                logger.info(
                    f"Vector count {total_vectors} exceeded threshold {self.ivf_threshold}, rebuilding index"
                )
                self.rebuild_index()

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
                    should_include = all(
                        metadata.get(key) == value 
                        for key, value in filter_metadata.items()
                    )
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

    def clear_cache(self) -> None:
        """공개 캐시 정리 API: 메타데이터 캐시 및 내부 캐시를 초기화합니다."""
        # 메타데이터 캐시 전부 비우기
        cleared = len(self.metadata_cache)
        self.metadata_cache.clear()
        # 매핑은 유지 (인덱스와 동기화)
        logger.info(f"FAISS metadata cache cleared: {cleared} entries")
        # 인덱스 파일 갱신 (선택적)
        try:
            self.save_index()
        except Exception as e:
            logger.warning(f"FAISS cache clear: save_index warning: {e}")
    
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
