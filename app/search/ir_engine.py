import sqlite3
import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
import json
import hashlib

from app.core.database import get_db_manager
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class IRSearchResult:
    """IR 검색 결과"""
    chunk_id: str
    document_id: int
    score: float
    title: str
    content: str
    snippet: str
    metadata: Optional[Dict[str, Any]] = None


class SQLiteFTS5Engine:
    """
    SQLite FTS5 기반 Information Retrieval 검색 엔진
    한국어 특화 처리 및 고급 검색 기능 포함
    """
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.cache_enabled = True
        self.max_cache_entries = 1000
        
        # 한국어 검색 최적화 설정
        self.enable_korean_optimization = True
        self.snippet_length = 200
        
        logger.info("SQLite FTS5 IR Engine initialized")
    
    def _normalize_query(self, query: str) -> str:
        """
        검색 쿼리 정규화
        한국어 특화 처리 포함
        """
        if not query or not query.strip():
            return ""
        
        # 기본 정규화
        normalized = query.strip()
        
        # 특수 문자 처리 (FTS5 예약어 이스케이프)
        normalized = re.sub(r'["\(\)\[\]{}]', '', normalized)
        
        # 연속된 공백 제거
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # 한국어 최적화
        if self.enable_korean_optimization:
            normalized = self._optimize_korean_query(normalized)
        
        return normalized.strip()
    
    def _optimize_korean_query(self, query: str) -> str:
        """한국어 쿼리 최적화"""
        # 한국어 조사 제거 (간단한 버전)
        korean_particles = ['은', '는', '이', '가', '을', '를', '에서', '로', '으로', '와', '과']
        words = query.split()
        
        optimized_words = []
        for word in words:
            # 조사 제거
            optimized_word = word
            for particle in korean_particles:
                if word.endswith(particle) and len(word) > len(particle):
                    optimized_word = word[:-len(particle)]
                    break
            optimized_words.append(optimized_word)
        
        return ' '.join(optimized_words)
    
    def _build_fts_query(self, query: str, search_mode: str = "AND") -> str:
        """
        FTS5 검색 쿼리 구성
        다양한 검색 모드 지원
        """
        normalized_query = self._normalize_query(query)
        if not normalized_query:
            return ""
        
        words = normalized_query.split()
        if not words:
            return ""
        
        if search_mode == "AND":
            # 모든 단어 포함 (기본값)
            fts_query = " AND ".join(f'"{word}"' for word in words)
        elif search_mode == "OR":
            # 단어 중 하나라도 포함
            fts_query = " OR ".join(f'"{word}"' for word in words)
        elif search_mode == "PHRASE":
            # 정확한 구문 검색
            fts_query = f'"{normalized_query}"'
        else:
            # 자동 모드: 단어가 많으면 OR, 적으면 AND
            if len(words) > 3:
                fts_query = " OR ".join(f'"{word}"' for word in words)
            else:
                fts_query = " AND ".join(f'"{word}"' for word in words)
        
        return fts_query
    
    def _get_query_cache_key(self, query: str, top_k: int, search_mode: str, filters: Optional[Dict[str, Any]]) -> str:
        """검색 쿼리 캐시 키 생성"""
        cache_data = {
            'query': query,
            'top_k': top_k,
            'search_mode': search_mode,
            'filters': filters or {}
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_cached_results(self, cache_key: str, search_type: str = 'ir') -> Optional[List[IRSearchResult]]:
        """캐시된 검색 결과 조회"""
        if not self.cache_enabled:
            return None

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT results_json, hit_count
                    FROM search_cache
                    WHERE query_hash = ? AND search_type = ?
                """, (cache_key, search_type))

                result = cursor.fetchone()
                if not result:
                    return None

                results_json, hit_count = result

                # 히트 카운트 업데이트
                cursor.execute("""
                    UPDATE search_cache
                    SET hit_count = ?, last_accessed = CURRENT_TIMESTAMP
                    WHERE query_hash = ? AND search_type = ?
                """, (hit_count + 1, cache_key, search_type))

                # JSON 결과를 객체로 변환
                results_data = json.loads(results_json)
                return [
                    IRSearchResult(
                        chunk_id=r['chunk_id'],
                        document_id=r['document_id'],
                        score=r['score'],
                        title=r['title'],
                        content=r['content'],
                        snippet=r['snippet'],
                        metadata=r.get('metadata')
                    )
                    for r in results_data
                ]

        except Exception as e:
            logger.error(f"Failed to get cached results: {e}")
            return None

    def _cache_results(self, cache_key: str, query: str, results: List[IRSearchResult], search_type: str = 'ir'):
        """검색 결과 캐시 저장"""
        if not self.cache_enabled:
            return

        try:
            # 결과를 JSON으로 직렬화
            results_data = [
                {
                    'chunk_id': r.chunk_id,
                    'document_id': r.document_id,
                    'score': r.score,
                    'title': r.title,
                    'content': r.content,
                    'snippet': r.snippet,
                    'metadata': r.metadata
                }
                for r in results
            ]
            results_json = json.dumps(results_data, ensure_ascii=False)

            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO search_cache
                    (query_hash, query_text, search_type, results_json, hit_count, last_accessed)
                    VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                """, (cache_key, query, search_type, results_json))

        except Exception as e:
            logger.error(f"Failed to cache results: {e}")
    
    def _generate_snippet(self, content: str, query: str) -> str:
        """검색 쿼리 기반 스니펫 생성"""
        if not content or not query:
            return content[:self.snippet_length] + "..." if len(content) > self.snippet_length else content
        
        # 쿼리 단어들로 스니펫 찾기
        query_words = self._normalize_query(query).split()
        if not query_words:
            return content[:self.snippet_length] + "..." if len(content) > self.snippet_length else content
        
        # 첫 번째 매치 위치 찾기
        content_lower = content.lower()
        best_position = 0
        best_score = 0
        
        for word in query_words:
            word_lower = word.lower()
            pos = content_lower.find(word_lower)
            if pos >= 0:
                # 단어 주변의 컨텍스트 점수 계산
                score = 1 / (pos + 1)  # 앞쪽에 있을수록 높은 점수
                if score > best_score:
                    best_score = score
                    best_position = pos
        
        # 스니펫 추출
        start = max(0, best_position - self.snippet_length // 3)
        end = min(len(content), start + self.snippet_length)
        snippet = content[start:end]
        
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def search(self, query: str, top_k: int = 20, search_mode: str = "AUTO",
              filters: Optional[Dict[str, Any]] = None) -> List[IRSearchResult]:
        """
        FTS5 기반 검색 수행
        캐싱 및 성능 최적화 포함
        """
        try:
            if not query or not query.strip():
                return []
            
            # 캐시 확인
            cache_key = self._get_query_cache_key(query, top_k, search_mode, filters)
            cached_results = self._get_cached_results(cache_key, 'ir')
            if cached_results is not None:
                logger.info(f"Returned cached IR search results for query: {query}")
                return cached_results[:top_k]
            
            # FTS5 쿼리 구성
            fts_query = self._build_fts_query(query, search_mode)
            if not fts_query:
                return []
            
            # SQL 쿼리 구성
            sql_query = """
                SELECT 
                    d.id as document_id,
                    d.title,
                    d.content,
                    d.keywords,
                    d.file_name,
                    d.file_type,
                    fts.rank as score
                FROM documents_fts fts
                JOIN documents d ON d.id = fts.rowid
                WHERE documents_fts MATCH ?
            """
            
            params = [fts_query]
            
            # 필터 적용
            if filters:
                if 'file_type' in filters:
                    sql_query += " AND d.file_type = ?"
                    params.append(filters['file_type'])
                
                if 'date_from' in filters:
                    sql_query += " AND d.created_at >= ?"
                    params.append(filters['date_from'])
                
                if 'date_to' in filters:
                    sql_query += " AND d.created_at <= ?"
                    params.append(filters['date_to'])
            
            # 정렬 및 제한
            sql_query += " ORDER BY fts.rank LIMIT ?"
            params.append(top_k * 2)  # 여유있게 가져온 후 후처리
            
            # 검색 실행
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_query, params)
                rows = cursor.fetchall()
            
            # 결과 후처리
            results = []
            for row in rows:
                document_id = row[0]
                title = row[1] or ""
                content = row[2] or ""
                keywords = row[3] or ""
                file_name = row[4] or ""
                file_type = row[5] or ""
                score = abs(float(row[6]))  # FTS5 rank는 음수이므로 절댓값
                
                # 스니펫 생성
                snippet = self._generate_snippet(content, query)
                
                # 메타데이터 구성
                metadata = {
                    'file_name': file_name,
                    'file_type': file_type,
                    'keywords': keywords
                }
                
                # chunk_id 생성 (문서 단위 검색이므로 document_id 사용)
                chunk_id = f"doc_{document_id}"
                
                results.append(IRSearchResult(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    score=score,
                    title=title,
                    content=content,
                    snippet=snippet,
                    metadata=metadata
                ))
            
            # 점수 정규화 (0-1 범위)
            if results:
                max_score = max(r.score for r in results)
                if max_score > 0:
                    for result in results:
                        result.score = result.score / max_score
            
            # 상위 결과만 선택
            final_results = results[:top_k]
            
            # 캐시 저장
            self._cache_results(cache_key, query, final_results, 'ir')
            
            logger.info(f"IR search returned {len(final_results)} results for query: {query}")
            return final_results
            
        except Exception as e:
            logger.error(f"IR search failed for query '{query}': {e}")
            return []
    
    def search_chunks(self, query: str, top_k: int = 20) -> List[IRSearchResult]:
        """청크 단위 FTS5 검색"""
        try:
            if not query or not query.strip():
                return []

            cache_key = self._get_query_cache_key(query, top_k, 'AUTO', None)
            cached_results = self._get_cached_results(cache_key, 'ir_chunk')
            if cached_results is not None:
                logger.info(f"Returned cached chunk search results for query: {query}")
                return cached_results[:top_k]

            fts_query = self._build_fts_query(query, 'AUTO')
            if not fts_query:
                return []

            sql_query = """
                SELECT
                    c.id as chunk_id,
                    c.document_id,
                    c.chunk_index,
                    c.content,
                    d.title,
                    d.keywords,
                    d.file_name,
                    d.file_type,
                    fts.rank as score
                FROM chunks_fts fts
                JOIN chunks c ON c.id = fts.rowid
                JOIN documents d ON d.id = c.document_id
                WHERE chunks_fts MATCH ?
                ORDER BY fts.rank LIMIT ?
            """

            params = [fts_query, top_k * 2]

            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_query, params)
                rows = cursor.fetchall()

            results = []
            for row in rows:
                chunk_id = row[0]
                document_id = row[1]
                chunk_index = row[2]
                content = row[3] or ""
                title = row[4] or ""
                keywords = row[5] or ""
                file_name = row[6] or ""
                file_type = row[7] or ""
                score = abs(float(row[8]))

                snippet = self._generate_snippet(content, query)
                metadata = {
                    'file_name': file_name,
                    'file_type': file_type,
                    'keywords': keywords,
                    'chunk_index': chunk_index
                }

                results.append(IRSearchResult(
                    chunk_id=f"chunk_{chunk_id}",
                    document_id=document_id,
                    score=score,
                    title=title,
                    content=content,
                    snippet=snippet,
                    metadata=metadata
                ))

            if results:
                max_score = max(r.score for r in results)
                if max_score > 0:
                    for r in results:
                        r.score = r.score / max_score

            final_results = results[:top_k]

            self._cache_results(cache_key, query, final_results, 'ir_chunk')

            logger.info(f"IR chunk search returned {len(final_results)} results for query: {query}")
            return final_results

        except Exception as e:
            logger.error(f"IR chunk search failed for query '{query}': {e}")
            return []
    
    def get_similar_documents(self, document_id: int, top_k: int = 10) -> List[IRSearchResult]:
        """
        유사 문서 검색 (키워드 기반)
        """
        try:
            # 기준 문서의 키워드 조회
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT keywords, title FROM documents WHERE id = ?
                """, (document_id,))
                
                row = cursor.fetchone()
                if not row:
                    return []
                
                keywords, title = row
                
            # 키워드를 쿼리로 사용하여 검색
            search_query = keywords or title or ""
            if not search_query:
                return []
            
            results = self.search(search_query, top_k + 1, search_mode="OR")
            
            # 자기 자신 제외
            filtered_results = [r for r in results if r.document_id != document_id]
            
            return filtered_results[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find similar documents: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """검색 엔진 통계"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 문서 수
                cursor.execute("SELECT COUNT(*) FROM documents")
                doc_count = cursor.fetchone()[0]
                
                # FTS5 인덱스 크기 (대략적)
                cursor.execute("SELECT COUNT(*) FROM documents_fts")
                fts_count = cursor.fetchone()[0]
                
                # 캐시 통계
                cursor.execute("""
                    SELECT COUNT(*), AVG(hit_count), MAX(hit_count) 
                    FROM search_cache WHERE search_type = 'ir'
                """)
                cache_row = cursor.fetchone()
                cache_count, avg_hits, max_hits = cache_row
                
                return {
                    "document_count": doc_count,
                    "fts_index_count": fts_count,
                    "cache_entries": cache_count,
                    "average_cache_hits": float(avg_hits or 0),
                    "max_cache_hits": int(max_hits or 0),
                    "korean_optimization": self.enable_korean_optimization,
                    "cache_enabled": self.cache_enabled
                }
                
        except Exception as e:
            logger.error(f"Failed to get IR engine stats: {e}")
            return {"error": str(e)}
    
    def cleanup_cache(self, max_age_hours: int = 24, max_entries: int = 1000) -> int:
        """검색 캐시 정리"""
        try:
            deleted_count = self.db_manager.cleanup_cache(max_age_hours, max_entries)
            logger.info(f"Cleaned up {deleted_count} IR cache entries")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup IR cache: {e}")
            return 0


# 전역 인스턴스 (싱글톤 패턴)
_ir_engine: Optional[SQLiteFTS5Engine] = None


def get_ir_engine() -> SQLiteFTS5Engine:
    """IR 엔진 싱글톤 인스턴스 반환"""
    global _ir_engine
    if _ir_engine is None:
        _ir_engine = SQLiteFTS5Engine()
    return _ir_engine