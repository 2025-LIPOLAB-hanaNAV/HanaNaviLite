from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
import os
from typing import Dict, Any

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import get_db_manager
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.api.etl import router as etl_router
from app.api.rag import router as rag_router
from app.api.statistics import router as statistics_router
from app.api.admin import router as admin_router
from app.api.evaluation import router as evaluation_router
from app.conversation.api import conversation_router
from app.search.faiss_engine import cleanup_faiss_engine
from app.llm.embedding import get_embedding_manager


# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log') if os.path.exists(os.path.dirname(os.path.abspath('app.log'))) else logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 라이프사이클 관리"""
    # 시작시 실행
    logger.info("Starting HanaNaviLite application...")
    
    # 데이터베이스 초기화 확인
    db_manager = get_db_manager()
    health_status = db_manager.health_check()
    
    if health_status.get("status") != "healthy":
        logger.error(f"Database health check failed: {health_status}")
        raise RuntimeError("Database initialization failed")
    
    # 임베딩 모델 로드
    try:
        embedding_manager = get_embedding_manager()
        embedding_manager.load_model()
        logger.info("Embedding model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load embedding model during startup: {e}", exc_info=True)
        # 모델 로딩 실패 시에도 서버는 시작될 수 있도록 처리 (선택적)
        # raise RuntimeError("Failed to load essential models") from e
    
    logger.info(f"Database initialized: {health_status}")
    logger.info(f"Application started on {settings.api_host}:{settings.api_port}")
    
    yield
    
    # 종료시 실행
    logger.info("Shutting down HanaNaviLite application...")
    cleanup_faiss_engine()
    logger.info("FAISS engine cleaned up.")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="HanaNaviLite - 경량화 RAG 챗봇 시스템",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 전역 예외 처리기
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# 라우터 등록
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(search_router, prefix="/api/v1", tags=["Search"])
app.include_router(etl_router, prefix="/api/v1", tags=["ETL"])
app.include_router(rag_router, prefix="/api/v1", tags=["RAG"])
app.include_router(statistics_router, prefix="/api/v1", tags=["Statistics"])
app.include_router(admin_router, prefix="/api/v1", tags=["Admin"])
app.include_router(evaluation_router, prefix="/api/v1", tags=["Evaluation"])
app.include_router(conversation_router, prefix="/api/v1", tags=["Conversation"])


# 루트 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "HanaNaviLite API",
        "version": settings.api_version,
        "status": "running",
        "docs": "/docs"
    }


# 시스템 정보 엔드포인트
@app.get("/info")
async def get_system_info():
    """시스템 정보 반환"""
    import psutil
    
    # 메모리 사용량
    memory = psutil.virtual_memory()
    memory_used_gb = memory.used / (1024**3)
    memory_total_gb = memory.total / (1024**3)
    
    # 디스크 사용량
    disk = psutil.disk_usage('/')
    disk_used_gb = disk.used / (1024**3)
    disk_total_gb = disk.total / (1024**3)
    
    return {
        "system": {
            "memory": {
                "used_gb": round(memory_used_gb, 2),
                "total_gb": round(memory_total_gb, 2),
                "percentage": memory.percent
            },
            "disk": {
                "used_gb": round(disk_used_gb, 2),
                "total_gb": round(disk_total_gb, 2),
                "percentage": round((disk_used_gb / disk_total_gb) * 100, 2)
            }
        },
        "settings": {
            "max_memory_gb": settings.max_memory_gb,
            "embedding_model": settings.embedding_model,
            "llm_model": settings.llm_model,
            "faiss_dimension": settings.faiss_dimension
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower()
    )