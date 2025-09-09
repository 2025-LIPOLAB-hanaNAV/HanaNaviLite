#!/usr/bin/env python3
"""
사용 통계 API
애플리케이션 사용량, 성능, 사용자 피드백 통계를 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

from app.core.database import get_db_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/usage", response_model=Dict[str, Any])
async def get_usage_statistics(
    period: str = Query("daily", description="조회 기간: daily, monthly, total"),
    date: Optional[str] = Query(None, description="조회 날짜 (YYYY-MM-DD 또는 YYYY-MM)")
):
    """
    애플리케이션 사용 통계를 조회합니다.
    - **period**: 'daily', 'monthly', 'total'
    - **date**: 특정 날짜 또는 월 (period가 'daily' 또는 'monthly'일 때 사용)
    """
    """
    애플리케이션 사용 통계를 조회합니다.
    총 쿼리 수, 고유 사용자 수, 평균 응답 시간 등 다양한 사용 지표를 제공합니다.
    """
    db_manager = get_db_manager()
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 일별, 월별, 전체 기간별 사용 통계를 조회합니다.
            if period == "daily":
                if not date:
                    date = datetime.now().strftime('%Y-%m-%d')
                cursor.execute("SELECT * FROM usage_metrics WHERE metric_date = ? AND period_type = 'daily'", (date,))
                row = cursor.fetchone()
                if row:
                    return {
                        "metric_date": row[1],
                        "period_type": row[2],
                        "total_queries": row[3],
                        "unique_users": row[4],
                        "avg_response_time_ms": row[5],
                        "successful_queries": row[6],
                        "failed_queries": row[7],
                        "total_sessions": row[8],
                        "avg_turns_per_session": row[9],
                        "updated_at": row[10]
                    }
                return {"message": "No data for this date"}
            
            elif period == "monthly":
                if not date:
                    date = datetime.now().strftime('%Y-%m')
                cursor.execute("SELECT * FROM monthly_usage_summary WHERE month = ?", (date,))
                row = cursor.fetchone()
                if row:
                    return {
                        "month": row[0],
                        "total_queries": row[1],
                        "unique_users": row[2],
                        "avg_response_time_ms": row[3],
                        "successful_queries": row[4],
                        "failed_queries": row[5],
                        "total_sessions": row[6]
                    }
                return {"message": "No data for this month"}
            
            elif period == "total":
                cursor.execute("""
                    SELECT 
                        SUM(total_queries), 
                        SUM(unique_users), 
                        AVG(avg_response_time_ms), 
                        SUM(successful_queries), 
                        SUM(failed_queries), 
                        SUM(total_sessions)
                    FROM usage_metrics WHERE period_type = 'daily'
                """)
                row = cursor.fetchone()
                if row:
                    return {
                        "total_queries": row[0] or 0,
                        "unique_users": row[1] or 0,
                        "avg_response_time_ms": round(row[2], 2) if row[2] else 0.0,
                        "successful_queries": row[3] or 0,
                        "failed_queries": row[4] or 0,
                        "total_sessions": row[5] or 0
                    }
                return {"message": "No total data available"}
            
            else:
                raise HTTPException(status_code=400, detail="Invalid period. Use 'daily', 'monthly', or 'total'.")
                
    except Exception as e:
        logger.error(f"Failed to get usage statistics: {e}")
        raise HTTPException(status_code=500, detail=f"통계 정보 조회 중 오류 발생: {e}")


@router.get("/popular_queries", response_model=List[Dict[str, Any]])
async def get_popular_queries(top_k: int = Query(10, ge=1, le=100)):
    """
    가장 인기 있는 검색어/질문 목록을 조회합니다.
    사용자들이 자주 검색하거나 질문하는 키워드를 파악하는 데 사용됩니다.
    """
    db_manager = get_db_manager()
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT query_text, hit_count, last_hit_at FROM popular_queries ORDER BY hit_count DESC LIMIT ?", (top_k,))
            rows = cursor.fetchall()
            
            return [{
                "query_text": row[0],
                "hit_count": row[1],
                "last_hit_at": row[2]
            } for row in rows]
            
    except Exception as e:
        logger.error(f"Failed to get popular queries: {e}")
        raise HTTPException(status_code=500, detail=f"인기 검색어 조회 중 오류 발생: {e}")


@router.get("/document_usage", response_model=List[Dict[str, Any]])
async def get_document_usage(top_k: int = Query(10, ge=1, le=100)):
    """
    가장 많이 조회되거나 검색된 문서 목록을 조회합니다.
    어떤 문서가 사용자들에게 유용한지 파악하는 데 사용됩니다.
    """
    db_manager = get_db_manager()
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            # documents 테이블과 조인하여 문서 제목도 함께 가져옴
            cursor.execute("""
                SELECT d.title, du.view_count, du.search_hit_count, du.last_accessed_at
                FROM document_usage du
                JOIN documents d ON du.document_id = d.id
                ORDER BY (du.view_count + du.search_hit_count) DESC LIMIT ?
            """, (top_k,))
            rows = cursor.fetchall()
            
            return [{
                "title": row[0],
                "view_count": row[1],
                "search_hit_count": row[2],
                "last_accessed_at": row[3]
            } for row in rows]
            
    except Exception as e:
        logger.error(f"Failed to get document usage: {e}")
        raise HTTPException(status_code=500, detail=f"문서 사용량 조회 중 오류 발생: {e}")


@router.get("/feedback_summary", response_model=Dict[str, Any])
async def get_feedback_summary(
    date: Optional[str] = Query(None, description="조회 날짜 (YYYY-MM-DD)")
):
    """
    사용자 피드백 요약을 조회합니다.
    특정 날짜에 대한 긍정, 부정, 중립 피드백 수와 평균 별점을 제공합니다.
    """
    db_manager = get_db_manager()
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            cursor.execute("SELECT * FROM feedback_summary WHERE feedback_date = ?", (date,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "feedback_date": row[1],
                    "positive_count": row[2],
                    "negative_count": row[3],
                    "neutral_count": row[4],
                    "avg_rating": row[5],
                    "updated_at": row[6]
                }
            return {"message": "No feedback data for this date"}
            
    except Exception as e:
        logger.error(f"Failed to get feedback summary: {e}")
        raise HTTPException(status_code=500, detail=f"피드백 요약 조회 중 오류 발생: {e}")


from app.core.performance_tuner import get_performance_tuner, PerformanceTuner

@router.post("/tune_weights", response_model=Dict[str, Any])
async def tune_weights(
    strategy: str = Query("basic_optimization", description="튜닝 전략"),
    tuner: PerformanceTuner = Depends(get_performance_tuner)
):
    """
    검색 가중치를 튜닝합니다.
    시스템 성능 지표에 따라 검색 엔진의 벡터 및 IR 가중치를 자동으로 조정합니다.
    """
    try:
        tuner.tune_search_weights(strategy)
        current_weights = tuner.get_search_weights()
        return {"message": "Search weights tuned successfully", "current_weights": current_weights}
    except Exception as e:
        logger.error(f"Failed to tune weights: {e}")
        raise HTTPException(status_code=500, detail=f"가중치 튜닝 중 오류 발생: {e}")


@router.get("/popular_queries", response_model=List[Dict[str, Any]])
async def get_popular_queries(top_k: int = Query(10, ge=1, le=100)):
    """
    가장 인기 있는 검색어/질문 목록을 조회합니다.
    - **top_k**: 반환할 검색어 개수
    """
    db_manager = get_db_manager()
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT query_text, hit_count, last_hit_at FROM popular_queries ORDER BY hit_count DESC LIMIT ?", (top_k,))
            rows = cursor.fetchall()
            
            return [{
                "query_text": row[0],
                "hit_count": row[1],
                "last_hit_at": row[2]
            } for row in rows]
            
    except Exception as e:
        logger.error(f"Failed to get popular queries: {e}")
        raise HTTPException(status_code=500, detail=f"인기 검색어 조회 중 오류 발생: {e}")


@router.get("/document_usage", response_model=List[Dict[str, Any]])
async def get_document_usage(top_k: int = Query(10, ge=1, le=100)):
    """
    가장 많이 조회되거나 검색된 문서 목록을 조회합니다.
    - **top_k**: 반환할 문서 개수
    """
    db_manager = get_db_manager()
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            # documents 테이블과 조인하여 문서 제목도 함께 가져옴
            cursor.execute("""
                SELECT d.title, du.view_count, du.search_hit_count, du.last_accessed_at
                FROM document_usage du
                JOIN documents d ON du.document_id = d.id
                ORDER BY (du.view_count + du.search_hit_count) DESC LIMIT ?
            """, (top_k,))
            rows = cursor.fetchall()
            
            return [{
                "title": row[0],
                "view_count": row[1],
                "search_hit_count": row[2],
                "last_accessed_at": row[3]
            } for row in rows]
            
    except Exception as e:
        logger.error(f"Failed to get document usage: {e}")
        raise HTTPException(status_code=500, detail=f"문서 사용량 조회 중 오류 발생: {e}")


@router.get("/feedback_summary", response_model=Dict[str, Any])
async def get_feedback_summary(
    date: Optional[str] = Query(None, description="조회 날짜 (YYYY-MM-DD)")
):
    """
    사용자 피드백 요약을 조회합니다.
    - **date**: 특정 날짜 (YYYY-MM-DD)
    """
    db_manager = get_db_manager()
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            cursor.execute("SELECT * FROM feedback_summary WHERE feedback_date = ?", (date,))
            row = cursor.fetchone()
            
            if row:
                return {
                    "feedback_date": row[1],
                    "positive_count": row[2],
                    "negative_count": row[3],
                    "neutral_count": row[4],
                    "avg_rating": row[5],
                    "updated_at": row[6]
                }
            return {"message": "No feedback data for this date"}
            
    except Exception as e:
        logger.error(f"Failed to get feedback summary: {e}")
        raise HTTPException(status_code=500, detail=f"피드백 요약 조회 중 오류 발생: {e}")


from app.core.performance_tuner import get_performance_tuner, PerformanceTuner

@router.post("/tune_weights", response_model=Dict[str, Any])
async def tune_weights(
    strategy: str = Query("basic_optimization", description="튜닝 전략"),
    tuner: PerformanceTuner = Depends(get_performance_tuner)
):
    """
    검색 가중치를 튜닝합니다.
    - **strategy**: 튜닝 전략 (예: basic_optimization)
    """
    try:
        tuner.tune_search_weights(strategy)
        current_weights = tuner.get_search_weights()
        return {"message": "Search weights tuned successfully", "current_weights": current_weights}
    except Exception as e:
        logger.error(f"Failed to tune weights: {e}")
        raise HTTPException(status_code=500, detail=f"가중치 튜닝 중 오류 발생: {e}")
