from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # 데이터베이스
    database_url: str = "sqlite:///data/hananavilite.db"
    
    # FAISS 설정
    faiss_dimension: int = 1024
    faiss_index_path: str = "models/faiss_index"
    
    # LLM 설정
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "gemma3:12b-it-qat"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.1
    
    # 임베딩 설정
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_batch_size: int = 32
    
    # 검색 설정
    hybrid_search_top_k: int = 20
    rrf_k: int = 60
    vector_weight: float = 0.6
    ir_weight: float = 0.4
    
    # 시스템 설정
    log_level: str = "INFO"
    max_memory_gb: int = 25
    
    # API 설정
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_title: str = "HanaNaviLite API"
    api_version: str = "1.0.0"
    
    # 파일 업로드 설정
    max_file_size_mb: int = 100
    upload_dir: str = "uploads"
    
    # 보안 설정
    cors_origins: list = ["*"]
    
    class Config:
        env_file = ".env"


# 전역 설정 인스턴스
settings = Settings()


def get_settings() -> Settings:
    """설정 인스턴스를 반환하는 함수"""
    return settings


# 데이터베이스 URL을 절대 경로로 변환
def get_database_path() -> str:
    """SQLite 데이터베이스의 절대 경로를 반환"""
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url[10:]  # "sqlite:///" 제거
        if not os.path.isabs(db_path):
            # 상대 경로를 절대 경로로 변환
            return os.path.join(os.getcwd(), db_path)
        return db_path
    return settings.database_url


# FAISS 인덱스 경로를 절대 경로로 변환
def get_faiss_index_path() -> str:
    """FAISS 인덱스의 절대 경로를 반환"""
    if not os.path.isabs(settings.faiss_index_path):
        return os.path.join(os.getcwd(), settings.faiss_index_path)
    return settings.faiss_index_path


# 업로드 디렉토리 절대 경로
def get_upload_dir() -> str:
    """업로드 디렉토리의 절대 경로를 반환"""
    if not os.path.isabs(settings.upload_dir):
        return os.path.join(os.getcwd(), settings.upload_dir)
    return settings.upload_dir