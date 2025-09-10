from pydantic_settings import BaseSettings
from typing import Optional
import os
import logging # 로깅을 위한 모듈 추가

logger = logging.getLogger(__name__) # 로거 인스턴스 생성

class Settings(BaseSettings):
    # 데이터베이스 설정: SQLite 데이터베이스 파일 경로
    database_url: str = "sqlite:///data/hananavilite.db"
    
    # FAISS (벡터 검색 엔진) 설정
    faiss_dimension: int = 1024 # FAISS 인덱스의 벡터 차원 (snowflake-arctic-embed-l은 1024차원)
    faiss_index_path: str = "models/faiss_index" # FAISS 인덱스 파일 저장 경로
    
    # LLM (대규모 언어 모델) 설정
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435") # Ollama 서버의 기본 URL
    llm_model: str = os.getenv("LLM_MODEL", "gemma3:12b-it-qat") # 사용할 LLM 모델 이름
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2048")) # LLM 응답의 최대 토큰 수
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1")) # LLM 응답의 다양성 (창의성) 제어 (0.0 ~ 1.0)
    
    # 임베딩 (텍스트를 벡터로 변환) 설정
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "dragonkue/snowflake-arctic-embed-l-v2.0-ko") # 사용할 임베딩 모델 이름
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32")) # 임베딩 처리 시 배치 크기
    embedding_cache_size: int = int(os.getenv("EMBEDDING_CACHE_SIZE", "1024")) # 임베딩 캐시 최대 크기
    
    # 검색 엔진 설정 (하이브리드 검색)
    hybrid_search_top_k: int = 20 # 하이브리드 검색 결과의 최대 개수
    rrf_k: int = 60 # RRF (Reciprocal Rank Fusion) 알고리즘의 K 파라미터
    vector_weight: float = 0.6 # 벡터 검색 결과의 가중치 (RRF 융합 시 사용)
    ir_weight: float = 0.4 # IR (정보 검색) 결과의 가중치 (RRF 융합 시 사용)
    
    # 시스템 전반 설정
    log_level: str = "INFO" # 애플리케이션 로깅 레벨 (DEBUG, INFO, WARNING, ERROR 등)
    max_memory_gb: int = 25 # 애플리케이션의 최대 메모리 사용량 제한 (GB)
    
    # FastAPI API 설정
    api_host: str = "0.0.0.0" # API 서버가 바인딩될 호스트 주소
    api_port: int = 8001 # API 서버가 사용할 포트 번호
    api_title: str = "HanaNaviLite API" # API 문서에 표시될 제목
    api_version: str = "1.0.0" # API 버전
    
    # 파일 업로드 설정
    max_file_size_mb: int = 100 # 업로드 가능한 파일의 최대 크기 (MB)
    upload_dir: str = "uploads" # 업로드된 파일이 저장될 디렉토리
    
    # 보안 설정
    cors_origins: list = ["*"] # CORS (Cross-Origin Resource Sharing) 허용 오리진 목록

    class Config:
        # .env 파일에서 환경 변수를 로드하도록 설정
        env_file = ".env"


# 전역 설정 인스턴스: 애플리케이션 전체에서 이 설정을 공유하여 사용합니다.
settings = Settings()


def get_settings() -> Settings:
    """
    설정 인스턴스를 반환하는 함수.
    FastAPI의 Depends 주입 시스템에서 사용될 수 있습니다.
    """
    return settings


def get_database_path() -> str:
    """
    SQLite 데이터베이스 파일의 절대 경로를 반환합니다.
    설정된 database_url이 상대 경로일 경우, 현재 작업 디렉토리를 기준으로 절대 경로를 생성합니다.
    """
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url[10:]  # "sqlite:///" 접두사 제거
        if not os.path.isabs(db_path):
            # 상대 경로를 절대 경로로 변환
            return os.path.join(os.getcwd(), db_path)
        return db_path
    return settings.database_url


def get_faiss_index_path() -> str:
    """
    FAISS 인덱스 파일의 절대 경로를 반환합니다.
    설정된 faiss_index_path가 상대 경로일 경우, 현재 작업 디렉토리를 기준으로 절대 경로를 생성합니다。
    """
    if not os.path.isabs(settings.faiss_index_path):
        return os.path.join(os.getcwd(), settings.faiss_index_path)
    return settings.faiss_index_path


def get_upload_dir() -> str:
    """
    업로드 디렉토리의 절대 경로를 반환합니다.
    설정된 upload_dir이 상대 경로일 경우, 현재 작업 디렉토리를 기준으로 절대 경로를 생성합니다.
    """
    if not os.path.isabs(settings.upload_dir):
        return os.path.join(os.getcwd(), settings.upload_dir)
    return settings.upload_dir