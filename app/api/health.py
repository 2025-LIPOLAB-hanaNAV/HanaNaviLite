from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import psutil
import os
from datetime import datetime

from app.core.database import get_db_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """종합 헬스체크 엔드포인트"""
    try:
        # 데이터베이스 상태 확인
        db_manager = get_db_manager()
        db_status = db_manager.health_check()
        
        # 메모리 사용량 확인
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        
        # 메모리 사용량이 임계치를 넘었는지 확인
        memory_warning = memory_used_gb > (settings.max_memory_gb * 0.8)
        
        # 디스크 사용량 확인
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024**3)
        
        # 전체 상태 결정
        overall_status = "healthy"
        issues = []
        
        if db_status.get("status") != "healthy":
            overall_status = "unhealthy"
            issues.append("database_connection_failed")
        
        if memory_warning:
            overall_status = "warning" if overall_status == "healthy" else overall_status
            issues.append("high_memory_usage")
        
        if disk_free_gb < 1.0:  # 1GB 미만일 때 경고
            overall_status = "warning" if overall_status == "healthy" else overall_status
            issues.append("low_disk_space")
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.api_version,
            "issues": issues,
            "details": {
                "database": db_status,
                "memory": {
                    "used_gb": round(memory_used_gb, 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "percentage": memory.percent,
                    "limit_gb": settings.max_memory_gb,
                    "warning": memory_warning
                },
                "disk": {
                    "free_gb": round(disk_free_gb, 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                    "percentage": round((disk.used / disk.total) * 100, 2)
                },
                "uptime": _get_uptime()
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/health/database")
async def database_health() -> Dict[str, Any]:
    """데이터베이스 전용 헬스체크"""
    try:
        db_manager = get_db_manager()
        return db_manager.health_check()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/memory")
async def memory_health() -> Dict[str, Any]:
    """메모리 사용량 상태 확인"""
    try:
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        
        return {
            "status": "warning" if memory_used_gb > (settings.max_memory_gb * 0.8) else "healthy",
            "memory": {
                "used_gb": round(memory_used_gb, 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2),
                "percentage": memory.percent,
                "limit_gb": settings.max_memory_gb
            }
        }
    except Exception as e:
        logger.error(f"Memory health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/system")
async def system_health() -> Dict[str, Any]:
    """시스템 리소스 상태 확인"""
    try:
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 정보
        memory = psutil.virtual_memory()
        
        # 디스크 정보
        disk = psutil.disk_usage('/')
        
        # 프로세스 정보
        process = psutil.Process()
        process_memory = process.memory_info().rss / (1024**3)
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "percentage": memory.percent
                },
                "disk": {
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                    "percentage": round((disk.used / disk.total) * 100, 2)
                },
                "process": {
                    "memory_gb": round(process_memory, 2),
                    "cpu_percent": process.cpu_percent()
                }
            },
            "uptime": _get_uptime()
        }
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health/cache/cleanup")
async def cleanup_cache():
    """검색 캐시 정리"""
    try:
        db_manager = get_db_manager()
        deleted_count = db_manager.cleanup_cache()
        
        return {
            "status": "success",
            "message": f"Cleaned up {deleted_count} cache entries",
            "deleted_entries": deleted_count
        }
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_uptime() -> str:
    """시스템 업타임 계산"""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        return f"{days}d {hours}h {minutes}m"
    except:
        # Windows나 다른 시스템에서는 psutil 사용
        import time
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        return f"{days}d {hours}h {minutes}m"