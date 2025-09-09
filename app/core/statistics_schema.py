#!/usr/bin/env python3
"""
사용 통계 및 대시보드 관련 데이터베이스 스키마
애플리케이션 사용량, 성능, 사용자 피드백 등을 추적하기 위한 테이블 정의
"""

import sqlite3
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StatisticsSchema:
    """사용 통계 스키마 관리 클래스"""
    
    @staticmethod
    def create_statistics_tables(cursor: sqlite3.Cursor):
        """
        사용 통계 관련 테이블 생성.
        애플리케이션의 사용량, 인기 검색어, 문서 사용량, 피드백 요약 등을 저장합니다.
        """
        
        # 일별/월별 집계 메트릭스 테이블 (usage_metrics)
        # 총 쿼리 수, 고유 사용자 수, 평균 응답 시간 등 핵심 사용 지표를 집계합니다。
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_date TEXT NOT NULL UNIQUE, -- YYYY-MM-DD 또는 YYYY-MM (집계 기준 날짜/월)
                period_type TEXT NOT NULL, -- 'daily', 'monthly' (집계 기간 타입)
                total_queries INTEGER DEFAULT 0, -- 총 쿼리 수
                unique_users INTEGER DEFAULT 0, -- 고유 사용자 수
                avg_response_time_ms REAL DEFAULT 0.0, -- 평균 응답 시간 (밀리초)
                successful_queries INTEGER DEFAULT 0, -- 성공한 쿼리 수
                failed_queries INTEGER DEFAULT 0, -- 실패한 쿼리 수
                total_sessions INTEGER DEFAULT 0, -- 총 세션 수
                avg_turns_per_session REAL DEFAULT 0.0, -- 세션당 평균 턴 수
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 마지막 업데이트 시각
                UNIQUE(metric_date, period_type)
            );
        """)
        
        # 인기 검색어/질문 테이블 (popular_queries)
        # 사용자들이 자주 검색하거나 질문하는 쿼리를 추적하고 집계합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS popular_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL UNIQUE, -- 검색어/질문 텍스트
                query_hash TEXT NOT NULL UNIQUE, -- 쿼리 텍스트의 해시 (중복 방지 및 빠른 조회)
                hit_count INTEGER DEFAULT 0, -- 조회/사용 횟수
                last_hit_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 마지막 조회 시각
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 최초 생성 시각
            );
        """)
        
        # 문서 사용량/인기 문서 테이블 (document_usage)
        # 문서별 조회 수, 검색 히트 수 등 문서 사용 통계를 추적합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL, -- 문서 ID (documents 테이블 참조)
                view_count INTEGER DEFAULT 0, -- 조회 횟수
                search_hit_count INTEGER DEFAULT 0, -- 검색 결과에 노출된 횟수
                last_accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 마지막 접근 시각
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 최초 생성 시각
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE(document_id)
            );
        """)
        
        # 사용자 피드백 요약 테이블 (feedback_summary)
        # 일별 사용자 피드백 (긍정/부정/중립)을 집계하고 평균 별점을 계산합니다.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_date TEXT NOT NULL UNIQUE, -- YYYY-MM-DD (피드백 집계 날짜)
                positive_count INTEGER DEFAULT 0, -- 긍정 피드백 수 (4, 5점)
                negative_count INTEGER DEFAULT 0, -- 부정 피드백 수 (1, 2점)
                neutral_count INTEGER DEFAULT 0, -- 중립 피드백 수 (3점)
                avg_rating REAL DEFAULT 0.0, -- 평균 별점
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 마지막 업데이트 시각
            );
        """)
        
        logger.info("Statistics tables created successfully")
    
    @staticmethod
    def create_statistics_indexes(cursor: sqlite3.Cursor):
        """
        사용 통계 관련 인덱스 생성.
        테이블의 조회 성능을 최적화하기 위한 인덱스를 정의합니다.
        """
        
        indexes = [
            # usage_metrics 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_usage_metrics_date ON usage_metrics(metric_date);",
            # popular_queries 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_popular_queries_hit_count ON popular_queries(hit_count DESC);",
            # document_usage 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_document_usage_view_count ON document_usage(view_count DESC);",
            "CREATE INDEX IF NOT EXISTS idx_document_usage_search_hit_count ON document_usage(search_hit_count DESC);",
            # feedback_summary 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_feedback_summary_date ON feedback_summary(feedback_date);",
        ]
        
        for sql in indexes:
            try:
                cursor.execute(sql)
            except sqlite3.Error as e:
                logger.warning(f"Statistics index creation failed: {e}")
        
        logger.info("Statistics indexes created successfully")
    
    @staticmethod
    def create_statistics_triggers(cursor: sqlite3.Cursor):
        """
        사용 통계 관련 트리거 생성.
        데이터 변경 시 자동으로 통계 테이블을 업데이트하는 트리거를 정의합니다.
        """
        # query_logs 테이블에 INSERT 시 popular_queries 업데이트
        # 새로운 쿼리 로그가 추가될 때마다 인기 검색어 테이블을 갱신합니다.
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_popular_queries_on_insert
            AFTER INSERT ON query_logs
            FOR EACH ROW
            BEGIN
                INSERT OR IGNORE INTO popular_queries (query_text, query_hash, hit_count, last_hit_at)
                VALUES (NEW.query_text, NEW.query_text, 1, NEW.created_at); -- query_hash는 일단 query_text로
                
                UPDATE popular_queries
                SET hit_count = hit_count + 1,
                    last_hit_at = NEW.created_at
                WHERE query_hash = NEW.query_text;
            END;
        """)
        
        # query_logs 테이블에 INSERT 시 daily usage_metrics 업데이트
        # 새로운 쿼리 로그가 추가될 때마다 일별 사용량 메트릭스를 갱신합니다.
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_daily_usage_metrics_on_insert
            AFTER INSERT ON query_logs
            FOR EACH ROW
            BEGIN
                INSERT OR IGNORE INTO usage_metrics (metric_date, period_type, total_queries, successful_queries, failed_queries, updated_at)
                VALUES (strftime('%Y-%m-%d', NEW.created.at), 'daily', 0, 0, 0, CURRENT_TIMESTAMP);
                
                UPDATE usage_metrics
                SET total_queries = total_queries + 1,
                    successful_queries = successful_queries + CASE WHEN NEW.success = 1 THEN 1 ELSE 0 END,
                    failed_queries = failed_queries + CASE WHEN NEW.success = 0 THEN 1 ELSE 0 END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE metric_date = strftime('%Y-%m-%d', NEW.created_at) AND period_type = 'daily';
            END;
        """)
        
        # conversation_sessions 테이블에 INSERT 시 daily usage_metrics의 unique_users, total_sessions 업데이트
        # 새로운 세션이 생성될 때마다 일별 고유 사용자 및 총 세션 수를 갱신합니다.
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_daily_session_metrics_on_insert
            AFTER INSERT ON conversation_sessions
            FOR EACH ROW
            BEGIN
                INSERT OR IGNORE INTO usage_metrics (metric_date, period_type, total_sessions, unique_users, updated_at)
                VALUES (strftime('%Y-%m-%d', NEW.created_at), 'daily', 0, 0, CURRENT_TIMESTAMP);
                
                UPDATE usage_metrics
                SET total_sessions = total_sessions + 1,
                    unique_users = unique_users + CASE WHEN NOT EXISTS (SELECT 1 FROM conversation_sessions WHERE user_id = NEW.user_id AND strftime('%Y-%m-%d', created_at) = strftime('%Y-%m-%d', NEW.created_at) AND session_id != NEW.session_id) THEN 1 ELSE 0 END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE metric_date = strftime('%Y-%m-%d', NEW.created_at) AND period_type = 'daily';
            END;
        """)
        
        # conversation_turns 테이블에 feedback_rating 업데이트 시 feedback_summary 업데이트
        # 턴에 대한 피드백이 제출될 때마다 일별 피드백 요약 테이블을 갱신합니다.
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_feedback_summary_on_turn_update
            AFTER UPDATE OF feedback_rating ON conversation_turns
            FOR EACH ROW
            WHEN NEW.feedback_rating IS NOT NULL AND OLD.feedback_rating IS NULL -- 피드백이 새로 추가될 때만
            BEGIN
                INSERT OR IGNORE INTO feedback_summary (feedback_date, positive_count, negative_count, neutral_count, avg_rating, updated_at)
                VALUES (strftime('%Y-%m-%d', NEW.created_at), 0, 0, 0, 0.0, CURRENT_TIMESTAMP);
                
                UPDATE feedback_summary
                SET positive_count = positive_count + CASE WHEN NEW.feedback_rating >= 4 THEN 1 ELSE 0 END,
                    negative_count = negative_count + CASE WHEN NEW.feedback_rating <= 2 THEN 1 ELSE 0 END,
                    neutral_count = neutral_count + CASE WHEN NEW.feedback_rating = 3 THEN 1 ELSE 0 END,
                    avg_rating = ( (positive_count + negative_count + neutral_count) * avg_rating + NEW.feedback_rating ) / (positive_count + negative_count + neutral_count + 1),
                    updated_at = CURRENT_TIMESTAMP
                WHERE feedback_date = strftime('%Y-%m-%d', NEW.created_at);
            END;
        """)
        
        logger.info("Statistics triggers created successfully")
    
    @staticmethod
    def create_statistics_views(cursor: sqlite3.Cursor):
        """
        사용 통계 관련 뷰 생성.
        복잡한 쿼리를 단순화하고 특정 통계 데이터를 쉽게 조회할 수 있도록 뷰를 정의합니다.
        """
        
        # 월별 사용량 요약 뷰
        # 일별 사용량 메트릭스를 기반으로 월별 총 사용량을 집계합니다.
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS monthly_usage_summary AS
            SELECT
                strftime('%Y-%m', metric_date) as month,
                SUM(total_queries) as total_queries,
                SUM(unique_users) as unique_users,
                AVG(avg_response_time_ms) as avg_response_time_ms,
                SUM(successful_queries) as successful_queries,
                SUM(failed_queries) as failed_queries,
                SUM(total_sessions) as total_sessions
            FROM usage_metrics
            WHERE period_type = 'daily'
            GROUP BY month
            ORDER BY month DESC;
        """)
        
        logger.info("Statistics views created successfully")
    
    @staticmethod
    def migrate_statistics_schema(cursor: sqlite3.Cursor):
        """
        사용 통계 스키마 마이그레이션 실행.
        모든 통계 관련 테이블, 인덱스, 트리거, 뷰를 생성합니다.
        """
        logger.info("Starting statistics schema migration...")
        
        StatisticsSchema.create_statistics_tables(cursor)
        StatisticsSchema.create_statistics_indexes(cursor)
        StatisticsSchema.create_statistics_triggers(cursor)
        StatisticsSchema.create_statistics_views(cursor)
        
        logger.info("Statistics schema migration completed successfully")


def apply_statistics_migration(db_manager):
    """
    데이터베이스 매니저를 사용하여 사용 통계 스키마 마이그레이션 적용.
    애플리케이션 시작 시 호출되어 통계 관련 데이터베이스 구조를 최신 상태로 유지합니다.
    """
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        StatisticsSchema.migrate_statistics_schema(cursor)
        conn.commit()
        logger.info("Statistics migration applied successfully")
