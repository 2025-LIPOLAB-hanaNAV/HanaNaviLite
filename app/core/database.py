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
    """
    SQLite 데이터베이스를 관리하는 클래스.
    데이터베이스 연결, 초기화, 스키마 마이그레이션, 설정 관리 등을 담당합니다.
    """
    def __init__(self, db_path: Optional[str] = None):
        # 데이터베이스 파일 경로 설정 (기본값: get_database_path()에서 가져옴)
        self.db_path = db_path or get_database_path()
        # 데이터베이스 파일이 저장될 디렉토리가 존재하는지 확인하고 없으면 생성
        self._ensure_db_directory()
        # 데이터베이스 초기화 (테이블, 인덱스, 트리거 생성 및 마이그레이션 적용)
        self._initialize_database()

    def _ensure_db_directory(self):
        """
        데이터베이스 파일이 저장될 디렉토리가 존재하는지 확인하고, 없으면 생성합니다.
        """
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"데이터베이스 디렉토리 생성: {db_dir}")

    @contextmanager
    def get_connection(self):
        """
        데이터베이스 연결을 제공하는 컨텍스트 매니저.
        연결을 자동으로 열고 닫으며, 트랜잭션 관리 (커밋/롤백)를 수행합니다.
        """
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False, # 멀티스레드 환경에서 안전하게 사용하기 위함
            timeout=30.0, # 연결 타임아웃 설정
        )
        # 필수 PRAGMA 설정: 데이터베이스 성능 및 무결성 관련 설정
        conn.execute("PRAGMA foreign_keys = ON;") # 외래 키 제약 조건 활성화
        conn.execute("PRAGMA journal_mode = WAL;") # WAL (Write-Ahead Logging) 모드 활성화 (동시성 및 복구 성능 향상)
        conn.execute("PRAGMA synchronous = NORMAL;") # 동기화 모드 설정 (성능과 데이터 안전성 균형)
        # 재귀 트리거는 기본 OFF (설계상 재귀를 유발하는 트리거를 사용하지 않음)
        conn.execute("PRAGMA recursive_triggers = OFF;")

        try:
            yield conn # 연결 객체를 호출자에게 전달
            conn.commit() # 작업 성공 시 트랜잭션 커밋
        except Exception as e:
            conn.rollback() # 예외 발생 시 트랜잭션 롤백
            logger.error(f"데이터베이스 오류 발생: {e}")
            raise # 예외 다시 발생
        finally:
            conn.close() # 연결 닫기

    def _initialize_database(self):
        """
        데이터베이스를 초기화하고 필요한 테이블, 인덱스, 트리거를 생성합니다.
        각 모듈의 스키마 마이그레이션을 적용합니다.
        """
        with self.get_connection() as conn:
            cur = conn.cursor()

            # documents 테이블: 처리된 문서의 메타데이터 및 내용 저장
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
                    status TEXT DEFAULT 'pending' -- 문서 처리 상태 (pending, processing, processed, failed)
                );
            """)

            # FTS5 (Full-Text Search) 가상 테이블: 문서 내용에 대한 고속 전문 검색을 지원
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title,
                    content,
                    keywords,
                    content=documents, -- documents 테이블의 내용을 기반으로 함
                    content_rowid=id, -- documents 테이블의 id를 참조
                    tokenize='porter unicode61' -- 토큰화 방식 (영어/유니코드 지원)
                );
            """)

            # chunks 테이블: 문서 내용을 작은 단위(청크)로 분할하여 저장
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL, -- 원본 문서 ID
                    chunk_index INTEGER NOT NULL, -- 문서 내 청크의 순서
                    content TEXT NOT NULL, -- 청크 내용
                    embedding_vector BLOB, -- 청크 내용의 임베딩 벡터 (바이너리 형태로 저장)
                    token_count INTEGER, -- 청크의 토큰 수
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(document_id, chunk_index)
                );
            """)

            # search_cache 테이블: 이전에 수행된 검색 쿼리 결과를 캐시하여 응답 속도 향상
            cur.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT NOT NULL UNIQUE, -- 쿼리 내용의 해시 값
                    query_text TEXT NOT NULL, -- 원본 쿼리 텍스트
                    search_type TEXT NOT NULL, -- 검색 타입 (예: hybrid, vector, ir)
                    results_json TEXT NOT NULL, -- 검색 결과 (JSON 형태로 저장)
                    hit_count INTEGER DEFAULT 0, -- 캐시 히트 횟수
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # system_settings 테이블: 애플리케이션의 동적 설정 값들을 저장 (예: 검색 가중치)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY, -- 설정 키 (예: 'vector_weight')
                    value TEXT NOT NULL, -- 설정 값
                    description TEXT, -- 설정에 대한 설명
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # user_sessions 테이블: 사용자 세션 정보 및 활동 기록
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE, -- 고유 세션 ID
                    user_agent TEXT, -- 사용자 에이전트 정보
                    ip_address TEXT, -- 사용자 IP 주소
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    query_count INTEGER DEFAULT 0 -- 해당 세션에서 발생한 쿼리 수
                );
            """)

            # query_logs 테이블: 모든 검색 쿼리 및 RAG 쿼리 기록
            cur.execute("""
                CREATE TABLE IF NOT EXISTS query_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT, -- 사용자 세션 ID (user_sessions 테이블 참조)
                    query_text TEXT NOT NULL, -- 사용자의 원본 쿼리 텍스트
                    search_type TEXT, -- 쿼리 타입 (예: 'hybrid_search', 'rag_query')
                    results_count INTEGER, -- 반환된 검색 결과 수
                    response_time_ms INTEGER, -- 응답 시간 (밀리초)
                    success BOOLEAN DEFAULT TRUE, -- 쿼리 성공 여부
                    error_message TEXT, -- 오류 메시지 (실패 시)
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
                );
            """)

            # 인덱스 및 트리거 생성
            self._create_indexes(cur)
            self._create_triggers(cur)
            
            # 대화 스키마 마이그레이션 적용
            # 멀티턴 대화 관련 테이블, 인덱스, 트리거 등을 생성합니다.
            apply_conversation_migration(self)
            
            # 통계 스키마 마이그레이션 적용
            # 사용 통계 관련 테이블, 인덱스, 트리거 등을 생성합니다.
            apply_statistics_migration(self)

            logger.info("데이터베이스 초기화 완료")

    def _create_indexes(self, cur):
        """
        데이터베이스 테이블에 인덱스를 생성합니다.
        조회 성능을 향상시키기 위해 자주 사용되는 컬럼에 인덱스를 추가합니다.
        """
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
                logger.warning(f"인덱스 생성 실패: {e}")

    def _create_triggers(self, cur):
        """
        데이터베이스 트리거를 생성합니다.
        주로 FTS5 가상 테이블과 documents 테이블 간의 자동 동기화를 처리합니다.
        (재귀를 유발하는 트리거는 설계상 사용하지 않음)
        """

        # 기존 트리거 정리 (재실행 시 중복 생성 방지)
        cur.execute("DROP TRIGGER IF EXISTS documents_fts_insert;")
        cur.execute("DROP TRIGGER IF EXISTS documents_fts_update;")
        cur.execute("DROP TRIGGER IF EXISTS documents_fts_delete;")
        # 의도적으로 updated_at 자동 갱신 트리거는 생성하지 않음
        # (AFTER UPDATE에서 documents를 다시 UPDATE하면 재귀 유발 가능성)

        # INSERT 시 FTS5 인덱스에 문서 내용 추가
        cur.execute("""
            CREATE TRIGGER documents_fts_insert
            AFTER INSERT ON documents
            BEGIN
                INSERT INTO documents_fts(rowid, title, content, keywords)
                VALUES (new.id, new.title, new.content, new.keywords);
            END;
        """)

        # UPDATE 시 FTS5 인덱스 재색인 (기존 항목 삭제 후 새 항목 삽입 패턴)
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

        # DELETE 시 FTS5 인덱스에서 문서 내용 제거
        cur.execute("""
            CREATE TRIGGER documents_fts_delete
            AFTER DELETE ON documents
            BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, title, content, keywords)
                VALUES ('delete', old.id, old.content, old.keywords);
            END;
        """)

    def health_check(self) -> Dict[str, Any]:
        """
        데이터베이스의 상태를 확인합니다.
        연결 가능 여부, 주요 테이블의 레코드 수, 데이터베이스 파일 크기 등을 반환합니다.
        """
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1") # 간단한 쿼리로 연결 확인
                cur.execute("SELECT COUNT(*) FROM documents")
                doc_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM search_cache")
                cache_count = cur.fetchone()[0]
                cur.execute("PRAGMA page_count") # 데이터베이스 페이지 수
                page_count = cur.fetchone()[0]
                cur.execute("PRAGMA page_size") # 페이지 크기
                page_size = cur.fetchone()[0]
                db_size_mb = (page_count * page_size) / (1024 * 1024) # 데이터베이스 크기 (MB)
                return {
                    "status": "healthy",
                    "database_path": self.db_path,
                    "documents_count": doc_count,
                    "chunks_count": chunk_count,
                    "cache_count": cache_count,
                    "database_size_mb": round(db_size_mb, 2),
                    "wal_mode": True, # WAL 모드 활성화 여부
                }
        except Exception as e:
            logger.error(f"데이터베이스 헬스체크 실패: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def get_setting(self, key: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        시스템 설정 값을 system_settings 테이블에서 조회합니다.
        지정된 키에 해당하는 값이 없으면 기본값을 반환합니다.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return default_value

    def set_setting(self, key: str, value: str, description: Optional[str] = None):
        """
        시스템 설정 값을 system_settings 테이블에 저장하거나 업데이트합니다.
        설정 키가 이미 존재하면 값을 갱신하고, 없으면 새로 삽입합니다.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO system_settings (key, value, description) VALUES (?, ?, ?)",
                (key, value, description),
            )
            conn.commit()


# 전역 인스턴스: 애플리케이션 전체에서 데이터베이스 매니저를 싱글톤으로 사용합니다.
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """
    전역 데이터베이스 매니저 인스턴스를 반환하는 함수.
    FastAPI의 Depends 주입 시스템에서 사용될 수 있습니다.
    """
    return db_manager
