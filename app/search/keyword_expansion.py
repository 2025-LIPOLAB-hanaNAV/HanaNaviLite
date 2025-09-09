#!/usr/bin/env python3
"""
Keyword Auto-Expansion System with Banking Domain Dictionary
Phase 2 고급 검색 기능 - 키워드 자동 확장 및 은행 업무 용어 사전
"""

import re
import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import sqlite3
import json

logger = logging.getLogger(__name__)


@dataclass
class KeywordExpansion:
    """키워드 확장 정보"""
    original_keyword: str
    expanded_keywords: Set[str]
    synonyms: Set[str]
    related_terms: Set[str]
    domain_terms: Set[str]
    confidence: float
    expansion_type: str  # "synonym", "related", "domain", "morphological"


@dataclass
class ExpandedQuery:
    """확장된 쿼리"""
    original_query: str
    expanded_query: str
    expansions: List[KeywordExpansion]
    boost_terms: Dict[str, float]  # 용어별 가중치
    total_expansion_count: int


class BankingDomainDictionary:
    """은행 업무 도메인 사전"""
    
    def __init__(self):
        self.synonyms = self._initialize_synonyms()
        self.related_terms = self._initialize_related_terms()
        self.domain_hierarchy = self._initialize_domain_hierarchy()
        self.abbreviations = self._initialize_abbreviations()
        self.technical_terms = self._initialize_technical_terms()
    
    def _initialize_synonyms(self) -> Dict[str, Set[str]]:
        """동의어 사전 초기화"""
        return {
            # 기본 금융 용어
            "대출": {"론", "융자", "차입", "자금조달", "신용대출", "담보대출"},
            "예금": {"저축", "적립", "예치", "입금", "저금"},
            "적금": {"정기적금", "자유적금", "청약적금", "주택적금"},
            "계좌": {"통장", "어카운트", "account"},
            "이자": {"금리", "수익률", "이율", "interest"},
            "수수료": {"fee", "수료", "비용", "요금"},
            "투자": {"자산운용", "포트폴리오", "investment"},
            "보험": {"insurance", "보장", "담보"},
            
            # 카드 관련
            "카드": {"신용카드", "체크카드", "직불카드", "카드결제"},
            "결제": {"지불", "payment", "정산", "결제승인"},
            "승인": {"approval", "인증", "허가", "확인"},
            
            # 외환 관련
            "외환": {"환율", "달러", "원화", "외화", "exchange"},
            "환전": {"currency exchange", "통화교환", "외화교환"},
            
            # 전자금융
            "인터넷뱅킹": {"온라인뱅킹", "웹뱅킹", "internet banking"},
            "모바일뱅킹": {"앱뱅킹", "mobile banking", "스마트뱅킹"},
            "ATM": {"현금인출기", "자동입출금기", "cash dispenser"},
            
            # 고객 서비스
            "고객": {"customer", "client", "회원", "이용자"},
            "서비스": {"service", "업무", "상품", "혜택"},
            "상담": {"문의", "consultation", "안내", "도움"},
            
            # 보안 관련
            "보안": {"security", "안전", "보호", "암호화"},
            "인증": {"authentication", "본인확인", "신원확인"},
            "비밀번호": {"password", "패스워드", "PIN", "암호"},
            
            # 규정 관련
            "규정": {"규칙", "rule", "regulation", "내규"},
            "정책": {"policy", "방침", "기준", "지침"},
            "절차": {"procedure", "과정", "프로세스", "단계"},
            
            # 금융감독
            "금감원": {"금융감독원", "FSS", "금융위원회"},
            "한국은행": {"한은", "BOK", "중앙은행"},
            "예보": {"예금보험공사", "KDIC"},
        }
    
    def _initialize_related_terms(self) -> Dict[str, Set[str]]:
        """연관 용어 사전 초기화"""
        return {
            # 대출 관련 용어군
            "대출": {
                "신용평가", "담보", "보증", "금리", "상환", "연체", 
                "DSR", "DTI", "LTV", "신용등급", "한도"
            },
            
            # 예적금 관련 용어군  
            "예금": {
                "만기", "원금", "이자", "복리", "단리", "자동연장",
                "중도해지", "예금자보호", "FDIC"
            },
            
            # 카드 관련 용어군
            "카드": {
                "포인트", "마일리지", "할인", "캐시백", "연회비",
                "결제한도", "승인거절", "해외사용", "분할결제"
            },
            
            # 투자 관련 용어군
            "투자": {
                "펀드", "ETF", "주식", "채권", "파생상품", "리스크",
                "수익률", "변동성", "분산투자", "자산배분"
            },
            
            # 보안 관련 용어군
            "보안": {
                "공동인증서", "생체인증", "OTP", "SMS인증", "ARS인증",
                "피싱", "파밍", "스미싱", "보이스피싱"
            },
            
            # 금융규제 관련 용어군
            "규제": {
                "바젤협약", "자본적정성", "유동성비율", "레버리지비율",
                "스트레스테스트", "내부통제", "리스크관리"
            },
            
            # 핀테크 관련 용어군
            "핀테크": {
                "오픈뱅킹", "API", "블록체인", "암호화폐", "디지털화폐",
                "간편결제", "P2P", "로보어드바이저"
            }
        }
    
    def _initialize_domain_hierarchy(self) -> Dict[str, Dict[str, Set[str]]]:
        """도메인 계층 구조 초기화"""
        return {
            "금융상품": {
                "예적금": {"예금", "적금", "정기예금", "자유적금", "청약적금"},
                "대출": {"신용대출", "담보대출", "전세대출", "주택담보대출"},
                "카드": {"신용카드", "체크카드", "기업카드", "선불카드"},
                "투자": {"펀드", "ETF", "주식", "채권", "파생상품"},
                "보험": {"생명보험", "손해보험", "연금보험", "건강보험"}
            },
            
            "업무프로세스": {
                "고객관리": {"가입", "해지", "변경", "상담", "민원"},
                "리스크관리": {"신용평가", "담보관리", "연체관리", "회수"},
                "운영관리": {"정산", "결산", "감사", "보고", "모니터링"}
            },
            
            "규제준수": {
                "금융규제": {"바젤", "IFRS", "자본규제", "유동성규제"},
                "정보보안": {"개인정보보호", "정보보안", "사이버보안"},
                "준법감시": {"컴플라이언스", "내부통제", "자금세탁방지"}
            },
            
            "채널": {
                "대면": {"영업점", "상담센터", "전화상담"},
                "비대면": {"인터넷뱅킹", "모바일뱅킹", "ATM", "키오스크"}
            }
        }
    
    def _initialize_abbreviations(self) -> Dict[str, str]:
        """약어 사전 초기화"""
        return {
            # 금융 약어
            "DSR": "총부채원리금상환비율",
            "DTI": "총부채상환비율", 
            "LTV": "주택담보대출비율",
            "KYC": "고객확인절차",
            "AML": "자금세탁방지",
            "CDD": "고객실사",
            "EDD": "강화된실사",
            "PEP": "정치적중요인물",
            
            # 기관 약어
            "FSC": "금융위원회",
            "FSS": "금융감독원", 
            "BOK": "한국은행",
            "KDIC": "예금보험공사",
            "KOFIA": "금융투자협회",
            "KFTC": "금융결제원",
            
            # 기술 약어
            "API": "응용프로그래밍인터페이스",
            "AI": "인공지능",
            "ML": "머신러닝",
            "RPA": "로봇프로세스자동화",
            "DLT": "분산원장기술",
            "CBDC": "중앙은행디지털화폐",
            
            # 업무 약어
            "STP": "직통처리",
            "T+1": "거래일익일",
            "EOD": "업무종료",
            "SOD": "업무개시",
            "BCM": "업무연속성관리"
        }
    
    def _initialize_technical_terms(self) -> Dict[str, Set[str]]:
        """기술 용어 사전"""
        return {
            "시스템": {
                "코어뱅킹", "차세대시스템", "레거시", "인터페이스",
                "배치", "온라인", "실시간", "API", "웹서비스"
            },
            
            "데이터": {
                "빅데이터", "데이터웨어하우스", "ETL", "데이터마트",
                "마스터데이터", "메타데이터", "데이터거버넌스"
            },
            
            "보안기술": {
                "암호화", "PKI", "HSM", "토큰화", "익명화",
                "방화벽", "침입탐지", "DLP", "SIEM"
            },
            
            "인공지능": {
                "머신러닝", "딥러닝", "자연어처리", "챗봇",
                "로보어드바이저", "이상탐지", "예측모델"
            }
        }


class MorphologicalAnalyzer:
    """한국어 형태소 분석 및 어간 추출"""
    
    def __init__(self):
        self.korean_endings = self._initialize_korean_endings()
        self.irregular_verbs = self._initialize_irregular_verbs()
    
    def _initialize_korean_endings(self) -> Set[str]:
        """한국어 어미 패턴"""
        return {
            # 동사 어미
            "하다", "되다", "이다", "하는", "되는", "하여", "하고",
            "한다", "된다", "했다", "됐다", "하지", "하면", "하니",
            
            # 형용사 어미
            "하다", "스럽다", "답다", "롭다", "적이다",
            
            # 명사 어미
            "이다", "들", "의", "을", "를", "이", "가", "에", "에서", "으로"
        }
    
    def _initialize_irregular_verbs(self) -> Dict[str, str]:
        """불규칙 활용 동사"""
        return {
            "간다": "가다",
            "온다": "오다", 
            "한다": "하다",
            "된다": "되다",
            "있다": "있다",
            "없다": "없다",
            "좋다": "좋다",
            "많다": "많다",
            "크다": "크다",
            "작다": "작다"
        }
    
    def extract_stem(self, word: str) -> str:
        """어간 추출 (간단한 규칙 기반)"""
        word = word.strip()
        
        # 불규칙 활용 확인
        if word in self.irregular_verbs:
            return self.irregular_verbs[word]
        
        # 일반적인 어미 제거
        for ending in sorted(self.korean_endings, key=len, reverse=True):
            if word.endswith(ending) and len(word) > len(ending):
                stem = word[:-len(ending)]
                if len(stem) >= 1:  # 최소 길이 확인
                    return stem
        
        return word
    
    def get_morphological_variants(self, word: str) -> Set[str]:
        """형태소 변형 생성"""
        variants = {word}
        stem = self.extract_stem(word)
        
        if stem != word:
            variants.add(stem)
            
            # 기본 활용형들
            common_endings = ["다", "하다", "되다", "이다", "의", "들"]
            for ending in common_endings:
                variants.add(stem + ending)
        
        return variants


class KeywordExpansionEngine:
    """키워드 확장 엔진"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.banking_dict = BankingDomainDictionary()
        self.morphological_analyzer = MorphologicalAnalyzer()
        self._initialize_expansion_cache()
    
    def _initialize_expansion_cache(self):
        """확장 캐시 초기화"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 키워드 확장 캐시 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS keyword_expansion_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_keyword TEXT NOT NULL,
                        expanded_keywords TEXT NOT NULL,  -- JSON array
                        expansion_type TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        usage_count INTEGER DEFAULT 0,
                        UNIQUE(original_keyword, expansion_type)
                    )
                """)
                
                # 쿼리 확장 통계 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS query_expansion_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_query TEXT NOT NULL,
                        expanded_query TEXT NOT NULL,
                        expansion_count INTEGER NOT NULL,
                        improvement_score REAL,  -- 검색 개선 점수
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_expansion_cache_keyword ON keyword_expansion_cache(original_keyword)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_expansion_stats_query ON query_expansion_stats(original_query)")
                
                logger.info("Keyword expansion cache initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize expansion cache: {e}")
    
    def expand_query(self, query: str, max_expansions: int = 5) -> ExpandedQuery:
        """쿼리 확장 수행"""
        try:
            words = self._tokenize_query(query)
            expansions = []
            expanded_terms = set()
            boost_terms = {}
            
            for word in words:
                if len(word) > 1:  # 한 글자 단어 제외
                    expansion = self._expand_keyword(word, max_expansions)
                    if expansion and expansion.expanded_keywords:
                        expansions.append(expansion)
                        expanded_terms.update(expansion.expanded_keywords)
                        
                        # 확장 타입별 가중치 설정
                        weight = self._get_expansion_weight(expansion.expansion_type)
                        for term in expansion.expanded_keywords:
                            boost_terms[term] = weight
            
            # 확장된 쿼리 생성
            expanded_query = self._build_expanded_query(query, expanded_terms, boost_terms)
            
            # 통계 저장
            self._save_expansion_stats(query, expanded_query, len(expanded_terms))
            
            return ExpandedQuery(
                original_query=query,
                expanded_query=expanded_query,
                expansions=expansions,
                boost_terms=boost_terms,
                total_expansion_count=len(expanded_terms)
            )
            
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return ExpandedQuery(
                original_query=query,
                expanded_query=query,
                expansions=[],
                boost_terms={},
                total_expansion_count=0
            )
    
    def _tokenize_query(self, query: str) -> List[str]:
        """쿼리 토큰화"""
        # 간단한 토큰화 (공백 및 특수문자 기준)
        tokens = re.findall(r'[가-힣a-zA-Z0-9]+', query)
        return [token for token in tokens if len(token) > 1]
    
    def _expand_keyword(self, keyword: str, max_expansions: int) -> Optional[KeywordExpansion]:
        """단일 키워드 확장"""
        try:
            # 캐시에서 먼저 확인
            cached_expansion = self._get_cached_expansion(keyword)
            if cached_expansion:
                return cached_expansion
            
            expanded_keywords = set()
            synonyms = set()
            related_terms = set()
            domain_terms = set()
            expansion_types = []
            
            keyword_lower = keyword.lower()
            
            # 1. 동의어 확장
            if keyword_lower in self.banking_dict.synonyms:
                synonyms = self.banking_dict.synonyms[keyword_lower].copy()
                expanded_keywords.update(synonyms)
                expansion_types.append("synonym")
            
            # 2. 연관 용어 확장
            if keyword_lower in self.banking_dict.related_terms:
                related_terms = self.banking_dict.related_terms[keyword_lower].copy()
                expanded_keywords.update(list(related_terms)[:max_expansions//2])
                expansion_types.append("related")
            
            # 3. 도메인 계층 확장
            domain_matches = self._find_domain_matches(keyword_lower)
            if domain_matches:
                domain_terms = domain_matches
                expanded_keywords.update(list(domain_terms)[:max_expansions//3])
                expansion_types.append("domain")
            
            # 4. 약어 확장
            if keyword.upper() in self.banking_dict.abbreviations:
                full_term = self.banking_dict.abbreviations[keyword.upper()]
                expanded_keywords.add(full_term)
                expansion_types.append("abbreviation")
            
            # 약어의 역방향 확장
            for abbr, full_term in self.banking_dict.abbreviations.items():
                if keyword_lower in full_term.lower():
                    expanded_keywords.add(abbr)
                    expansion_types.append("reverse_abbreviation")
            
            # 5. 형태소 변형 확장
            morphological_variants = self.morphological_analyzer.get_morphological_variants(keyword)
            expanded_keywords.update(morphological_variants)
            if len(morphological_variants) > 1:
                expansion_types.append("morphological")
            
            # 원본 키워드 제거
            expanded_keywords.discard(keyword)
            expanded_keywords.discard(keyword_lower)
            
            if not expanded_keywords:
                return None
            
            # 확신도 계산
            confidence = self._calculate_expansion_confidence(
                keyword, expanded_keywords, expansion_types
            )
            
            expansion = KeywordExpansion(
                original_keyword=keyword,
                expanded_keywords=expanded_keywords,
                synonyms=synonyms,
                related_terms=related_terms,
                domain_terms=domain_terms,
                confidence=confidence,
                expansion_type="|".join(expansion_types)
            )
            
            # 캐시에 저장
            self._cache_expansion(expansion)
            
            return expansion
            
        except Exception as e:
            logger.error(f"Keyword expansion failed for '{keyword}': {e}")
            return None
    
    def _find_domain_matches(self, keyword: str) -> Set[str]:
        """도메인 계층에서 관련 용어 찾기"""
        matches = set()
        
        for domain, categories in self.banking_dict.domain_hierarchy.items():
            for category, terms in categories.items():
                if keyword in terms:
                    # 같은 카테고리의 다른 용어들 추가
                    matches.update(terms)
                    matches.discard(keyword)
                elif any(keyword in term for term in terms):
                    # 부분 매칭되는 용어들 추가
                    matches.update([term for term in terms if keyword in term])
        
        return matches
    
    def _calculate_expansion_confidence(self, original: str, expansions: Set[str], 
                                      expansion_types: List[str]) -> float:
        """확장 확신도 계산"""
        base_confidence = 0.5
        
        # 확장 타입별 가중치
        type_weights = {
            "synonym": 0.3,
            "related": 0.2,
            "domain": 0.2,
            "abbreviation": 0.4,
            "reverse_abbreviation": 0.3,
            "morphological": 0.1
        }
        
        confidence_boost = sum(type_weights.get(exp_type, 0.1) for exp_type in expansion_types)
        
        # 확장 수에 따른 조정 (너무 많으면 신뢰도 감소)
        expansion_penalty = max(0, (len(expansions) - 5) * 0.05)
        
        final_confidence = min(1.0, base_confidence + confidence_boost - expansion_penalty)
        return final_confidence
    
    def _get_expansion_weight(self, expansion_type: str) -> float:
        """확장 타입별 검색 가중치"""
        type_weights = {
            "synonym": 1.0,      # 동의어는 동등한 가중치
            "related": 0.8,      # 연관 용어는 약간 낮은 가중치
            "domain": 0.7,       # 도메인 용어는 중간 가중치
            "abbreviation": 0.9, # 약어는 높은 가중치
            "morphological": 0.6 # 형태소 변형은 낮은 가중치
        }
        
        # 복합 타입인 경우 평균값 사용
        if "|" in expansion_type:
            types = expansion_type.split("|")
            weights = [type_weights.get(t, 0.5) for t in types]
            return sum(weights) / len(weights)
        
        return type_weights.get(expansion_type, 0.5)
    
    def _build_expanded_query(self, original_query: str, expanded_terms: Set[str], 
                            boost_terms: Dict[str, float]) -> str:
        """확장된 쿼리 구성"""
        if not expanded_terms:
            return original_query
        
        # 원본 쿼리를 기본으로 하고, 확장 용어들을 OR 조건으로 추가
        expanded_parts = []
        
        # 원본 쿼리 (높은 가중치)
        expanded_parts.append(f"({original_query})^2.0")
        
        # 확장 용어들 (개별 가중치 적용)
        for term in expanded_terms:
            weight = boost_terms.get(term, 0.5)
            expanded_parts.append(f"({term})^{weight:.1f}")
        
        return " OR ".join(expanded_parts)
    
    def _get_cached_expansion(self, keyword: str) -> Optional[KeywordExpansion]:
        """캐시된 확장 결과 조회"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT expanded_keywords, expansion_type, confidence
                    FROM keyword_expansion_cache
                    WHERE original_keyword = ?
                    ORDER BY confidence DESC
                    LIMIT 1
                """, (keyword,))
                
                row = cursor.fetchone()
                if row:
                    expanded_keywords = set(json.loads(row[0]))
                    expansion_type = row[1]
                    confidence = row[2]
                    
                    # 사용 횟수 업데이트
                    cursor.execute("""
                        UPDATE keyword_expansion_cache 
                        SET usage_count = usage_count + 1
                        WHERE original_keyword = ? AND expansion_type = ?
                    """, (keyword, expansion_type))
                    
                    return KeywordExpansion(
                        original_keyword=keyword,
                        expanded_keywords=expanded_keywords,
                        synonyms=set(),
                        related_terms=set(),
                        domain_terms=set(),
                        confidence=confidence,
                        expansion_type=expansion_type
                    )
                
        except Exception as e:
            logger.error(f"Failed to get cached expansion: {e}")
        
        return None
    
    def _cache_expansion(self, expansion: KeywordExpansion):
        """확장 결과 캐싱"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO keyword_expansion_cache
                    (original_keyword, expanded_keywords, expansion_type, confidence)
                    VALUES (?, ?, ?, ?)
                """, (
                    expansion.original_keyword,
                    json.dumps(list(expansion.expanded_keywords)),
                    expansion.expansion_type,
                    expansion.confidence
                ))
                
        except Exception as e:
            logger.error(f"Failed to cache expansion: {e}")
    
    def _save_expansion_stats(self, original_query: str, expanded_query: str, 
                            expansion_count: int):
        """확장 통계 저장"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO query_expansion_stats
                    (original_query, expanded_query, expansion_count)
                    VALUES (?, ?, ?)
                """, (original_query, expanded_query, expansion_count))
                
        except Exception as e:
            logger.error(f"Failed to save expansion stats: {e}")
    
    def get_expansion_statistics(self) -> Dict[str, Any]:
        """확장 통계 조회"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 가장 자주 확장되는 키워드
                cursor.execute("""
                    SELECT original_keyword, usage_count, expansion_type
                    FROM keyword_expansion_cache
                    ORDER BY usage_count DESC
                    LIMIT 20
                """)
                
                popular_expansions = [
                    {'keyword': row[0], 'usage_count': row[1], 'type': row[2]}
                    for row in cursor.fetchall()
                ]
                
                # 확장 타입별 통계
                cursor.execute("""
                    SELECT expansion_type, COUNT(*) as count, AVG(confidence) as avg_confidence
                    FROM keyword_expansion_cache
                    GROUP BY expansion_type
                    ORDER BY count DESC
                """)
                
                expansion_types = {}
                for row in cursor.fetchall():
                    expansion_types[row[0]] = {
                        'count': row[1],
                        'avg_confidence': round(row[2], 3)
                    }
                
                # 최근 쿼리 확장 현황
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_expansions,
                        AVG(expansion_count) as avg_expansion_count,
                        COUNT(CASE WHEN created_at >= date('now', '-7 days') THEN 1 END) as recent_expansions
                    FROM query_expansion_stats
                """)
                
                row = cursor.fetchone()
                expansion_summary = {
                    'total_expansions': row[0] if row else 0,
                    'avg_expansion_count': round(row[1], 2) if row and row[1] else 0,
                    'recent_expansions': row[2] if row else 0
                }
                
                return {
                    'popular_expansions': popular_expansions,
                    'expansion_types': expansion_types,
                    'expansion_summary': expansion_summary,
                    'dictionary_stats': {
                        'synonyms_count': sum(len(terms) for terms in self.banking_dict.synonyms.values()),
                        'related_terms_count': sum(len(terms) for terms in self.banking_dict.related_terms.values()),
                        'abbreviations_count': len(self.banking_dict.abbreviations),
                        'domain_terms_count': sum(
                            len(terms) for category in self.banking_dict.domain_hierarchy.values()
                            for terms in category.values()
                        )
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get expansion statistics: {e}")
            return {
                'popular_expansions': [],
                'expansion_types': {},
                'expansion_summary': {},
                'dictionary_stats': {}
            }
    
    def add_custom_synonym(self, term: str, synonyms: List[str]) -> bool:
        """사용자 정의 동의어 추가"""
        try:
            if term.lower() not in self.banking_dict.synonyms:
                self.banking_dict.synonyms[term.lower()] = set()
            
            self.banking_dict.synonyms[term.lower()].update(synonyms)
            
            # 캐시 무효화 (해당 용어의 캐시 삭제)
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM keyword_expansion_cache 
                    WHERE original_keyword = ?
                """, (term,))
            
            logger.info(f"Added custom synonyms for '{term}': {synonyms}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add custom synonym: {e}")
            return False


# 전역 인스턴스
_keyword_expansion_engine: Optional[KeywordExpansionEngine] = None


def get_keyword_expansion_engine(db_manager=None) -> KeywordExpansionEngine:
    """키워드 확장 엔진 싱글톤 반환"""
    global _keyword_expansion_engine
    if _keyword_expansion_engine is None:
        if db_manager is None:
            from app.core.database import get_database_manager
            db_manager = get_database_manager()
        _keyword_expansion_engine = KeywordExpansionEngine(db_manager)
    return _keyword_expansion_engine