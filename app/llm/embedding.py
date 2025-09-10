import numpy as np
import logging
from typing import List, Optional
from functools import lru_cache

from sentence_transformers import SentenceTransformer
import torch

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingManager:
    """
    SentenceTransformer 모델을 관리하고 텍스트 임베딩을 생성하는 클래스
    """
    
    def __init__(self):
        self.model_name = settings.embedding_model
        self.batch_size = settings.embedding_batch_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model: Optional[SentenceTransformer] = None

        # LRU cache for embeddings
        cache_size = getattr(settings, "embedding_cache_size", 0)
        self._cached_encode = (
            lru_cache(maxsize=cache_size)(self._encode_text)
            if cache_size and cache_size > 0
            else self._encode_text
        )
        
        logger.info(f"EmbeddingManager initialized - Model: {self.model_name}, Device: {self.device}")
    
    def load_model(self):
        """임베딩 모델 로드"""
        if self.model is not None:
            return
        logger.info(f"Loading embedding model: {self.model_name} on {self.device}")
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model {self.model_name}: {e}")
            self.model = None

    def _encode_text(self, text: str) -> np.ndarray:
        return self.model.encode(text, convert_to_numpy=True).astype(np.float32)

    def clear_cache(self):
        """Clear the embedding cache."""
        if hasattr(self._cached_encode, "cache_clear"):
            self._cached_encode.cache_clear()

    def get_embedding(self, text: str) -> np.ndarray:
        """단일 텍스트에 대한 임베딩 생성"""
        if self.model is None:
            self.load_model()
        
        if self.model is None:
            raise RuntimeError("Embedding model is not available.")
            
        return self._cached_encode(text)
            
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """여러 텍스트에 대한 임베딩을 배치로 생성"""
        if self.model is None:
            self.load_model()

        if self.model is None:
            raise RuntimeError("Embedding model is not available.")

        return np.array([self._cached_encode(t) for t in texts], dtype=np.float32)

# 전역 인스턴스 (싱글톤 패턴)
_embedding_manager: Optional[EmbeddingManager] = None


def get_embedding_manager() -> EmbeddingManager:
    """임베딩 매니저 싱글톤 인스턴스 반환"""
    global _embedding_manager
    if _embedding_manager is None:
        _embedding_manager = EmbeddingManager()
    return _embedding_manager


def get_text_embedding(text: str) -> np.ndarray:
    """단일 텍스트 임베딩 생성 편의 함수"""
    manager = get_embedding_manager()
    return manager.get_embedding(text)

