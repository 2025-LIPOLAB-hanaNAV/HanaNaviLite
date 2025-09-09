#!/usr/bin/env python3
"""
Semantic Document Filtering and Categorization System
Phase 2 고급 검색 기능 - 문서 자동 분류 및 의미적 필터링
"""

import re
import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import sqlite3

logger = logging.getLogger(__name__)


class DocumentCategory(Enum):
    """은행 업무 문서 카테고리"""
    NOTICE = "공지"           # 공지사항
    REGULATION = "규정"       # 규정/규칙
    GUIDELINE = "안내"        # 업무 안내
    PROCEDURE = "절차"        # 업무 절차
    FORM = "양식"            # 서식/양식
    POLICY = "정책"          # 정책 문서
    FINANCIAL = "금융"        # 금융 상품
    COMPLIANCE = "컴플라이언스" # 준법/감시
    REPORT = "보고서"         # 각종 보고서
    MANUAL = "매뉴얼"         # 매뉴얼/가이드
    FAQ = "FAQ"             # 자주 묻는 질문
    NEWS = "뉴스"            # 뉴스/소식
    OTHER = "기타"           # 기타


class DocumentPriority(Enum):
    """문서 중요도"""
    CRITICAL = "중요"         # 중요 문서
    HIGH = "높음"            # 높은 중요도  
    NORMAL = "보통"          # 일반 중요도
    LOW = "낮음"             # 낮은 중요도


@dataclass
class CategoryRule:
    """카테고리 분류 규칙"""
    category: DocumentCategory
    keywords: Set[str] = field(default_factory=set)
    title_patterns: List[str] = field(default_factory=list)
    content_patterns: List[str] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=list)
    confidence_boost: float = 1.0
    
    
@dataclass
class ClassificationResult:
    """문서 분류 결과"""
    document_id: int
    categories: List[Tuple[DocumentCategory, float]]  # (category, confidence)
    primary_category: DocumentCategory
    confidence: float
    priority: DocumentPriority
    tags: Set[str] = field(default_factory=set)
    reasoning: str = ""


class SemanticDocumentClassifier:
    """의미적 문서 분류기"""
    
    def __init__(self):
        self.category_rules = self._initialize_banking_rules()
        self.keyword_weights = self._initialize_keyword_weights()
        
    def _initialize_banking_rules(self) -> Dict[DocumentCategory, CategoryRule]:
        """은행 업무 특화 분류 규칙 초기화"""
        
        rules = {
            DocumentCategory.NOTICE: CategoryRule(
                category=DocumentCategory.NOTICE,
                keywords={
                    "공지", "알림", "안내", "발표", "소식", "변경", "개정", 
                    "시행", "적용", "실시", "공문", "전파"
                },
                title_patterns=[
                    r"공지.*사항", r".*알림", r".*안내", r".*발표", 
                    r"변경.*사항", r"개정.*사항", r"시행.*공지"
                ],
                content_patterns=[
                    r"공지드립니다", r"알려드립니다", r"안내드립니다",
                    r"변경되었습니다", r"개정되었습니다"
                ],
                confidence_boost=1.5
            ),
            
            DocumentCategory.REGULATION: CategoryRule(
                category=DocumentCategory.REGULATION,
                keywords={
                    "규정", "규칙", "시행령", "시행규칙", "내규", "준칙", 
                    "기준", "법령", "조례", "지침", "표준"
                },
                title_patterns=[
                    r".*규정", r".*규칙", r".*준칙", r".*기준", 
                    r".*지침", r"시행.*규칙", r"내부.*규정"
                ],
                content_patterns=[
                    r"제\d+조", r"제\d+항", r"별표.*참조", 
                    r"이 규정은", r"준수.*사항"
                ],
                confidence_boost=1.3
            ),
            
            DocumentCategory.PROCEDURE: CategoryRule(
                category=DocumentCategory.PROCEDURE,
                keywords={
                    "절차", "과정", "단계", "프로세스", "처리", "진행", 
                    "업무", "절차서", "매뉴얼", "방법"
                },
                title_patterns=[
                    r".*절차", r".*과정", r".*방법", r"업무.*절차", 
                    r"처리.*절차", r".*프로세스"
                ],
                content_patterns=[
                    r"\d+\.\s*단계", r"절차는.*다음과", r"처리.*방법",
                    r"다음.*순서", r"단계.*진행"
                ],
                confidence_boost=1.1
            ),
            
            DocumentCategory.FORM: CategoryRule(
                category=DocumentCategory.FORM,
                keywords={
                    "양식", "서식", "신청서", "동의서", "확인서", "증명서",
                    "계약서", "약정서", "신청", "접수"
                },
                title_patterns=[
                    r".*양식", r".*서식", r".*신청서", r".*동의서",
                    r".*확인서", r".*증명서", r".*계약서"
                ],
                file_patterns=[
                    r".*form.*", r".*양식.*", r".*서식.*", r".*신청.*"
                ],
                confidence_boost=1.4
            ),
            
            DocumentCategory.FINANCIAL: CategoryRule(
                category=DocumentCategory.FINANCIAL,
                keywords={
                    "금융", "상품", "대출", "예금", "적금", "펀드", "보험",
                    "카드", "투자", "자산", "금리", "수익", "이자"
                },
                title_patterns=[
                    r".*상품", r".*대출", r".*예금", r".*적금",
                    r".*펀드", r".*보험", r".*카드", r"금융.*상품"
                ],
                content_patterns=[
                    r"금리.*%", r"수익률", r"이자율", r"금융상품",
                    r"가입.*조건", r"상품.*특징"
                ],
                confidence_boost=1.2
            ),
            
            DocumentCategory.COMPLIANCE: CategoryRule(
                category=DocumentCategory.COMPLIANCE,
                keywords={
                    "컴플라이언스", "준법", "감시", "리스크", "위험", "관리",
                    "감독", "점검", "모니터링", "KYC", "AML"
                },
                title_patterns=[
                    r".*컴플라이언스", r".*준법", r".*감시", r".*리스크",
                    r"위험.*관리", r".*점검", r"KYC.*", r"AML.*"
                ],
                confidence_boost=1.3
            ),
            
            DocumentCategory.REPORT: CategoryRule(
                category=DocumentCategory.REPORT,
                keywords={
                    "보고서", "현황", "분석", "통계", "실적", "결과",
                    "요약", "리포트", "월간", "분기", "년간", "정기"
                },
                title_patterns=[
                    r".*보고서", r".*현황", r".*분석", r".*실적",
                    r"월간.*", r"분기.*", r".*년간", r".*요약"
                ],
                confidence_boost=1.1
            ),
            
            DocumentCategory.FAQ: CategoryRule(
                category=DocumentCategory.FAQ,
                keywords={
                    "FAQ", "질문", "답변", "궁금", "문의", "Q&A",
                    "자주", "묻는", "질의", "응답"
                },
                title_patterns=[
                    r".*FAQ", r".*Q&A", r"자주.*질문", r".*문의",
                    r"궁금.*사항", r"질의.*응답"
                ],
                content_patterns=[
                    r"Q\s*:", r"A\s*:", r"질문\s*:", r"답변\s*:",
                    r"\d+\.\s*Q", r"\d+\.\s*A"
                ],
                confidence_boost=1.5
            )
        }
        
        # 기타 카테고리는 별도로 처리하지 않음 (기본값)
        return rules
    
    def _initialize_keyword_weights(self) -> Dict[str, float]:
        """키워드 가중치 설정"""
        return {
            # 높은 가중치
            "중요": 2.0, "긴급": 2.0, "필수": 1.8, "주의": 1.5,
            "신규": 1.3, "변경": 1.3, "개정": 1.3, "추가": 1.2,
            # 보통 가중치  
            "일반": 1.0, "기본": 1.0, "표준": 1.0,
            # 낮은 가중치
            "참고": 0.8, "안내": 0.8, "기타": 0.5
        }
    
    def classify_document(self, document_data: Dict[str, Any]) -> ClassificationResult:
        """문서 분류 수행"""
        try:
            doc_id = document_data.get('id', 0)
            title = document_data.get('title', '') or ''
            content = document_data.get('content', '') or ''
            file_name = document_data.get('file_name', '') or ''
            
            # 카테고리별 점수 계산
            category_scores = {}
            
            for category, rule in self.category_rules.items():
                score = self._calculate_category_score(
                    rule, title, content, file_name
                )
                category_scores[category] = score
            
            # 상위 카테고리들 정렬
            sorted_categories = sorted(
                category_scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # 주 카테고리 결정
            if sorted_categories[0][1] > 0.3:  # 최소 신뢰도 임계값
                primary_category = sorted_categories[0][0]
                confidence = min(sorted_categories[0][1], 1.0)
            else:
                primary_category = DocumentCategory.OTHER
                confidence = 0.1
            
            # 우선순위 결정
            priority = self._determine_priority(title, content)
            
            # 태그 추출
            tags = self._extract_tags(title, content)
            
            # 추론 근거 생성
            reasoning = self._generate_reasoning(
                primary_category, confidence, title, content
            )
            
            return ClassificationResult(
                document_id=doc_id,
                categories=sorted_categories[:3],  # 상위 3개만
                primary_category=primary_category,
                confidence=confidence,
                priority=priority,
                tags=tags,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return ClassificationResult(
                document_id=document_data.get('id', 0),
                categories=[(DocumentCategory.OTHER, 0.1)],
                primary_category=DocumentCategory.OTHER,
                confidence=0.1,
                priority=DocumentPriority.NORMAL,
                reasoning=f"Classification error: {str(e)}"
            )
    
    def _calculate_category_score(self, rule: CategoryRule, 
                                title: str, content: str, file_name: str) -> float:
        """카테고리별 점수 계산"""
        score = 0.0
        
        # 키워드 매칭 (제목에서 더 높은 가중치)
        title_lower = title.lower()
        content_lower = content.lower()
        file_lower = file_name.lower()
        
        for keyword in rule.keywords:
            if keyword in title_lower:
                score += 0.3 * self.keyword_weights.get(keyword, 1.0)
            if keyword in content_lower:
                score += 0.1 * self.keyword_weights.get(keyword, 1.0)
            if keyword in file_lower:
                score += 0.2 * self.keyword_weights.get(keyword, 1.0)
        
        # 패턴 매칭
        for pattern in rule.title_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                score += 0.4
        
        for pattern in rule.content_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            score += min(matches * 0.1, 0.3)  # 최대 0.3점
        
        for pattern in rule.file_patterns:
            if re.search(pattern, file_name, re.IGNORECASE):
                score += 0.2
        
        # 신뢰도 부스트 적용
        score *= rule.confidence_boost
        
        return score
    
    def _determine_priority(self, title: str, content: str) -> DocumentPriority:
        """문서 중요도 결정"""
        high_priority_keywords = {
            "중요", "긴급", "필수", "즉시", "주의", "경고", 
            "변경", "개정", "시행", "의무"
        }
        
        critical_patterns = [
            r"중요.*공지", r"긴급.*사항", r"필수.*확인",
            r"즉시.*시행", r"의무.*사항"
        ]
        
        title_content = (title + " " + content[:500]).lower()
        
        # 긴급/중요 패턴 확인
        for pattern in critical_patterns:
            if re.search(pattern, title_content, re.IGNORECASE):
                return DocumentPriority.CRITICAL
        
        # 고우선순위 키워드 개수 확인
        priority_score = sum(
            1 for keyword in high_priority_keywords 
            if keyword in title_content
        )
        
        if priority_score >= 3:
            return DocumentPriority.CRITICAL
        elif priority_score >= 2:
            return DocumentPriority.HIGH
        elif priority_score >= 1:
            return DocumentPriority.NORMAL
        else:
            return DocumentPriority.LOW
    
    def _extract_tags(self, title: str, content: str) -> Set[str]:
        """문서 태그 추출"""
        tags = set()
        
        # 일반적인 은행 업무 태그
        banking_tags = {
            "대출": ["대출", "론", "신용"],
            "예금": ["예금", "적금", "저축"],
            "카드": ["카드", "신용카드", "체크카드"],
            "보험": ["보험", "보장", "담보"],
            "투자": ["투자", "펀드", "자산운용"],
            "외환": ["외환", "환율", "달러"],
            "전자금융": ["인터넷뱅킹", "모바일", "전자금융"],
            "KYC": ["KYC", "고객확인", "본인확인"],
            "AML": ["AML", "자금세탁", "의심거래"]
        }
        
        text = (title + " " + content[:1000]).lower()
        
        for tag, keywords in banking_tags.items():
            if any(keyword.lower() in text for keyword in keywords):
                tags.add(tag)
        
        return tags
    
    def _generate_reasoning(self, category: DocumentCategory, 
                          confidence: float, title: str, content: str) -> str:
        """분류 근거 생성"""
        if confidence > 0.7:
            certainty = "높은 확신"
        elif confidence > 0.5:
            certainty = "보통 확신"
        elif confidence > 0.3:
            certainty = "낮은 확신"
        else:
            certainty = "불확실"
        
        reasoning_parts = [
            f"{category.value} 카테고리로 분류 ({certainty}: {confidence:.2f})"
        ]
        
        # 주요 매칭 키워드 찾기
        if category in self.category_rules:
            rule = self.category_rules[category]
            matched_keywords = [
                kw for kw in rule.keywords 
                if kw in title.lower() or kw in content[:500].lower()
            ]
            
            if matched_keywords:
                reasoning_parts.append(
                    f"매칭 키워드: {', '.join(matched_keywords[:5])}"
                )
        
        return "; ".join(reasoning_parts)


class SemanticFilterManager:
    """의미적 필터 관리자"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.classifier = SemanticDocumentClassifier()
        self._initialize_filter_schema()
    
    def _initialize_filter_schema(self):
        """필터링을 위한 추가 스키마 생성"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 문서 카테고리 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER NOT NULL,
                        category TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        is_primary BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                        UNIQUE(document_id, category)
                    )
                """)
                
                # 문서 태그 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER NOT NULL,
                        tag TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                        UNIQUE(document_id, tag)
                    )
                """)
                
                # 문서 우선순위 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_priorities (
                        document_id INTEGER PRIMARY KEY,
                        priority TEXT NOT NULL,
                        reasoning TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """)
                
                # 인덱스 생성
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_categories_category ON document_categories(category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_categories_primary ON document_categories(is_primary)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_tags_tag ON document_tags(tag)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_priorities_priority ON document_priorities(priority)")
                
                logger.info("Semantic filter schema initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize semantic filter schema: {e}")
            raise
    
    def classify_document(self, document_id: int) -> Optional[ClassificationResult]:
        """단일 문서 분류"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 문서 데이터 조회
                cursor.execute("""
                    SELECT id, title, content, file_name, file_type 
                    FROM documents WHERE id = ?
                """, (document_id,))
                
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Document {document_id} not found")
                    return None
                
                document_data = {
                    'id': row[0],
                    'title': row[1] or '',
                    'content': row[2] or '',
                    'file_name': row[3] or '',
                    'file_type': row[4] or ''
                }
                
                # 분류 수행
                result = self.classifier.classify_document(document_data)
                
                # 결과 저장
                self._save_classification_result(result)
                
                logger.info(f"Document {document_id} classified as {result.primary_category.value}")
                return result
                
        except Exception as e:
            logger.error(f"Failed to classify document {document_id}: {e}")
            return None
    
    def classify_all_documents(self) -> Dict[str, int]:
        """전체 문서 분류"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 미분류 문서들 조회
                cursor.execute("""
                    SELECT d.id, d.title, d.content, d.file_name, d.file_type
                    FROM documents d
                    LEFT JOIN document_categories dc ON d.id = dc.document_id AND dc.is_primary = TRUE
                    WHERE dc.document_id IS NULL AND d.status = 'completed'
                """)
                
                documents = cursor.fetchall()
                
            results = {
                'total': len(documents),
                'classified': 0,
                'failed': 0,
                'categories': {}
            }
            
            for row in documents:
                document_data = {
                    'id': row[0],
                    'title': row[1] or '',
                    'content': row[2] or '',
                    'file_name': row[3] or '',
                    'file_type': row[4] or ''
                }
                
                try:
                    result = self.classifier.classify_document(document_data)
                    self._save_classification_result(result)
                    
                    # 통계 업데이트
                    results['classified'] += 1
                    category_name = result.primary_category.value
                    results['categories'][category_name] = results['categories'].get(category_name, 0) + 1
                    
                except Exception as e:
                    logger.error(f"Failed to classify document {row[0]}: {e}")
                    results['failed'] += 1
            
            logger.info(f"Batch classification completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Batch classification failed: {e}")
            return {'total': 0, 'classified': 0, 'failed': 1, 'categories': {}}
    
    def _save_classification_result(self, result: ClassificationResult):
        """분류 결과 저장"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 기존 분류 결과 삭제
                cursor.execute("DELETE FROM document_categories WHERE document_id = ?", 
                             (result.document_id,))
                cursor.execute("DELETE FROM document_tags WHERE document_id = ?", 
                             (result.document_id,))
                cursor.execute("DELETE FROM document_priorities WHERE document_id = ?", 
                             (result.document_id,))
                
                # 카테고리 저장
                for category, confidence in result.categories:
                    is_primary = (category == result.primary_category)
                    cursor.execute("""
                        INSERT INTO document_categories 
                        (document_id, category, confidence, is_primary)
                        VALUES (?, ?, ?, ?)
                    """, (result.document_id, category.value, confidence, is_primary))
                
                # 태그 저장
                for tag in result.tags:
                    cursor.execute("""
                        INSERT INTO document_tags (document_id, tag)
                        VALUES (?, ?)
                    """, (result.document_id, tag))
                
                # 우선순위 저장
                cursor.execute("""
                    INSERT INTO document_priorities 
                    (document_id, priority, reasoning)
                    VALUES (?, ?, ?)
                """, (result.document_id, result.priority.value, result.reasoning))
                
        except Exception as e:
            logger.error(f"Failed to save classification result: {e}")
            raise
    
    def get_documents_by_category(self, category: str, limit: int = 50) -> List[Dict]:
        """카테고리별 문서 조회"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT d.id, d.title, d.file_name, d.created_at, 
                           dc.confidence, dp.priority
                    FROM documents d
                    JOIN document_categories dc ON d.id = dc.document_id
                    LEFT JOIN document_priorities dp ON d.id = dp.document_id
                    WHERE dc.category = ? AND dc.is_primary = TRUE
                    ORDER BY dc.confidence DESC, d.created_at DESC
                    LIMIT ?
                """, (category, limit))
                
                rows = cursor.fetchall()
                
                return [{
                    'id': row[0],
                    'title': row[1],
                    'file_name': row[2],
                    'created_at': row[3],
                    'confidence': row[4],
                    'priority': row[5]
                } for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get documents by category {category}: {e}")
            return []
    
    def get_category_statistics(self) -> Dict[str, Any]:
        """카테고리 통계 조회"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 카테고리별 문서 수
                cursor.execute("""
                    SELECT category, COUNT(*) as count, AVG(confidence) as avg_confidence
                    FROM document_categories 
                    WHERE is_primary = TRUE
                    GROUP BY category
                    ORDER BY count DESC
                """)
                
                categories = {}
                for row in cursor.fetchall():
                    categories[row[0]] = {
                        'count': row[1],
                        'avg_confidence': round(row[2], 3) if row[2] else 0
                    }
                
                # 우선순위 통계
                cursor.execute("""
                    SELECT priority, COUNT(*) as count
                    FROM document_priorities
                    GROUP BY priority
                """)
                
                priorities = {row[0]: row[1] for row in cursor.fetchall()}
                
                # 태그 통계 (상위 20개)
                cursor.execute("""
                    SELECT tag, COUNT(*) as count
                    FROM document_tags
                    GROUP BY tag
                    ORDER BY count DESC
                    LIMIT 20
                """)
                
                tags = {row[0]: row[1] for row in cursor.fetchall()}
                
                return {
                    'categories': categories,
                    'priorities': priorities,
                    'top_tags': tags
                }
                
        except Exception as e:
            logger.error(f"Failed to get category statistics: {e}")
            return {'categories': {}, 'priorities': {}, 'top_tags': {}}


# 전역 인스턴스
_semantic_filter_manager: Optional[SemanticFilterManager] = None


def get_semantic_filter_manager(db_manager=None) -> SemanticFilterManager:
    """의미적 필터 관리자 싱글톤 반환"""
    global _semantic_filter_manager
    if _semantic_filter_manager is None:
        if db_manager is None:
            from app.core.database import get_database_manager
            db_manager = get_database_manager()
        _semantic_filter_manager = SemanticFilterManager(db_manager)
    return _semantic_filter_manager