#!/usr/bin/env python3
"""
대화 시스템 관련 데이터베이스 스키마 확장
멀티턴 대화, 세션 관리, 컨텍스트 추적을 위한 테이블 정의
"""

import sqlite3
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConversationSchema:
    """대화 시스템 스키마 관리 클래스"""
    
    @staticmethod
    def create_conversation_tables(cursor: sqlite3.Cursor):
        """대화 시스템 관련 테이블 생성"""
        
        # 대화 세션 테이블
        cursor.execute("""
            import sqlite3
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConversationSchema:
    """
    대화 시스템 관련 데이터베이스 스키마 관리 클래스.
    멀티턴 대화, 세션 관리, 컨텍스트 추적을 위한 테이블, 인덱스, 트리거, 뷰를 정의합니다.
    """
    
    @staticmethod
    def create_conversation_tables(cursor: sqlite3.Cursor):
        """
        대화 시스템 관련 테이블 생성.
        세션, 턴, 참조, 주제, 캐시, 패턴 분석을 위한 테이블을 정의합니다.
        """
        
        # conversation_sessions 테이블: 대화 세션의 기본 정보 저장
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE, -- 고유 세션 ID
                user_id TEXT, -- 사용자 ID (선택적)
                title TEXT, -- 세션 제목
                status TEXT DEFAULT 'active',  -- 세션 상태 (active, completed, expired)
                context_summary TEXT, -- 현재 세션의 컨텍스트 요약
                current_topic TEXT, -- 현재 대화 주제
                turn_count INTEGER DEFAULT 0, -- 현재 세션의 턴 수
                max_turns INTEGER DEFAULT 5, -- 세션당 최대 허용 턴 수
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 세션 생성 시각
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 마지막 업데이트 시각
                expires_at DATETIME, -- 세션 만료 시각
                metadata_json TEXT,  -- 추가 메타데이터 (JSON 형태)
                UNIQUE(session_id)
            );
        """)
        
        # conversation_turns 테이블: 실제 질문-답변 쌍 (대화 턴) 저장
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL, -- 세션 ID (conversation_sessions 테이블 참조)
                turn_number INTEGER NOT NULL, -- 세션 내 턴 번호
                user_message TEXT NOT NULL, -- 사용자 질문 메시지
                assistant_message TEXT, -- 어시스턴트 답변 메시지
                search_query TEXT,  -- 답변 생성에 사용된 검색 쿼리
                search_results_json TEXT,  -- 검색 결과 (JSON 형태)
                context_used TEXT,  -- 답변 생성에 활용된 이전 컨텍스트 요약
                response_time_ms INTEGER, -- 응답 시간 (밀리초)
                confidence_score REAL, -- 답변의 신뢰도 점수
                feedback_rating INTEGER,  -- 사용자 피드백 별점 (1-5점)
                feedback_comment TEXT, -- 사용자 피드백 코멘트
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 턴 생성 시각
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
                UNIQUE(session_id, turn_number)
            );
        """)
        
        # conversation_references 테이블: 대화 턴 간의 참조 관계 추적
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_turn_id INTEGER NOT NULL, -- 참조를 시작한 턴 ID
                to_turn_id INTEGER NOT NULL, -- 참조된 턴 ID
                reference_type TEXT NOT NULL,  -- 참조 타입 (예: 'clarification', 'follow_up', 'topic_continuation')
                confidence REAL DEFAULT 1.0, -- 참조의 신뢰도
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 참조 생성 시각
                FOREIGN KEY (from_turn_id) REFERENCES conversation_turns(id) ON DELETE CASCADE,
                FOREIGN KEY (to_turn_id) REFERENCES conversation_turns(id) ON DELETE CASCADE,
                UNIQUE(from_turn_id, to_turn_id, reference_type)
            );
        """)
        
        # conversation_topics 테이블: 대화 세션 내 주제 변화 추적
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL, -- 세션 ID
                topic_name TEXT NOT NULL, -- 주제 이름
                topic_keywords TEXT,  -- 주제를 나타내는 키워드 (쉼표로 구분)
                start_turn INTEGER NOT NULL, -- 주제가 시작된 턴 번호
                end_turn INTEGER, -- 주제가 종료된 턴 번호 (활성 주제는 NULL)
                confidence REAL DEFAULT 1.0, -- 주제 감지의 신뢰도
                is_active BOOLEAN DEFAULT TRUE, -- 현재 활성 주제인지 여부
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 주제 생성 시각
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE
            );
        """)
        
        # session_context_cache 테이블: 세션 컨텍스트의 빠른 조회를 위한 캐시
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_context_cache (
                session_id TEXT PRIMARY KEY, -- 세션 ID
                recent_queries TEXT,  -- 최근 질문들 (JSON 배열)
                recent_topics TEXT,   -- 최근 주제들 (JSON 배열)
                entity_mentions TEXT,  -- 대화에서 언급된 엔티티들 (JSON 객체)
                last_search_results TEXT,  -- 마지막 검색 결과 요약
                context_embedding BLOB,  -- 현재 컨텍스트의 벡터 표현
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 마지막 업데이트 시각
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE
            );
        """)
        
        # conversation_patterns 테이블: 대화 흐름 패턴 분석 및 학습용
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,  -- 패턴 타입 (예: 'question_type', 'follow_up_pattern')
                pattern_key TEXT NOT NULL, -- 패턴을 식별하는 키
                pattern_value TEXT NOT NULL, -- 패턴의 값
                frequency_count INTEGER DEFAULT 1, -- 패턴 발생 빈도
                success_rate REAL DEFAULT 1.0, -- 패턴의 성공률
                last_used DATETIME DEFAULT CURRENT_TIMESTAMP, -- 마지막 사용 시각
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 최초 생성 시각
                UNIQUE(pattern_type, pattern_key)
            );
        """)
        
        logger.info("대화 테이블 생성 완료")
    
    @staticmethod
    def create_conversation_indexes(cursor: sqlite3.Cursor):
        """
        대화 시스템 관련 인덱스 생성.
        테이블의 조회 성능을 최적화하기 위해 자주 사용되는 컬럼에 인덱스를 추가합니다.
        """
        
        indexes = [
            # conversation_sessions 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_sessions_session_id ON conversation_sessions(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_sessions_status ON conversation_sessions(status);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_sessions_created_at ON conversation_sessions(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_sessions_expires_at ON conversation_sessions(expires_at);",
            
            # conversation_turns 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_id ON conversation_turns(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_turns_turn_number ON conversation_turns(turn_number);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_turns_created_at ON conversation_turns(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_turn ON conversation_turns(session_id, turn_number);",
            
            # conversation_references 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_references_from_turn ON conversation_references(from_turn_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_references_to_turn ON conversation_references(to_turn_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_references_type ON conversation_references(reference_type);",
            
            # conversation_topics 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_topics_session_id ON conversation_topics(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_topics_active ON conversation_topics(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_topics_start_turn ON conversation_topics(start_turn);",
            
            # session_context_cache 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_session_context_cache_updated_at ON session_context_cache(updated_at);",
            
            # conversation_patterns 테이블 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_patterns_type ON conversation_patterns(pattern_type);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_patterns_key ON conversation_patterns(pattern_key);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_patterns_last_used ON conversation_patterns(last_used);",
        ]
        
        for sql in indexes:
            try:
                cursor.execute(sql)
            except sqlite3.Error as e:
                logger.warning(f"대화 인덱스 생성 실패: {e}")
        
        logger.info("대화 인덱스 생성 완료")
    
    @staticmethod
    def create_conversation_triggers(cursor: sqlite3.Cursor):
        """
        대화 시스템 관련 트리거 생성.
        데이터 변경 시 자동으로 관련 테이블을 업데이트하거나 상태를 변경합니다.
        """
        
        # 세션 업데이트 시 updated_at 자동 갱신 트리거
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS conversation_sessions_update_time
            AFTER UPDATE ON conversation_sessions
            FOR EACH ROW
            BEGIN
                UPDATE conversation_sessions 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END;
        """)
        
        # 새 턴 추가 시 세션의 turn_count 증가 및 updated_at 갱신 트리거
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS conversation_turns_increment_count
            AFTER INSERT ON conversation_turns
            FOR EACH ROW
            BEGIN
                UPDATE conversation_sessions 
                SET turn_count = turn_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = NEW.session_id;
            END;
        """)
        
        # 세션 컨텍스트 캐시 자동 업데이트 트리거
        # 새로운 턴이 추가될 때마다 해당 세션의 캐시 업데이트 시각을 갱신합니다.
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS conversation_context_cache_update
            AFTER INSERT ON conversation_turns
            FOR EACH ROW
            BEGIN
                INSERT OR REPLACE INTO session_context_cache (
                    session_id, 
                    updated_at
                ) VALUES (
                    NEW.session_id, 
                    CURRENT_TIMESTAMP
                );
            END;
        """)
        
        # 만료된 세션 자동 정리 (상태 변경) 트리거
        # 세션 만료 시각이 현재 시각을 지났고 상태가 'active'일 경우 'expired'로 변경합니다.
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS conversation_sessions_expire_check
            AFTER UPDATE ON conversation_sessions
            FOR EACH ROW
            WHEN NEW.expires_at < CURRENT_TIMESTAMP AND NEW.status = 'active'
            BEGIN
                UPDATE conversation_sessions 
                SET status = 'expired',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END;
        """)
        
        logger.info("대화 트리거 생성 완료")
    
    @staticmethod
    def create_conversation_views(cursor: sqlite3.Cursor):
        """
        대화 시스템 관련 뷰 생성.
        복잡한 조인이나 집계 쿼리를 단순화하여 데이터 조회를 용이하게 합니다.
        """
        
        # active_conversations 뷰: 활성 세션과 최근 턴 정보를 결합하여 조회
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS active_conversations AS
            SELECT 
                cs.session_id,
                cs.title,
                cs.current_topic,
                cs.turn_count,
                cs.max_turns,
                cs.created_at,
                cs.updated_at,
                ct.user_message as last_user_message,
                ct.assistant_message as last_assistant_message,
                ct.created_at as last_turn_time
            FROM conversation_sessions cs
            LEFT JOIN conversation_turns ct ON cs.session_id = ct.session_id
                AND ct.turn_number = cs.turn_count
            WHERE cs.status = 'active' 
                AND cs.expires_at > CURRENT_TIMESTAMP
            ORDER BY cs.updated_at DESC;
        """)
        
        # session_topic_summary 뷰: 세션별 주제 요약 정보 조회
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS session_topic_summary AS
            SELECT 
                session_id,
                GROUP_CONCAT(DISTINCT topic_name) as topics,
                COUNT(id) as topic_count,
                MAX(end_turn) as latest_topic_turn
            FROM conversation_topics
            WHERE is_active = 1
            GROUP BY session_id;
        """)
        
        logger.info("대화 뷰 생성 완료")
    
    @staticmethod
    def migrate_conversation_schema(cursor: sqlite3.Cursor):
        """
        대화 시스템 스키마 마이그레이션 실행.
        모든 대화 관련 테이블, 인덱스, 트리거, 뷰를 생성합니다.
        """
        logger.info("대화 스키마 마이그레이션 시작...")
        
        ConversationSchema.create_conversation_tables(cursor)
        ConversationSchema.create_conversation_indexes(cursor)
        ConversationSchema.create_conversation_triggers(cursor)
        ConversationSchema.create_conversation_views(cursor)
        
        logger.info("대화 스키마 마이그레이션 완료")
    
    @staticmethod
    def cleanup_expired_conversations(cursor: sqlite3.Cursor, days_old: int = 7):
        """
        만료된 대화 데이터 정리.
        지정된 기간보다 오래된 완료되거나 만료된 세션 데이터를 삭제합니다.
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # 오래된 완료/만료 세션 삭제 (CASCADE로 관련 데이터도 함께 삭제)
        cursor.execute("""
            DELETE FROM conversation_sessions 
            WHERE (status IN ('completed', 'expired') 
                   AND updated_at < ?)
               OR (expires_at < ? AND status != 'active')
        """, (cutoff_date, datetime.now()))
        
        deleted_count = cursor.rowcount
        logger.info(f"만료된 대화 세션 {deleted_count}개 정리 완료")
        
        return deleted_count


def apply_conversation_migration(db_manager):
    """
    데이터베이스 매니저를 사용하여 대화 스키마 마이그레이션 적용.
    애플리케이션 시작 시 호출되어 대화 관련 데이터베이스 구조를 최신 상태로 유지합니다.
    """
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        ConversationSchema.migrate_conversation_schema(cursor)
        conn.commit()
        logger.info("대화 마이그레이션 적용 완료")
        """)
        
        # 대화 턴 테이블 (실제 질문-답변 쌍)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_number INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                assistant_message TEXT,
                search_query TEXT,  -- 실제 검색에 사용된 쿼리
                search_results_json TEXT,  -- 검색 결과를 JSON으로 저장
                context_used TEXT,  -- 이전 컨텍스트 요약
                response_time_ms INTEGER,
                confidence_score REAL,
                feedback_rating INTEGER,  -- 1-5 별점
                feedback_comment TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
                UNIQUE(session_id, turn_number)
            );
        """)
        
        # 컨텍스트 참조 테이블 (턴 간 참조 추적)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_turn_id INTEGER NOT NULL,
                to_turn_id INTEGER NOT NULL,
                reference_type TEXT NOT NULL,  -- 'clarification', 'follow_up', 'topic_continuation'
                confidence REAL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_turn_id) REFERENCES conversation_turns(id) ON DELETE CASCADE,
                FOREIGN KEY (to_turn_id) REFERENCES conversation_turns(id) ON DELETE CASCADE,
                UNIQUE(from_turn_id, to_turn_id, reference_type)
            );
        """)
        
        # 대화 주제 추적 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                topic_name TEXT NOT NULL,
                topic_keywords TEXT,  -- 쉼표로 구분된 키워드
                start_turn INTEGER NOT NULL,
                end_turn INTEGER,
                confidence REAL DEFAULT 1.0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE
            );
        """)
        
        # 세션 컨텍스트 캐시 테이블 (빠른 조회를 위한 캐시)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_context_cache (
                session_id TEXT PRIMARY KEY,
                recent_queries TEXT,  -- 최근 질문들 (JSON 배열)
                recent_topics TEXT,   -- 최근 주제들 (JSON 배열)
                entity_mentions TEXT,  -- 언급된 엔티티들 (JSON 객체)
                last_search_results TEXT,  -- 마지막 검색 결과 요약
                context_embedding BLOB,  -- 컨텍스트 벡터 표현
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE
            );
        """)
        
        # 대화 흐름 분석 테이블 (패턴 학습용)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,  -- 'question_type', 'follow_up_pattern', 'topic_transition'
                pattern_key TEXT NOT NULL,
                pattern_value TEXT NOT NULL,
                frequency_count INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 1.0,
                last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pattern_type, pattern_key)
            );
        """)
        
        logger.info("Conversation tables created successfully")
    
    @staticmethod
    def create_conversation_indexes(cursor: sqlite3.Cursor):
        """대화 시스템 관련 인덱스 생성"""
        
        indexes = [
            # conversation_sessions 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_sessions_session_id ON conversation_sessions(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_sessions_status ON conversation_sessions(status);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_sessions_created_at ON conversation_sessions(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_sessions_expires_at ON conversation_sessions(expires_at);",
            
            # conversation_turns 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_id ON conversation_turns(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_turns_turn_number ON conversation_turns(turn_number);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_turns_created_at ON conversation_turns(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_turn ON conversation_turns(session_id, turn_number);",
            
            # conversation_references 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_references_from_turn ON conversation_references(from_turn_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_references_to_turn ON conversation_references(to_turn_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_references_type ON conversation_references(reference_type);",
            
            # conversation_topics 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_topics_session_id ON conversation_topics(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_topics_active ON conversation_topics(is_active);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_topics_start_turn ON conversation_topics(start_turn);",
            
            # session_context_cache 인덱스
            "CREATE INDEX IF NOT EXISTS idx_session_context_cache_updated_at ON session_context_cache(updated_at);",
            
            # conversation_patterns 인덱스
            "CREATE INDEX IF NOT EXISTS idx_conversation_patterns_type ON conversation_patterns(pattern_type);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_patterns_key ON conversation_patterns(pattern_key);",
            "CREATE INDEX IF NOT EXISTS idx_conversation_patterns_last_used ON conversation_patterns(last_used);",
        ]
        
        for sql in indexes:
            try:
                cursor.execute(sql)
            except sqlite3.Error as e:
                logger.warning(f"Conversation index creation failed: {e}")
        
        logger.info("Conversation indexes created successfully")
    
    @staticmethod
    def create_conversation_triggers(cursor: sqlite3.Cursor):
        """대화 시스템 관련 트리거 생성"""
        
        # 세션 업데이트 시 updated_at 자동 갱신
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS conversation_sessions_update_time
            AFTER UPDATE ON conversation_sessions
            FOR EACH ROW
            BEGIN
                UPDATE conversation_sessions 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END;
        """)
        
        # 새 턴 추가 시 세션의 turn_count 증가
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS conversation_turns_increment_count
            AFTER INSERT ON conversation_turns
            FOR EACH ROW
            BEGIN
                UPDATE conversation_sessions 
                SET turn_count = turn_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = NEW.session_id;
            END;
        """)
        
        # 세션 컨텍스트 캐시 자동 업데이트
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS conversation_context_cache_update
            AFTER INSERT ON conversation_turns
            FOR EACH ROW
            BEGIN
                INSERT OR REPLACE INTO session_context_cache (
                    session_id, 
                    updated_at
                ) VALUES (
                    NEW.session_id, 
                    CURRENT_TIMESTAMP
                );
            END;
        """)
        
        # 만료된 세션 자동 정리 (상태 변경)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS conversation_sessions_expire_check
            AFTER UPDATE ON conversation_sessions
            FOR EACH ROW
            WHEN NEW.expires_at < CURRENT_TIMESTAMP AND NEW.status = 'active'
            BEGIN
                UPDATE conversation_sessions 
                SET status = 'expired',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.id;
            END;
        """)
        
        logger.info("Conversation triggers created successfully")
    
    @staticmethod
    def create_conversation_views(cursor: sqlite3.Cursor):
        """대화 시스템 관련 뷰 생성 (편의성을 위한)"""
        
        # 활성 세션과 최근 턴 정보 뷰
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS active_conversations AS
            SELECT 
                cs.session_id,
                cs.title,
                cs.current_topic,
                cs.turn_count,
                cs.max_turns,
                cs.created_at,
                cs.updated_at,
                ct.user_message as last_user_message,
                ct.assistant_message as last_assistant_message,
                ct.created_at as last_turn_time
            FROM conversation_sessions cs
            LEFT JOIN conversation_turns ct ON cs.session_id = ct.session_id
                AND ct.turn_number = cs.turn_count
            WHERE cs.status = 'active' 
                AND cs.expires_at > CURRENT_TIMESTAMP
            ORDER BY cs.updated_at DESC;
        """)
        
        # 세션별 주제 요약 뷰
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS session_topic_summary AS
            SELECT 
                session_id,
                GROUP_CONCAT(DISTINCT topic_name) as topics,
                COUNT(id) as topic_count,
                MAX(end_turn) as latest_topic_turn
            FROM conversation_topics
            WHERE is_active = 1
            GROUP BY session_id;
        """)
        
        logger.info("Conversation views created successfully")
    
    @staticmethod
    def migrate_conversation_schema(cursor: sqlite3.Cursor):
        """대화 시스템 스키마 마이그레이션 실행"""
        logger.info("Starting conversation schema migration...")
        
        ConversationSchema.create_conversation_tables(cursor)
        ConversationSchema.create_conversation_indexes(cursor)
        ConversationSchema.create_conversation_triggers(cursor)
        ConversationSchema.create_conversation_views(cursor)
        
        logger.info("Conversation schema migration completed successfully")
    
    @staticmethod
    def cleanup_expired_conversations(cursor: sqlite3.Cursor, days_old: int = 7):
        """만료된 대화 데이터 정리"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # 오래된 완료/만료 세션 삭제 (CASCADE로 관련 데이터도 삭제)
        cursor.execute("""
            DELETE FROM conversation_sessions 
            WHERE (status IN ('completed', 'expired') 
                   AND updated_at < ?)
               OR (expires_at < ? AND status != 'active')
        """, (cutoff_date, datetime.now()))
        
        deleted_count = cursor.rowcount
        logger.info(f"Cleaned up {deleted_count} expired conversation sessions")
        
        return deleted_count


def apply_conversation_migration(db_manager):
    """데이터베이스 매니저를 사용하여 대화 스키마 마이그레이션 적용"""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        ConversationSchema.migrate_conversation_schema(cursor)
        conn.commit()
        logger.info("Conversation migration applied successfully")