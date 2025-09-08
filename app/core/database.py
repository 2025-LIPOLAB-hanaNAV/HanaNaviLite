import sqlite3
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from app.core.config import get_database_path, settings
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_database_path()
        self._ensure_db_directory()
        self._initialize_database()
    
    def _ensure_db_directory(self):
        """데이터베이스 디렉토리가 존재하는지 확인하고 없으면 생성"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
    
    @contextmanager
    def get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0
        )
        # WAL 모드 활성화 (동시성 향상)
        conn.execute("PRAGMA journal_mode=WAL")
        # 외래 키 제약 조건 활성화
        conn.execute("PRAGMA foreign_keys=ON")
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _initialize_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 메타데이터 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    file_size INTEGER NOT NULL,
                    file_type TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    summary TEXT,
                    keywords TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME,
                    status TEXT DEFAULT 'pending'
                )
            """)
            
            # FTS5 전문검색 테이블
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title,
                    content,
                    keywords,
                    content=documents,
                    content_rowid=id,
                    tokenize='porter unicode61'
                )
            """)
            
            # 청크 테이블 (벡터 검색용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding_vector BLOB,
                    token_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
                    UNIQUE(document_id, chunk_index)
                )
            """)
            
            # 검색 캐시 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT NOT NULL UNIQUE,
                    query_text TEXT NOT NULL,
                    search_type TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 시스템 설정 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 사용자 세션 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    user_agent TEXT,
                    ip_address TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    query_count INTEGER DEFAULT 0
                )
            """)
            
            # 쿼리 로그 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    query_text TEXT NOT NULL,
                    search_type TEXT,
                    results_count INTEGER,
                    response_time_ms INTEGER,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES user_sessions (session_id)
                )
            """)
            
            # 인덱스 생성
            self._create_indexes(cursor)
            
            # 트리거 생성
            self._create_triggers(cursor)
            
            logger.info("Database initialized successfully")
    
    def _create_indexes(self, cursor):
        """성능 최적화를 위한 인덱스 생성"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)",
            "CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type)",
            "CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_search_cache_query_hash ON search_cache(query_hash)",
            "CREATE INDEX IF NOT EXISTS idx_search_cache_created_at ON search_cache(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_query_logs_session_id ON query_logs(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except sqlite3.Error as e:
                logger.warning(f"Index creation failed: {e}")
    
    def _create_triggers(self, cursor):
        """데이터 동기화를 위한 트리거 생성"""
        # FTS5 테이블 동기화 트리거
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_insert 
            AFTER INSERT ON documents 
            BEGIN
                INSERT INTO documents_fts(rowid, title, content, keywords)
                VALUES (new.id, new.title, new.content, new.keywords);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_update 
            AFTER UPDATE ON documents 
            BEGIN
                UPDATE documents_fts SET 
                    title = new.title,
                    content = new.content,
                    keywords = new.keywords
                WHERE rowid = new.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_delete 
            AFTER DELETE ON documents 
            BEGIN
                DELETE FROM documents_fts WHERE rowid = old.id;
            END
        """)
        
        # updated_at 자동 업데이트 트리거
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_updated_at 
            AFTER UPDATE ON documents 
            BEGIN
                UPDATE documents SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = new.id;
            END
        """)
    
    def health_check(self) -> Dict[str, Any]:
        """데이터베이스 상태 확인"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 기본 연결 테스트
                cursor.execute("SELECT 1")
                
                # 테이블 카운트
                cursor.execute("SELECT COUNT(*) FROM documents")
                doc_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM search_cache")
                cache_count = cursor.fetchone()[0]
                
                # 데이터베이스 크기
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                db_size_mb = (page_count * page_size) / (1024 * 1024)
                
                return {
                    "status": "healthy",
                    "database_path": self.db_path,
                    "documents_count": doc_count,
                    "chunks_count": chunk_count,
                    "cache_count": cache_count,
                    "database_size_mb": round(db_size_mb, 2),
                    "wal_mode": True
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def cleanup_cache(self, max_age_hours: int = 24, max_entries: int = 1000):
        """검색 캐시 정리"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 오래된 캐시 엔트리 삭제
            cursor.execute("""
                DELETE FROM search_cache 
                WHERE created_at < datetime('now', '-{} hours')
            """.format(max_age_hours))
            
            # 최대 엔트리 수 제한
            cursor.execute("""
                DELETE FROM search_cache 
                WHERE id NOT IN (
                    SELECT id FROM search_cache 
                    ORDER BY hit_count DESC, last_accessed DESC 
                    LIMIT ?
                )
            """, (max_entries,))
            
            deleted_count = cursor.rowcount
            logger.info(f"Cleaned up {deleted_count} cache entries")
            return deleted_count


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """데이터베이스 매니저 인스턴스 반환"""
    return db_manager