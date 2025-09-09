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
        """사용 통계 관련 테이블 생성"""
        
        # 일별/월별 집계 메트릭스 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_date TEXT NOT NULL UNIQUE, -- YYYY-MM-DD 또는 YYYY-MM
                period_type TEXT NOT NULL, -- 'daily', 'monthly'
                total_queries INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0,
                avg_response_time_ms REAL DEFAULT 0.0,
                successful_queries INTEGER DEFAULT 0,
                failed_queries INTEGER DEFAULT 0,
                total_sessions INTEGER DEFAULT 0,
                avg_turns_per_session REAL DEFAULT 0.0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(metric_date, period_type)
            );
        """)
        
        # 인기 검색어/질문 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS popular_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL UNIQUE,
                query_hash TEXT NOT NULL UNIQUE,
                hit_count INTEGER DEFAULT 0,
                last_hit_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 문서 사용량/인기 문서 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                view_count INTEGER DEFAULT 0,
                search_hit_count INTEGER DEFAULT 0,
                last_accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                UNIQUE(document_id)
            );
        """)
        
        # 사용자 피드백 요약 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_date TEXT NOT NULL UNIQUE, -- YYYY-MM-DD
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                neutral_count INTEGER DEFAULT 0,
                avg_rating REAL DEFAULT 0.0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        logger.info("Statistics tables created successfully")
    
    @staticmethod
    def create_statistics_indexes(cursor: sqlite3.Cursor):
        """사용 통계 관련 인덱스 생성"""
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_usage_metrics_date ON usage_metrics(metric_date);",
            "CREATE INDEX IF NOT EXISTS idx_popular_queries_hit_count ON popular_queries(hit_count DESC);",
            "CREATE INDEX IF NOT EXISTS idx_document_usage_view_count ON document_usage(view_count DESC);",
            "CREATE INDEX IF NOT EXISTS idx_document_usage_search_hit_count ON document_usage(search_hit_count DESC);",
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
        """사용 통계 관련 트리거 생성"""
        # query_logs 테이블에 INSERT 시 popular_queries 업데이트
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
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_daily_usage_metrics_on_insert
            AFTER INSERT ON query_logs
            FOR EACH ROW
            BEGIN
                INSERT OR IGNORE INTO usage_metrics (metric_date, period_type, total_queries, successful_queries, failed_queries, updated_at)
                VALUES (strftime('%Y-%m-%d', NEW.created_at), 'daily', 0, 0, 0, CURRENT_TIMESTAMP);
                
                UPDATE usage_metrics
                SET total_queries = total_queries + 1,
                    successful_queries = successful_queries + CASE WHEN NEW.success = 1 THEN 1 ELSE 0 END,
                    failed_queries = failed_queries + CASE WHEN NEW.success = 0 THEN 1 ELSE 0 END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE metric_date = strftime('%Y-%m-%d', NEW.created_at) AND period_type = 'daily';
            END;
        """)
        
        # conversation_sessions 테이블에 INSERT 시 daily usage_metrics의 unique_users, total_sessions 업데이트
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
        """사용 통계 관련 뷰 생성"""
        
        # 월별 사용량 요약 뷰
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
        """사용 통계 스키마 마이그레이션 실행"""
        logger.info("Starting statistics schema migration...")
        
        StatisticsSchema.create_statistics_tables(cursor)
        StatisticsSchema.create_statistics_indexes(cursor)
        StatisticsSchema.create_statistics_triggers(cursor)
        StatisticsSchema.create_statistics_views(cursor)
        
        logger.info("Statistics schema migration completed successfully")


def apply_statistics_migration(db_manager):
    """데이터베이스 매니저를 사용하여 사용 통계 스키마 마이그레이션 적용"""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        StatisticsSchema.migrate_statistics_schema(cursor)
        conn.commit()
        logger.info("Statistics migration applied successfully")
