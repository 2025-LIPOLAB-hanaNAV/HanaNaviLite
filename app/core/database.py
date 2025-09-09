import sqlite3
import os
from typing import Optional, Dict, Any
from contextlib import contextmanager
from app.core.config import get_database_path
from app.core.conversation_schema import apply_conversation_migration
from app.core.statistics_schema import apply_statistics_migration
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_database_path()
        self._ensure_db_directory()
        self._initialize_database()

    def _ensure_db_directory(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0,
        )
        # 필수 PRAGMA
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        # 재귀 트리거는 기본 OFF (문제 트리거를 설계상 제거)
        conn.execute("PRAGMA recursive_triggers = OFF;")

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
        with self.get_connection() as conn:
            cur = conn.cursor()

            # documents
            cur.execute("""
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
                );
            """)

            # FTS5 (외부콘텐츠)
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title,
                    content,
                    keywords,
                    content=documents,
                    content_rowid=id,
                    tokenize='porter unicode61'
                );
            """)

            # chunks
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding_vector BLOB,
                    token_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(document_id, chunk_index)
                );
            """)

            # search_cache
            cur.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT NOT NULL UNIQUE,
                    query_text TEXT NOT NULL,
                    search_type TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # system_settings
            cur.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # user_sessions
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    user_agent TEXT,
                    ip_address TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    query_count INTEGER DEFAULT 0
                );
            """)

            # query_logs
            cur.execute("""
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
                    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
                );
            """)

            self._create_indexes(cur)
            self._create_triggers(cur)
            
            # Apply conversation schema migration
            apply_conversation_migration(self)
            
            # Apply statistics schema migration
            apply_statistics_migration(self)

            logger.info("Database initialized successfully")

    def _create_indexes(self, cur):
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);",
            "CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);",
            "CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);",
            "CREATE INDEX IF NOT EXISTS idx_search_cache_query_hash ON search_cache(query_hash);",
            "CREATE INDEX IF NOT EXISTS idx_search_cache_created_at ON search_cache(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_query_logs_session_id ON query_logs(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);",
        ]
        for sql in indexes:
            try:
                cur.execute(sql)
            except sqlite3.Error as e:
                logger.warning(f"Index creation failed: {e}")

    def _create_triggers(self, cur):
        """외부콘텐츠 FTS5 동기화 트리거만 생성 (재귀 유발 트리거 금지)"""

        # 기존 트리거 정리
        cur.execute("DROP TRIGGER IF EXISTS documents_fts_insert;")
        cur.execute("DROP TRIGGER IF EXISTS documents_fts_update;")
        cur.execute("DROP TRIGGER IF EXISTS documents_fts_delete;")
        # 의도적으로 updated_at 자동 갱신 트리거는 생성하지 않음
        # (AFTER UPDATE에서 documents를 다시 UPDATE하면 재귀 유발)

        # INSERT → FTS 색인
        cur.execute("""
            CREATE TRIGGER documents_fts_insert
            AFTER INSERT ON documents
            BEGIN
                INSERT INTO documents_fts(rowid, title, content, keywords)
                VALUES (new.id, new.title, new.content, new.keywords);
            END;
        """)

        # UPDATE → FTS 재색인 (delete → insert 패턴)
        cur.execute("""
            CREATE TRIGGER documents_fts_update
            AFTER UPDATE ON documents
            BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content, keywords)
                VALUES ('delete', old.id, old.title, old.content, old.keywords);

                INSERT INTO documents_fts(rowid, title, content, keywords)
                VALUES (new.id, new.title, new.content, new.keywords);
            END;
        """)

        # DELETE → FTS에서 제거
        cur.execute("""
            CREATE TRIGGER documents_fts_delete
            AFTER DELETE ON documents
            BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content, keywords)
                VALUES ('delete', old.id, old.title, old.content, old.keywords);
            END;
        """)

    def health_check(self) -> Dict[str, Any]:
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.execute("SELECT COUNT(*) FROM documents")
                doc_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM search_cache")
                cache_count = cur.fetchone()[0]
                cur.execute("PRAGMA page_count")
                page_count = cur.fetchone()[0]
                cur.execute("PRAGMA page_size")
                page_size = cur.fetchone()[0]
                db_size_mb = (page_count * page_size) / (1024 * 1024)
                return {
                    "status": "healthy",
                    "database_path": self.db_path,
                    "documents_count": doc_count,
                    "chunks_count": chunk_count,
                    "cache_count": cache_count,
                    "database_size_mb": round(db_size_mb, 2),
                    "wal_mode": True,
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def get_setting(self, key: str, default_value: Optional[str] = None) -> Optional[str]:
        """시스템 설정 값을 조회합니다."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return default_value

    def set_setting(self, key: str, value: str, description: Optional[str] = None):
        """시스템 설정 값을 저장하거나 업데이트합니다."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO system_settings (key, value, description) VALUES (?, ?, ?)",
                (key, value, description),
            )
            conn.commit()


# 전역 인스턴스
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    return db_manager
