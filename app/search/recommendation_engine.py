#!/usr/bin/env python3
"""
Document Recommendation Engine
Phase 2 고급 검색 기능 - 연관 문서 추천 및 개인화 시스템
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import sqlite3
import json
import math

logger = logging.getLogger(__name__)


@dataclass
class DocumentSimilarity:
    """문서 유사도 정보"""
    document_id: int
    title: str
    similarity_score: float
    similarity_type: str  # "content", "category", "keyword", "user_pattern"
    reasons: List[str] = field(default_factory=list)


@dataclass
class UserSearchPattern:
    """사용자 검색 패턴"""
    user_id: str
    frequent_keywords: Dict[str, int]
    preferred_categories: Dict[str, int]
    search_times: List[datetime]
    viewed_documents: Set[int]
    interaction_score: Dict[int, float]  # document_id -> score


@dataclass
class RecommendationResult:
    """추천 결과"""
    recommendations: List[DocumentSimilarity]
    recommendation_type: str
    confidence: float
    reasoning: str


class ContentSimilarityCalculator:
    """콘텐츠 유사도 계산기"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def calculate_tfidf_similarity(self, doc1_id: int, doc2_id: int) -> float:
        """TF-IDF 기반 문서 유사도 계산"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 두 문서의 콘텐츠 조회
                cursor.execute("""
                    SELECT content, keywords FROM documents 
                    WHERE id IN (?, ?) AND content IS NOT NULL
                """, (doc1_id, doc2_id))
                
                results = cursor.fetchall()
                if len(results) != 2:
                    return 0.0
                
                doc1_content = (results[0][0] or '') + ' ' + (results[0][1] or '')
                doc2_content = (results[1][0] or '') + ' ' + (results[1][1] or '')
                
                # 간단한 TF-IDF 유사도 계산
                similarity = self._compute_cosine_similarity(doc1_content, doc2_content)
                return similarity
                
        except Exception as e:
            logger.error(f"TF-IDF similarity calculation failed: {e}")
            return 0.0
    
    def _compute_cosine_similarity(self, text1: str, text2: str) -> float:
        """코사인 유사도 계산"""
        try:
            # 단순한 토큰화
            tokens1 = set(text1.lower().split())
            tokens2 = set(text2.lower().split())
            
            if not tokens1 or not tokens2:
                return 0.0
            
            # 교집합과 합집합 계산
            intersection = tokens1.intersection(tokens2)
            union = tokens1.union(tokens2)
            
            if not union:
                return 0.0
            
            # Jaccard 유사도 (코사인 유사도의 간단한 근사)
            jaccard_similarity = len(intersection) / len(union)
            
            # 0.0 ~ 1.0 범위로 정규화
            return min(jaccard_similarity * 2, 1.0)
            
        except Exception as e:
            logger.warning(f"Cosine similarity computation failed: {e}")
            return 0.0
    
    def get_similar_documents_by_content(self, document_id: int, 
                                       top_k: int = 10) -> List[DocumentSimilarity]:
        """콘텐츠 기반 유사 문서 찾기"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 비교할 문서들 조회 (자기 자신 제외)
                cursor.execute("""
                    SELECT id, title, content, keywords 
                    FROM documents 
                    WHERE id != ? AND status = 'completed' 
                    AND content IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 100  -- 성능을 위해 최근 100개만
                """, (document_id,))
                
                candidate_docs = cursor.fetchall()
                similarities = []
                
                for doc in candidate_docs:
                    candidate_id, title, content, keywords = doc
                    
                    # 유사도 계산
                    similarity = self.calculate_tfidf_similarity(document_id, candidate_id)
                    
                    if similarity > 0.1:  # 최소 유사도 임계값
                        similarities.append(DocumentSimilarity(
                            document_id=candidate_id,
                            title=title or '',
                            similarity_score=similarity,
                            similarity_type="content",
                            reasons=[f"콘텐츠 유사도: {similarity:.2f}"]
                        ))
                
                # 유사도 순으로 정렬 후 상위 k개 반환
                similarities.sort(key=lambda x: x.similarity_score, reverse=True)
                return similarities[:top_k]
                
        except Exception as e:
            logger.error(f"Content similarity search failed: {e}")
            return []


class CategoryBasedRecommender:
    """카테고리 기반 추천기"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_similar_documents_by_category(self, document_id: int, 
                                        top_k: int = 10) -> List[DocumentSimilarity]:
        """카테고리 기반 유사 문서 찾기"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 기준 문서의 카테고리들 조회
                cursor.execute("""
                    SELECT category, confidence 
                    FROM document_categories 
                    WHERE document_id = ?
                    ORDER BY confidence DESC
                """, (document_id,))
                
                base_categories = cursor.fetchall()
                if not base_categories:
                    return []
                
                # 같은 카테고리의 다른 문서들 조회
                category_conditions = []
                params = []
                
                for category, confidence in base_categories:
                    category_conditions.append("dc.category = ?")
                    params.append(category)
                
                params.extend([document_id, top_k * 2])  # 자기 제외, 여유있게 조회
                
                cursor.execute(f"""
                    SELECT DISTINCT d.id, d.title, dc.category, dc.confidence,
                           d.created_at
                    FROM documents d
                    JOIN document_categories dc ON d.id = dc.document_id
                    WHERE ({' OR '.join(category_conditions)})
                    AND d.id != ? AND d.status = 'completed'
                    ORDER BY dc.confidence DESC, d.created_at DESC
                    LIMIT ?
                """, params)
                
                results = cursor.fetchall()
                
                # 문서별 유사도 계산
                doc_scores = defaultdict(list)
                for doc_id, title, category, confidence, created_at in results:
                    doc_scores[doc_id].append((title, category, confidence, created_at))
                
                similarities = []
                for doc_id, info_list in doc_scores.items():
                    title = info_list[0][0]  # 첫 번째 타이틀 사용
                    created_at = info_list[0][3]
                    
                    # 카테고리 매칭 점수 계산
                    total_score = sum(confidence for _, _, confidence, _ in info_list)
                    avg_score = total_score / len(info_list)
                    
                    # 최근성 가중치 (최근 문서일수록 높은 점수)
                    days_old = (datetime.now() - datetime.fromisoformat(created_at)).days
                    recency_weight = max(0.1, 1.0 - (days_old / 365.0))  # 1년 기준
                    
                    final_score = avg_score * recency_weight
                    
                    reasons = [f"카테고리 매칭: {', '.join(set(cat for _, cat, _, _ in info_list))}"]
                    if recency_weight > 0.5:
                        reasons.append(f"최근 문서 ({days_old}일 전)")
                    
                    similarities.append(DocumentSimilarity(
                        document_id=doc_id,
                        title=title or '',
                        similarity_score=final_score,
                        similarity_type="category",
                        reasons=reasons
                    ))
                
                # 점수 순으로 정렬 후 상위 k개 반환
                similarities.sort(key=lambda x: x.similarity_score, reverse=True)
                return similarities[:top_k]
                
        except Exception as e:
            logger.error(f"Category-based recommendation failed: {e}")
            return []


class UserPatternAnalyzer:
    """사용자 패턴 분석기"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._initialize_user_patterns_schema()
    
    def _initialize_user_patterns_schema(self):
        """사용자 패턴 추적용 스키마 초기화"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 사용자 검색 로그 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_search_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        query TEXT NOT NULL,
                        document_id INTEGER,
                        action_type TEXT NOT NULL,  -- 'search', 'view', 'click'
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_id TEXT,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """)
                
                # 사용자 문서 상호작용 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_document_interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        document_id INTEGER NOT NULL,
                        interaction_type TEXT NOT NULL,  -- 'view', 'download', 'bookmark'
                        duration_seconds INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                        UNIQUE(user_id, document_id, interaction_type, created_at)
                    )
                """)
                
                # 인덱스 생성
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON user_search_logs(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON user_search_logs(created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user_doc ON user_document_interactions(user_id, document_id)")
                
                logger.info("User patterns schema initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize user patterns schema: {e}")
    
    def record_search(self, user_id: str, query: str, session_id: str = None):
        """검색 기록 저장"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_search_logs (user_id, query, action_type, session_id)
                    VALUES (?, ?, 'search', ?)
                """, (user_id, query, session_id))
                
        except Exception as e:
            logger.error(f"Failed to record search: {e}")
    
    def record_document_interaction(self, user_id: str, document_id: int, 
                                  interaction_type: str, duration_seconds: int = None):
        """문서 상호작용 기록"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO user_document_interactions 
                    (user_id, document_id, interaction_type, duration_seconds)
                    VALUES (?, ?, ?, ?)
                """, (user_id, document_id, interaction_type, duration_seconds))
                
        except Exception as e:
            logger.error(f"Failed to record document interaction: {e}")
    
    def get_user_search_pattern(self, user_id: str, days: int = 30) -> UserSearchPattern:
        """사용자 검색 패턴 분석"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 검색 키워드 분석
                cursor.execute("""
                    SELECT query, COUNT(*) as frequency
                    FROM user_search_logs 
                    WHERE user_id = ? AND created_at >= ? AND action_type = 'search'
                    GROUP BY query
                    ORDER BY frequency DESC
                    LIMIT 50
                """, (user_id, cutoff_date.isoformat()))
                
                search_queries = cursor.fetchall()
                
                # 키워드 추출 및 빈도 계산
                keyword_counter = Counter()
                for query, frequency in search_queries:
                    words = query.lower().split()
                    for word in words:
                        if len(word) > 1:  # 한 글자 단어 제외
                            keyword_counter[word] += frequency
                
                # 선호 카테고리 분석 (상호작용한 문서들의 카테고리)
                cursor.execute("""
                    SELECT dc.category, COUNT(*) as frequency
                    FROM user_document_interactions udi
                    JOIN document_categories dc ON udi.document_id = dc.document_id
                    WHERE udi.user_id = ? AND udi.created_at >= ?
                    AND dc.is_primary = TRUE
                    GROUP BY dc.category
                    ORDER BY frequency DESC
                """, (user_id, cutoff_date.isoformat()))
                
                preferred_categories = {row[0]: row[1] for row in cursor.fetchall()}
                
                # 검색 시간 패턴
                cursor.execute("""
                    SELECT created_at
                    FROM user_search_logs 
                    WHERE user_id = ? AND created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT 100
                """, (user_id, cutoff_date.isoformat()))
                
                search_times = [
                    datetime.fromisoformat(row[0]) for row in cursor.fetchall()
                ]
                
                # 조회한 문서들
                cursor.execute("""
                    SELECT DISTINCT document_id
                    FROM user_document_interactions 
                    WHERE user_id = ? AND created_at >= ?
                """, (user_id, cutoff_date.isoformat()))
                
                viewed_documents = {row[0] for row in cursor.fetchall()}
                
                # 문서별 상호작용 점수 계산
                cursor.execute("""
                    SELECT document_id, interaction_type, COUNT(*) as count,
                           AVG(COALESCE(duration_seconds, 0)) as avg_duration
                    FROM user_document_interactions 
                    WHERE user_id = ? AND created_at >= ?
                    GROUP BY document_id, interaction_type
                """, (user_id, cutoff_date.isoformat()))
                
                interaction_scores = defaultdict(float)
                interaction_weights = {'view': 1.0, 'download': 3.0, 'bookmark': 5.0}
                
                for doc_id, interaction_type, count, avg_duration in cursor.fetchall():
                    base_score = interaction_weights.get(interaction_type, 1.0) * count
                    duration_bonus = min(avg_duration / 60.0, 2.0) if avg_duration else 0
                    interaction_scores[doc_id] += base_score + duration_bonus
                
                return UserSearchPattern(
                    user_id=user_id,
                    frequent_keywords=dict(keyword_counter.most_common(20)),
                    preferred_categories=preferred_categories,
                    search_times=search_times,
                    viewed_documents=viewed_documents,
                    interaction_score=dict(interaction_scores)
                )
                
        except Exception as e:
            logger.error(f"Failed to analyze user search pattern: {e}")
            return UserSearchPattern(
                user_id=user_id,
                frequent_keywords={},
                preferred_categories={},
                search_times=[],
                viewed_documents=set(),
                interaction_score={}
            )
    
    def get_personalized_recommendations(self, user_id: str, 
                                       top_k: int = 10) -> List[DocumentSimilarity]:
        """개인화 추천"""
        try:
            user_pattern = self.get_user_search_pattern(user_id)
            
            if not user_pattern.preferred_categories and not user_pattern.frequent_keywords:
                # 패턴이 없으면 최신 문서 추천
                return self._get_trending_documents(top_k)
            
            recommendations = []
            
            # 선호 카테고리 기반 추천
            category_recs = self._get_category_based_recommendations(
                user_pattern, top_k // 2
            )
            recommendations.extend(category_recs)
            
            # 키워드 기반 추천
            keyword_recs = self._get_keyword_based_recommendations(
                user_pattern, top_k // 2
            )
            recommendations.extend(keyword_recs)
            
            # 중복 제거 및 점수 순 정렬
            seen_docs = set()
            unique_recs = []
            
            for rec in sorted(recommendations, key=lambda x: x.similarity_score, reverse=True):
                if rec.document_id not in seen_docs and rec.document_id not in user_pattern.viewed_documents:
                    unique_recs.append(rec)
                    seen_docs.add(rec.document_id)
                    
                    if len(unique_recs) >= top_k:
                        break
            
            return unique_recs
            
        except Exception as e:
            logger.error(f"Personalized recommendations failed: {e}")
            return []
    
    def _get_trending_documents(self, top_k: int) -> List[DocumentSimilarity]:
        """트렌딩 문서 추천 (패턴이 없는 경우)"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT d.id, d.title, COUNT(udi.id) as interaction_count
                    FROM documents d
                    LEFT JOIN user_document_interactions udi ON d.id = udi.document_id
                    WHERE d.status = 'completed' 
                    AND d.created_at >= date('now', '-30 days')
                    GROUP BY d.id, d.title
                    ORDER BY interaction_count DESC, d.created_at DESC
                    LIMIT ?
                """, (top_k,))
                
                results = cursor.fetchall()
                
                return [
                    DocumentSimilarity(
                        document_id=row[0],
                        title=row[1] or '',
                        similarity_score=0.5 + (row[2] / 10.0),  # 기본 점수 + 인기도 보너스
                        similarity_type="trending",
                        reasons=["최근 인기 문서", f"상호작용 수: {row[2]}"]
                    )
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Failed to get trending documents: {e}")
            return []
    
    def _get_category_based_recommendations(self, user_pattern: UserSearchPattern, 
                                          top_k: int) -> List[DocumentSimilarity]:
        """카테고리 기반 개인화 추천"""
        try:
            if not user_pattern.preferred_categories:
                return []
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 선호 카테고리의 최신 문서들
                category_conditions = []
                params = []
                
                for category, frequency in user_pattern.preferred_categories.items():
                    category_conditions.append("dc.category = ?")
                    params.append(category)
                
                # 이미 본 문서들 제외
                viewed_doc_conditions = []
                if user_pattern.viewed_documents:
                    viewed_doc_conditions = ["d.id != ?"] * len(user_pattern.viewed_documents)
                    params.extend(list(user_pattern.viewed_documents))
                
                where_clause = f"({' OR '.join(category_conditions)})"
                if viewed_doc_conditions:
                    where_clause += f" AND ({' AND '.join(viewed_doc_conditions)})"
                
                params.append(top_k * 2)
                
                cursor.execute(f"""
                    SELECT d.id, d.title, dc.category, dc.confidence, d.created_at
                    FROM documents d
                    JOIN document_categories dc ON d.id = dc.document_id
                    WHERE {where_clause}
                    AND d.status = 'completed' AND dc.is_primary = TRUE
                    ORDER BY dc.confidence DESC, d.created_at DESC
                    LIMIT ?
                """, params)
                
                results = cursor.fetchall()
                
                recommendations = []
                for doc_id, title, category, confidence, created_at in results:
                    # 사용자의 카테고리 선호도 반영
                    user_preference = user_pattern.preferred_categories.get(category, 1)
                    preference_weight = min(math.log(user_preference + 1), 3.0)  # 로그 스케일 적용
                    
                    score = confidence * preference_weight / 3.0  # 정규화
                    
                    recommendations.append(DocumentSimilarity(
                        document_id=doc_id,
                        title=title or '',
                        similarity_score=score,
                        similarity_type="personalized_category",
                        reasons=[f"선호 카테고리: {category}", f"사용자 선호도: {user_preference}"]
                    ))
                
                return recommendations[:top_k]
                
        except Exception as e:
            logger.error(f"Category-based personalized recommendation failed: {e}")
            return []
    
    def _get_keyword_based_recommendations(self, user_pattern: UserSearchPattern, 
                                         top_k: int) -> List[DocumentSimilarity]:
        """키워드 기반 개인화 추천"""
        try:
            if not user_pattern.frequent_keywords:
                return []
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # FTS5를 이용한 키워드 기반 검색
                top_keywords = list(user_pattern.frequent_keywords.keys())[:5]  # 상위 5개 키워드
                keyword_query = ' OR '.join(top_keywords)
                
                # 이미 본 문서 제외 조건
                viewed_exclusion = ""
                params = [keyword_query]
                
                if user_pattern.viewed_documents:
                    placeholders = ','.join(['?'] * len(user_pattern.viewed_documents))
                    viewed_exclusion = f"AND d.id NOT IN ({placeholders})"
                    params.extend(list(user_pattern.viewed_documents))
                
                params.append(top_k)
                
                cursor.execute(f"""
                    SELECT d.id, d.title, d.keywords, 
                           rank, snippet(documents_fts, 1, '[', ']', '...', 32) as snippet
                    FROM documents_fts
                    JOIN documents d ON documents_fts.rowid = d.id
                    WHERE documents_fts MATCH ? {viewed_exclusion}
                    AND d.status = 'completed'
                    ORDER BY rank
                    LIMIT ?
                """, params)
                
                results = cursor.fetchall()
                
                recommendations = []
                for doc_id, title, keywords, rank, snippet in results:
                    # 키워드 매칭 점수 계산
                    doc_keywords = set((keywords or '').lower().split())
                    matched_keywords = doc_keywords.intersection(set(top_keywords))
                    
                    keyword_score = sum(
                        user_pattern.frequent_keywords.get(kw, 0) 
                        for kw in matched_keywords
                    )
                    
                    # FTS5 rank와 키워드 빈도 결합
                    final_score = min(keyword_score / 100.0, 1.0)  # 정규화
                    
                    recommendations.append(DocumentSimilarity(
                        document_id=doc_id,
                        title=title or '',
                        similarity_score=final_score,
                        similarity_type="personalized_keyword",
                        reasons=[
                            f"매칭 키워드: {', '.join(matched_keywords)}",
                            f"키워드 점수: {keyword_score}"
                        ]
                    ))
                
                return recommendations
                
        except Exception as e:
            logger.error(f"Keyword-based personalized recommendation failed: {e}")
            return []


class DocumentRecommendationEngine:
    """통합 문서 추천 엔진"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.content_calculator = ContentSimilarityCalculator(db_manager)
        self.category_recommender = CategoryBasedRecommender(db_manager)
        self.user_analyzer = UserPatternAnalyzer(db_manager)
    
    def get_recommendations(self, document_id: int = None, user_id: str = None,
                          recommendation_type: str = "hybrid", 
                          top_k: int = 10) -> RecommendationResult:
        """통합 추천 수행"""
        try:
            recommendations = []
            reasoning_parts = []
            confidence = 0.0
            
            if recommendation_type == "content" and document_id:
                # 콘텐츠 기반 추천
                content_recs = self.content_calculator.get_similar_documents_by_content(
                    document_id, top_k
                )
                recommendations.extend(content_recs)
                reasoning_parts.append(f"콘텐츠 유사도 기반 {len(content_recs)}개 문서")
                confidence = 0.7
                
            elif recommendation_type == "category" and document_id:
                # 카테고리 기반 추천
                category_recs = self.category_recommender.get_similar_documents_by_category(
                    document_id, top_k
                )
                recommendations.extend(category_recs)
                reasoning_parts.append(f"카테고리 기반 {len(category_recs)}개 문서")
                confidence = 0.8
                
            elif recommendation_type == "personalized" and user_id:
                # 개인화 추천
                personal_recs = self.user_analyzer.get_personalized_recommendations(
                    user_id, top_k
                )
                recommendations.extend(personal_recs)
                reasoning_parts.append(f"개인화 기반 {len(personal_recs)}개 문서")
                confidence = 0.6
                
            elif recommendation_type == "hybrid":
                # 하이브리드 추천
                if document_id:
                    content_recs = self.content_calculator.get_similar_documents_by_content(
                        document_id, top_k // 2
                    )
                    category_recs = self.category_recommender.get_similar_documents_by_category(
                        document_id, top_k // 2
                    )
                    recommendations.extend(content_recs)
                    recommendations.extend(category_recs)
                    reasoning_parts.extend([
                        f"콘텐츠 기반 {len(content_recs)}개",
                        f"카테고리 기반 {len(category_recs)}개"
                    ])
                
                if user_id:
                    personal_recs = self.user_analyzer.get_personalized_recommendations(
                        user_id, top_k // 3
                    )
                    recommendations.extend(personal_recs)
                    reasoning_parts.append(f"개인화 {len(personal_recs)}개")
                
                confidence = 0.75
            
            # 중복 제거 및 점수 기준 정렬
            seen_docs = set()
            unique_recommendations = []
            
            for rec in sorted(recommendations, key=lambda x: x.similarity_score, reverse=True):
                if rec.document_id not in seen_docs:
                    unique_recommendations.append(rec)
                    seen_docs.add(rec.document_id)
                    
                    if len(unique_recommendations) >= top_k:
                        break
            
            reasoning = "; ".join(reasoning_parts) if reasoning_parts else "추천 결과 없음"
            
            return RecommendationResult(
                recommendations=unique_recommendations,
                recommendation_type=recommendation_type,
                confidence=confidence,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Recommendation engine failed: {e}")
            return RecommendationResult(
                recommendations=[],
                recommendation_type=recommendation_type,
                confidence=0.0,
                reasoning=f"추천 실패: {str(e)}"
            )
    
    def record_user_activity(self, user_id: str, query: str = None, 
                           document_id: int = None, action: str = "search",
                           session_id: str = None, duration_seconds: int = None):
        """사용자 활동 기록"""
        try:
            if query and action == "search":
                self.user_analyzer.record_search(user_id, query, session_id)
            
            if document_id and action in ["view", "download", "bookmark"]:
                self.user_analyzer.record_document_interaction(
                    user_id, document_id, action, duration_seconds
                )
                
        except Exception as e:
            logger.error(f"Failed to record user activity: {e}")
    
    def get_recommendation_statistics(self) -> Dict[str, Any]:
        """추천 시스템 통계"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 사용자 활동 통계
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(*) as total_searches,
                        COUNT(CASE WHEN created_at >= date('now', '-7 days') THEN 1 END) as recent_searches
                    FROM user_search_logs
                """)
                
                search_stats = cursor.fetchone()
                
                # 문서 상호작용 통계
                cursor.execute("""
                    SELECT interaction_type, COUNT(*) as count
                    FROM user_document_interactions
                    GROUP BY interaction_type
                """)
                
                interaction_stats = {row[0]: row[1] for row in cursor.fetchall()}
                
                # 인기 카테고리
                cursor.execute("""
                    SELECT dc.category, COUNT(udi.id) as interaction_count
                    FROM document_categories dc
                    JOIN user_document_interactions udi ON dc.document_id = udi.document_id
                    WHERE dc.is_primary = TRUE
                    GROUP BY dc.category
                    ORDER BY interaction_count DESC
                    LIMIT 10
                """)
                
                popular_categories = {row[0]: row[1] for row in cursor.fetchall()}
                
                return {
                    'search_statistics': {
                        'unique_users': search_stats[0] if search_stats else 0,
                        'total_searches': search_stats[1] if search_stats else 0,
                        'recent_searches': search_stats[2] if search_stats else 0
                    },
                    'interaction_statistics': interaction_stats,
                    'popular_categories': popular_categories
                }
                
        except Exception as e:
            logger.error(f"Failed to get recommendation statistics: {e}")
            return {
                'search_statistics': {'unique_users': 0, 'total_searches': 0, 'recent_searches': 0},
                'interaction_statistics': {},
                'popular_categories': {}
            }


# 전역 인스턴스
_recommendation_engine: Optional[DocumentRecommendationEngine] = None


def get_recommendation_engine(db_manager=None) -> DocumentRecommendationEngine:
    """문서 추천 엔진 싱글톤 반환"""
    global _recommendation_engine
    if _recommendation_engine is None:
        if db_manager is None:
            from app.core.database import get_database_manager
            db_manager = get_database_manager()
        _recommendation_engine = DocumentRecommendationEngine(db_manager)
    return _recommendation_engine