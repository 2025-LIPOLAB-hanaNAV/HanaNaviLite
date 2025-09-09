#!/usr/bin/env python3
"""
Answer Quality Enhancement System
Phase 2 고급 검색 기능 - 답변 품질 향상 및 신뢰도 시스템
"""

import re
import logging
import math
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import sqlite3
import json

logger = logging.getLogger(__name__)


class AnswerStyle(Enum):
    """답변 스타일"""
    SIMPLE = "간단"      # 간단명료한 답변
    DETAILED = "상세"    # 상세한 설명
    TECHNICAL = "전문"   # 전문적/기술적
    BEGINNER = "초급"    # 초보자용
    EXECUTIVE = "임원"   # 경영진용
    CUSTOMER = "고객"    # 고객 대상


class ConfidenceLevel(Enum):
    """신뢰도 수준"""
    VERY_HIGH = "매우높음"  # 0.9 이상
    HIGH = "높음"          # 0.7-0.9  
    MEDIUM = "보통"        # 0.5-0.7
    LOW = "낮음"           # 0.3-0.5
    VERY_LOW = "매우낮음"   # 0.3 미만


@dataclass
class SourceReliability:
    """출처 신뢰도 정보"""
    document_id: int
    title: str
    reliability_score: float
    reliability_factors: List[str]
    document_type: str
    creation_date: datetime
    authority_level: str  # "official", "internal", "external", "unknown"


@dataclass
class AnswerConfidence:
    """답변 신뢰도 정보"""
    confidence_score: float
    confidence_level: ConfidenceLevel
    confidence_factors: List[str]
    uncertainty_indicators: List[str]
    source_reliability: List[SourceReliability]
    reasoning: str


@dataclass 
class StyledAnswer:
    """스타일이 적용된 답변"""
    original_answer: str
    styled_answer: str
    style_type: AnswerStyle
    style_adjustments: List[str]
    target_audience: str


@dataclass
class QualityMetrics:
    """답변 품질 메트릭"""
    relevance_score: float      # 관련성 점수
    completeness_score: float   # 완성도 점수  
    clarity_score: float        # 명확성 점수
    accuracy_score: float       # 정확성 점수
    overall_quality: float      # 전체 품질 점수
    improvement_suggestions: List[str]


class SourceReliabilityAnalyzer:
    """출처 신뢰도 분석기"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.authority_patterns = self._initialize_authority_patterns()
        self.reliability_weights = self._initialize_reliability_weights()
    
    def _initialize_authority_patterns(self) -> Dict[str, List[str]]:
        """권위성 패턴 초기화"""
        return {
            "official": [  # 공식 문서 패턴
                r"금융위원회", r"금융감독원", r"한국은행", r"예금보험공사",
                r"공문", r"공고", r"시행령", r"시행규칙", r"규정", r"지침",
                r"금감원", r"금융위", r"한은", r"예보"
            ],
            
            "regulatory": [  # 규제 관련 패턴
                r"바젤\s*III?", r"IFRS", r"자본적정성", r"유동성비율",
                r"스트레스\s*테스트", r"내부통제", r"준법감시"
            ],
            
            "internal_policy": [  # 내부 정책 패턴
                r"내부규정", r"업무규정", r"처리지침", r"운영기준",
                r"매뉴얼", r"가이드라인", r"절차서", r"표준"
            ],
            
            "technical": [  # 기술 문서 패턴
                r"시스템", r"API", r"인터페이스", r"데이터베이스",
                r"네트워크", r"보안", r"아키텍처", r"개발"
            ],
            
            "outdated": [  # 구형/비신뢰 패턴
                r"임시", r"draft", r"초안", r"검토중", r"참고용",
                r"비공식", r"개인", r"메모", r"노트"
            ]
        }
    
    def _initialize_reliability_weights(self) -> Dict[str, float]:
        """신뢰도 가중치 초기화"""
        return {
            "official": 1.0,        # 공식 문서
            "regulatory": 0.95,     # 규제 문서
            "internal_policy": 0.85, # 내부 정책
            "technical": 0.75,      # 기술 문서
            "general": 0.6,         # 일반 문서
            "outdated": 0.3,        # 구형 문서
            "unknown": 0.5          # 분류 불가
        }
    
    def analyze_source_reliability(self, document_data: Dict[str, Any]) -> SourceReliability:
        """출처 신뢰도 분석"""
        try:
            doc_id = document_data.get('id', 0)
            title = document_data.get('title', '') or ''
            content = document_data.get('content', '') or ''
            file_name = document_data.get('file_name', '') or ''
            created_at = document_data.get('created_at', datetime.now())
            
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif not isinstance(created_at, datetime):
                created_at = datetime.now()
            
            # 권위성 수준 결정
            authority_level = self._determine_authority_level(title, content, file_name)
            
            # 기본 신뢰도 점수
            base_score = self.reliability_weights.get(authority_level, 0.5)
            
            # 신뢰도 요인들 분석
            reliability_factors = []
            score_adjustments = []
            
            # 1. 문서 최신성 (최근 문서일수록 신뢰도 높음)
            days_old = (datetime.now() - created_at).days
            if days_old <= 30:
                score_adjustments.append(0.1)
                reliability_factors.append("최신 문서 (30일 이내)")
            elif days_old <= 90:
                score_adjustments.append(0.05)
                reliability_factors.append("비교적 최신 (90일 이내)")
            elif days_old > 365:
                score_adjustments.append(-0.1)
                reliability_factors.append(f"오래된 문서 ({days_old}일 경과)")
            
            # 2. 제목의 공식성 지표
            if any(pattern for pattern in self.authority_patterns["official"]
                   if re.search(pattern, title, re.IGNORECASE)):
                score_adjustments.append(0.15)
                reliability_factors.append("공식 기관 발행")
            
            # 3. 문서 유형 분석
            doc_type = self._classify_document_type(title, file_name)
            type_bonus = {
                "regulation": 0.2,
                "policy": 0.15, 
                "manual": 0.1,
                "notice": 0.08,
                "memo": -0.1
            }
            
            if doc_type in type_bonus:
                score_adjustments.append(type_bonus[doc_type])
                reliability_factors.append(f"문서 유형: {doc_type}")
            
            # 4. 내용 완성도 (길이, 구조 등)
            content_score = self._assess_content_completeness(content)
            if content_score > 0.8:
                score_adjustments.append(0.05)
                reliability_factors.append("완성도 높은 내용")
            elif content_score < 0.3:
                score_adjustments.append(-0.05)
                reliability_factors.append("내용 부족")
            
            # 최종 신뢰도 점수 계산
            final_score = base_score + sum(score_adjustments)
            final_score = max(0.0, min(1.0, final_score))  # 0-1 범위 제한
            
            return SourceReliability(
                document_id=doc_id,
                title=title,
                reliability_score=final_score,
                reliability_factors=reliability_factors,
                document_type=doc_type,
                creation_date=created_at,
                authority_level=authority_level
            )
            
        except Exception as e:
            logger.error(f"Source reliability analysis failed: {e}")
            return SourceReliability(
                document_id=document_data.get('id', 0),
                title=document_data.get('title', '') or '',
                reliability_score=0.3,
                reliability_factors=["분석 실패"],
                document_type="unknown",
                creation_date=datetime.now(),
                authority_level="unknown"
            )
    
    def _determine_authority_level(self, title: str, content: str, file_name: str) -> str:
        """권위성 수준 결정"""
        text = (title + " " + content[:500] + " " + file_name).lower()
        
        # 우선순위대로 확인
        for authority_level, patterns in self.authority_patterns.items():
            if authority_level == "outdated":  # 구형 문서는 마지막에 확인
                continue
                
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return authority_level
        
        # 구형 문서 확인
        for pattern in self.authority_patterns["outdated"]:
            if re.search(pattern, text, re.IGNORECASE):
                return "outdated"
        
        return "general"
    
    def _classify_document_type(self, title: str, file_name: str) -> str:
        """문서 유형 분류"""
        text = (title + " " + file_name).lower()
        
        type_patterns = {
            "regulation": [r"규정", r"규칙", r"지침", r"기준", r"준칙"],
            "policy": [r"정책", r"방침", r"전략", r"계획"],
            "manual": [r"매뉴얼", r"가이드", r"안내", r"절차"],
            "notice": [r"공지", r"알림", r"발표", r"소식"],
            "report": [r"보고서", r"분석", r"현황", r"결과"],
            "form": [r"양식", r"서식", r"신청서", r"확인서"],
            "memo": [r"메모", r"노트", r"임시", r"초안"]
        }
        
        for doc_type, patterns in type_patterns.items():
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                return doc_type
        
        return "general"
    
    def _assess_content_completeness(self, content: str) -> float:
        """내용 완성도 평가"""
        if not content:
            return 0.0
        
        score = 0.0
        
        # 길이 점수 (적정 길이일 때 높은 점수)
        length = len(content)
        if 200 <= length <= 5000:
            score += 0.3
        elif 100 <= length < 200:
            score += 0.2
        elif length > 5000:
            score += 0.25
        
        # 구조적 요소 점수
        structure_indicators = [
            r'\n\d+\.',      # 번호 매긴 목록
            r'[가-힣]{2,}:',  # 한글 레이블
            r'[-•]\s',       # 불릿 포인트
            r'제\d+조',      # 조문
            r'별표\s*\d+'    # 별표
        ]
        
        structure_score = sum(0.1 for pattern in structure_indicators 
                            if re.search(pattern, content))
        score += min(structure_score, 0.4)
        
        # 전문성 지표 점수
        professional_terms = [
            r'금융', r'은행', r'대출', r'예금', r'투자', r'보험',
            r'규정', r'절차', r'기준', r'시스템', r'관리'
        ]
        
        term_score = sum(0.05 for term in professional_terms 
                        if re.search(term, content, re.IGNORECASE))
        score += min(term_score, 0.3)
        
        return min(score, 1.0)


class AnswerConfidenceCalculator:
    """답변 신뢰도 계산기"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.reliability_analyzer = SourceReliabilityAnalyzer(db_manager)
        self.uncertainty_patterns = self._initialize_uncertainty_patterns()
    
    def _initialize_uncertainty_patterns(self) -> List[str]:
        """불확실성 표현 패턴"""
        return [
            r'아마도?', r'추정', r'예상', r'가능성', r'아닐까',
            r'확실하지\s*않', r'명확하지\s*않', r'정확하지\s*않',
            r'불명확', r'애매', r'모호', r'불분명',
            r'일부', r'부분적', r'제한적', r'한정적',
            r'\?', r'의문', r'궁금', r'확인.*필요'
        ]
    
    def calculate_confidence(self, answer: str, source_documents: List[Dict], 
                           search_results: List[Dict]) -> AnswerConfidence:
        """답변 신뢰도 계산"""
        try:
            # 출처 문서 신뢰도 분석
            source_reliability = []
            for doc in source_documents:
                reliability = self.reliability_analyzer.analyze_source_reliability(doc)
                source_reliability.append(reliability)
            
            # 기본 신뢰도 점수 계산
            confidence_factors = []
            confidence_score = 0.5  # 기본 점수
            
            # 1. 출처 문서 품질 점수
            if source_reliability:
                avg_source_reliability = sum(sr.reliability_score for sr in source_reliability) / len(source_reliability)
                confidence_score += (avg_source_reliability - 0.5) * 0.4  # 최대 0.4점 추가
                
                high_quality_sources = sum(1 for sr in source_reliability if sr.reliability_score > 0.8)
                if high_quality_sources > 0:
                    confidence_factors.append(f"고품질 출처 {high_quality_sources}개")
            
            # 2. 다중 출처 일치도
            if len(source_documents) > 1:
                confidence_score += 0.1
                confidence_factors.append(f"다중 출처 확인 ({len(source_documents)}개 문서)")
            
            if len(source_documents) >= 3:
                confidence_score += 0.1
                confidence_factors.append("충분한 출처 확보")
            
            # 3. 답변 길이 및 완성도
            answer_completeness = self._assess_answer_completeness(answer)
            if answer_completeness > 0.8:
                confidence_score += 0.15
                confidence_factors.append("완성도 높은 답변")
            elif answer_completeness < 0.3:
                confidence_score -= 0.1
                confidence_factors.append("불완전한 답변")
            
            # 4. 불확실성 표현 감지
            uncertainty_indicators = self._detect_uncertainty(answer)
            if uncertainty_indicators:
                confidence_score -= 0.2
            
            # 5. 구체성 점수 (숫자, 날짜, 구체적 용어 포함)
            specificity_score = self._calculate_specificity(answer)
            if specificity_score > 0.5:
                confidence_score += 0.1
                confidence_factors.append("구체적 정보 포함")
            
            # 6. 검색 결과와의 일치도
            if search_results:
                search_relevance = sum(result.get('score', 0.5) for result in search_results) / len(search_results)
                if search_relevance > 0.8:
                    confidence_score += 0.1
                    confidence_factors.append("높은 검색 관련성")
            
            # 최종 점수 정규화
            confidence_score = max(0.0, min(1.0, confidence_score))
            
            # 신뢰도 수준 결정
            confidence_level = self._determine_confidence_level(confidence_score)
            
            # 추론 생성
            reasoning = self._generate_confidence_reasoning(
                confidence_score, confidence_factors, uncertainty_indicators, source_reliability
            )
            
            return AnswerConfidence(
                confidence_score=confidence_score,
                confidence_level=confidence_level,
                confidence_factors=confidence_factors,
                uncertainty_indicators=uncertainty_indicators,
                source_reliability=source_reliability,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return AnswerConfidence(
                confidence_score=0.3,
                confidence_level=ConfidenceLevel.LOW,
                confidence_factors=["계산 오류"],
                uncertainty_indicators=["신뢰도 분석 실패"],
                source_reliability=[],
                reasoning="신뢰도 계산 중 오류가 발생했습니다."
            )
    
    def _assess_answer_completeness(self, answer: str) -> float:
        """답변 완성도 평가"""
        if not answer:
            return 0.0
        
        score = 0.0
        
        # 길이 점수
        length = len(answer)
        if 50 <= length <= 1000:
            score += 0.4
        elif 20 <= length < 50:
            score += 0.2
        elif length > 1000:
            score += 0.3
        
        # 문장 구조 점수
        sentences = answer.split('.')
        if len(sentences) >= 2:
            score += 0.2
        
        # 정보 밀도 점수 (명사의 비율)
        words = answer.split()
        if words:
            # 간단한 명사 추정 (한글 2글자 이상)
            nouns = [word for word in words if re.match(r'^[가-힣]{2,}$', word)]
            noun_ratio = len(nouns) / len(words)
            score += min(noun_ratio, 0.4)
        
        return min(score, 1.0)
    
    def _detect_uncertainty(self, answer: str) -> List[str]:
        """불확실성 표현 감지"""
        indicators = []
        
        for pattern in self.uncertainty_patterns:
            if re.search(pattern, answer, re.IGNORECASE):
                indicators.append(pattern)
        
        return indicators[:3]  # 최대 3개만 반환
    
    def _calculate_specificity(self, answer: str) -> float:
        """구체성 점수 계산"""
        score = 0.0
        
        # 숫자 포함 여부
        if re.search(r'\d+', answer):
            score += 0.2
        
        # 날짜 포함 여부
        date_patterns = [r'\d{4}년', r'\d{1,2}월', r'\d{1,2}일']
        if any(re.search(pattern, answer) for pattern in date_patterns):
            score += 0.2
        
        # 구체적 용어 (%, 원, 억, 만 등)
        specific_terms = [r'%', r'원', r'억', r'만', r'건', r'개', r'회']
        specific_count = sum(1 for term in specific_terms if re.search(term, answer))
        score += min(specific_count * 0.1, 0.3)
        
        # 전문 용어 밀도
        professional_terms = [
            r'금리', r'대출', r'예금', r'투자', r'보험', r'계좌',
            r'규정', r'절차', r'승인', r'신청', r'처리'
        ]
        term_count = sum(1 for term in professional_terms if re.search(term, answer))
        score += min(term_count * 0.05, 0.3)
        
        return min(score, 1.0)
    
    def _determine_confidence_level(self, score: float) -> ConfidenceLevel:
        """신뢰도 수준 결정"""
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _generate_confidence_reasoning(self, score: float, factors: List[str], 
                                     uncertainty: List[str], 
                                     source_reliability: List[SourceReliability]) -> str:
        """신뢰도 추론 생성"""
        parts = [f"신뢰도 점수: {score:.2f}/1.0"]
        
        if factors:
            parts.append(f"긍정 요인: {', '.join(factors)}")
        
        if uncertainty:
            parts.append(f"불확실성 지표: {', '.join(uncertainty[:2])}")
        
        if source_reliability:
            avg_reliability = sum(sr.reliability_score for sr in source_reliability) / len(source_reliability)
            parts.append(f"출처 평균 신뢰도: {avg_reliability:.2f}")
            
            high_quality = [sr for sr in source_reliability if sr.reliability_score > 0.8]
            if high_quality:
                parts.append(f"고신뢰도 출처: {len(high_quality)}개")
        
        return "; ".join(parts)


class AnswerStyleAdjuster:
    """답변 스타일 조정기"""
    
    def __init__(self):
        self.style_templates = self._initialize_style_templates()
        self.audience_profiles = self._initialize_audience_profiles()
    
    def _initialize_style_templates(self) -> Dict[AnswerStyle, Dict[str, Any]]:
        """스타일 템플릿 초기화"""
        return {
            AnswerStyle.SIMPLE: {
                "max_length": 200,
                "sentence_complexity": "simple",
                "technical_terms": "minimal",
                "structure": "direct",
                "tone": "friendly"
            },
            
            AnswerStyle.DETAILED: {
                "max_length": 800,
                "sentence_complexity": "complex", 
                "technical_terms": "explained",
                "structure": "comprehensive",
                "tone": "informative"
            },
            
            AnswerStyle.TECHNICAL: {
                "max_length": 600,
                "sentence_complexity": "complex",
                "technical_terms": "full",
                "structure": "precise",
                "tone": "professional"
            },
            
            AnswerStyle.BEGINNER: {
                "max_length": 300,
                "sentence_complexity": "simple",
                "technical_terms": "explained",
                "structure": "step_by_step",
                "tone": "educational"
            },
            
            AnswerStyle.EXECUTIVE: {
                "max_length": 150,
                "sentence_complexity": "concise",
                "technical_terms": "business",
                "structure": "summary",
                "tone": "formal"
            },
            
            AnswerStyle.CUSTOMER: {
                "max_length": 250,
                "sentence_complexity": "moderate",
                "technical_terms": "customer_friendly",
                "structure": "helpful",
                "tone": "polite"
            }
        }
    
    def _initialize_audience_profiles(self) -> Dict[str, AnswerStyle]:
        """대상 고객별 기본 스타일"""
        return {
            "임직원": AnswerStyle.TECHNICAL,
            "신입사원": AnswerStyle.BEGINNER,
            "중간관리자": AnswerStyle.DETAILED,
            "임원": AnswerStyle.EXECUTIVE,
            "고객": AnswerStyle.CUSTOMER,
            "일반": AnswerStyle.SIMPLE
        }
    
    def adjust_answer_style(self, answer: str, target_style: AnswerStyle, 
                          audience: str = "일반") -> StyledAnswer:
        """답변 스타일 조정"""
        try:
            template = self.style_templates[target_style]
            adjustments = []
            styled_answer = answer
            
            # 1. 길이 조정
            max_length = template["max_length"]
            if len(styled_answer) > max_length:
                styled_answer = self._truncate_intelligently(styled_answer, max_length)
                adjustments.append(f"길이 조정 ({len(answer)} -> {len(styled_answer)} 글자)")
            
            # 2. 문장 복잡도 조정
            if template["sentence_complexity"] == "simple":
                styled_answer = self._simplify_sentences(styled_answer)
                adjustments.append("문장 단순화")
            elif template["sentence_complexity"] == "concise":
                styled_answer = self._make_concise(styled_answer)
                adjustments.append("간결화")
            
            # 3. 전문 용어 처리
            if template["technical_terms"] == "minimal":
                styled_answer = self._reduce_technical_terms(styled_answer)
                adjustments.append("전문 용어 최소화")
            elif template["technical_terms"] == "explained":
                styled_answer = self._add_term_explanations(styled_answer)
                adjustments.append("전문 용어 설명 추가")
            elif template["technical_terms"] == "customer_friendly":
                styled_answer = self._make_customer_friendly(styled_answer)
                adjustments.append("고객 친화적 용어로 변경")
            
            # 4. 구조 조정
            if template["structure"] == "step_by_step":
                styled_answer = self._add_step_structure(styled_answer)
                adjustments.append("단계별 구조화")
            elif template["structure"] == "summary":
                styled_answer = self._create_executive_summary(styled_answer)
                adjustments.append("요약 형태로 변경")
            
            # 5. 어조 조정
            tone_adjustment = self._adjust_tone(styled_answer, template["tone"])
            if tone_adjustment != styled_answer:
                styled_answer = tone_adjustment
                adjustments.append(f"어조 조정 ({template['tone']})")
            
            return StyledAnswer(
                original_answer=answer,
                styled_answer=styled_answer,
                style_type=target_style,
                style_adjustments=adjustments,
                target_audience=audience
            )
            
        except Exception as e:
            logger.error(f"Style adjustment failed: {e}")
            return StyledAnswer(
                original_answer=answer,
                styled_answer=answer,
                style_type=target_style,
                style_adjustments=["스타일 조정 실패"],
                target_audience=audience
            )
    
    def _truncate_intelligently(self, text: str, max_length: int) -> str:
        """지능적 텍스트 단축"""
        if len(text) <= max_length:
            return text
        
        # 문장 단위로 자르기 시도
        sentences = text.split('.')
        truncated = ""
        
        for sentence in sentences:
            if len(truncated + sentence + '.') <= max_length - 10:  # 여유 공간
                truncated += sentence + '.'
            else:
                break
        
        if not truncated:
            # 강제로 자르고 ... 추가
            truncated = text[:max_length-3] + "..."
        else:
            truncated += " (요약됨)"
        
        return truncated
    
    def _simplify_sentences(self, text: str) -> str:
        """문장 단순화"""
        # 복잡한 표현을 간단하게 변경
        simplifications = {
            r'에 대해서는': '은',
            r'에 대하여': '에',
            r'관련하여': '에 대해',
            r'하였습니다': '했습니다',
            r'되었습니다': '됐습니다',
            r'이용하실 수 있습니다': '이용할 수 있습니다',
            r'확인하시기 바랍니다': '확인해주세요'
        }
        
        simplified = text
        for pattern, replacement in simplifications.items():
            simplified = re.sub(pattern, replacement, simplified)
        
        return simplified
    
    def _make_concise(self, text: str) -> str:
        """간결하게 만들기"""
        # 불필요한 표현 제거
        concise_patterns = [
            (r'\s+', ' '),  # 연속 공백 제거
            (r'그런데', ''),
            (r'그리고\s*또한', '또한'),
            (r'이와\s*같이', '이렇게'),
            (r'다시\s*말해서', '즉'),
            (r'좀\s*더', '더'),
            (r'아시다시피', ''),
            (r'말씀드리면', '')
        ]
        
        concise = text
        for pattern, replacement in concise_patterns:
            concise = re.sub(pattern, replacement, concise)
        
        return concise.strip()
    
    def _reduce_technical_terms(self, text: str) -> str:
        """전문 용어 최소화"""
        term_replacements = {
            'DSR': '총부채원리금상환비율',
            'DTI': '총부채상환비율',
            'LTV': '주택담보대출비율',
            'KYC': '고객확인절차',
            '컴플라이언스': '준법관리',
            '포트폴리오': '투자자산',
            '마진': '수수료',
            '프리미엄': '할증료'
        }
        
        simplified = text
        for tech_term, simple_term in term_replacements.items():
            # Avoid replacing if the technical term is already followed by its explanation
            # e.g., DSR(총부채원리금상환비율) should not become 총부채원리금상환비율(총부채원리금상환비율)
            pattern = rf'\b{tech_term}\b(?:\s*\({re.escape(simple_term)}\))?'
            simplified = re.sub(pattern, simple_term, simplified, flags=re.IGNORECASE)
        
        return simplified
    
    def _add_term_explanations(self, text: str) -> str:
        """전문 용어 설명 추가"""
        explanations = {
            'DSR': 'DSR(총부채원리금상환비율)',
            'DTI': 'DTI(총부채상환비율)', 
            'LTV': 'LTV(주택담보대출비율)',
            'KYC': 'KYC(고객확인절차)',
            '컴플라이언스': '컴플라이언스(준법관리)'
        }
        
        explained = text
        for term, explanation in explanations.items():
            if term in explained and explanation not in explained:
                explained = explained.replace(term, explanation, 1)  # 첫 번째만 교체
        
        return explained
    
    def _make_customer_friendly(self, text: str) -> str:
        """고객 친화적으로 변경"""
        friendly_replacements = {
            '신청하시기 바랍니다': '신청해주시기 바랍니다',
            '처리됩니다': '처리해드립니다',
            '확인하세요': '확인해주세요',
            '이용하세요': '이용해주세요',
            '방문하세요': '방문해주세요',
            '규정': '기준',
            '절차': '과정',
            '승인': '허가'
        }
        
        friendly = text
        for formal, friendly_term in friendly_replacements.items():
            friendly = re.sub(formal, friendly_term, friendly)
        
        return friendly
    
    def _add_step_structure(self, text: str) -> str:
        """단계별 구조 추가"""
        # 이미 번호가 있는지 확인
        if re.search(r'\d+\.', text):
            return text
        
        # 문장을 단계별로 구조화
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        if len(sentences) <= 1:
            return text
        
        structured = ""
        for i, sentence in enumerate(sentences[:5], 1):  # 최대 5단계
            if sentence:
                structured += f"{i}. {sentence}.\n"
        
        return structured.strip()
    
    def _create_executive_summary(self, text: str) -> str:
        """임원용 요약 생성"""
        # 핵심 내용만 추출
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        if not sentences:
            return text
        
        # 첫 문장과 마지막 문장, 또는 가장 중요해 보이는 문장
        summary_parts = []
        
        # 첫 번째 문장 (보통 주요 내용)
        if sentences:
            summary_parts.append(sentences[0])
        
        # 숫자나 구체적 정보가 포함된 문장 우선 선택
        for sentence in sentences[1:]:
            if (re.search(r'\d+', sentence) or 
                any(keyword in sentence for keyword in ['중요', '필수', '반드시', '주의'])):
                summary_parts.append(sentence)
                break
        
        # 3문장을 넘지 않도록 제한
        summary = '. '.join(summary_parts[:3])
        if not summary.endswith('.'):
            summary += '.'
        
        return summary
    
    def _adjust_tone(self, text: str, tone: str) -> str:
        """어조 조정"""
        tone_adjustments = {
            "friendly": {
                r'입니다\.': '입니다!',
                r'됩니다\.': '돼요.',
                r'하세요': '해주세요'
            },
            "formal": {
                r'해주세요': '하시기 바랍니다',
                r'됐습니다': '되었습니다',
                r'했습니다': '하였습니다'
            },
            "polite": {
                r'하세요': '해주시면 됩니다',
                r'됩니다': '됩니다만',
                r'입니다': '입니다만'
            }
        }
        
        if tone in tone_adjustments:
            adjusted = text
            for pattern, replacement in tone_adjustments[tone].items():
                adjusted = re.sub(pattern, replacement, adjusted)
            return adjusted
        
        return text


class AnswerQualityEvaluator:
    """답변 품질 평가기"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.confidence_calculator = AnswerConfidenceCalculator(db_manager)
    
    def evaluate_answer_quality(self, answer: str, question: str, 
                              source_documents: List[Dict], 
                              search_results: List[Dict]) -> QualityMetrics:
        """답변 품질 종합 평가"""
        try:
            # 각 품질 차원별 점수 계산
            relevance_score = self._calculate_relevance(answer, question, search_results)
            completeness_score = self._calculate_completeness(answer, question)
            clarity_score = self._calculate_clarity(answer)
            accuracy_score = self._calculate_accuracy(answer, source_documents)
            
            # 전체 품질 점수 (가중 평균)
            weights = {'relevance': 0.3, 'completeness': 0.25, 'clarity': 0.2, 'accuracy': 0.25}
            overall_quality = (
                relevance_score * weights['relevance'] +
                completeness_score * weights['completeness'] +
                clarity_score * weights['clarity'] +
                accuracy_score * weights['accuracy']
            )
            
            # 개선 제안 생성
            improvement_suggestions = self._generate_improvement_suggestions(
                relevance_score, completeness_score, clarity_score, accuracy_score
            )
            
            return QualityMetrics(
                relevance_score=relevance_score,
                completeness_score=completeness_score,
                clarity_score=clarity_score,
                accuracy_score=accuracy_score,
                overall_quality=overall_quality,
                improvement_suggestions=improvement_suggestions
            )
            
        except Exception as e:
            logger.error(f"Quality evaluation failed: {e}")
            return QualityMetrics(
                relevance_score=0.3,
                completeness_score=0.3,
                clarity_score=0.3,
                accuracy_score=0.3,
                overall_quality=0.3,
                improvement_suggestions=["품질 평가 실패"]
            )
    
    def _calculate_relevance(self, answer: str, question: str, search_results: List[Dict]) -> float:
        """관련성 점수 계산"""
        score = 0.5  # 기본 점수
        
        # 질문의 키워드가 답변에 포함되는지 확인
        question_words = set(re.findall(r'[가-힣a-zA-Z0-9]+', question.lower()))
        answer_words = set(re.findall(r'[가-힣a-zA-Z0-9]+', answer.lower()))
        
        if question_words and answer_words:
            overlap = question_words.intersection(answer_words)
            overlap_ratio = len(overlap) / len(question_words)
            score += overlap_ratio * 0.3
        
        # 검색 결과와의 일치도
        if search_results:
            avg_search_score = sum(result.get('score', 0.5) for result in search_results) / len(search_results)
            score += (avg_search_score - 0.5) * 0.2
        
        return min(score, 1.0)
    
    def _calculate_completeness(self, answer: str, question: str) -> float:
        """완성도 점수 계산"""
        score = 0.3  # 기본 점수
        
        # 답변 길이 적절성
        answer_length = len(answer)
        if 100 <= answer_length <= 800:
            score += 0.3
        elif 50 <= answer_length < 100:
            score += 0.2
        elif answer_length > 800:
            score += 0.25
        
        # 정보의 구체성 (숫자, 날짜, 절차 등)
        concrete_elements = [
            r'\d+%', r'\d+원', r'\d+일', r'\d+월', r'\d+년',
            r'절차', r'방법', r'단계', r'조건', r'기준'
        ]
        
        concrete_count = sum(1 for pattern in concrete_elements 
                           if re.search(pattern, answer))
        score += min(concrete_count * 0.05, 0.2)
        
        # 질문 유형별 필수 요소 확인
        if '어떻게' in question or '방법' in question:
            if any(word in answer for word in ['절차', '방법', '단계']):
                score += 0.2
        
        if '언제' in question or '기간' in question:
            if re.search(r'\d+일|\d+월|\d+년|기간|시간', answer):
                score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_clarity(self, answer: str) -> float:
        """명확성 점수 계산"""
        score = 0.4  # 기본 점수
        
        # 문장 구조의 명확성
        sentences = answer.split('.')
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if valid_sentences:
            avg_sentence_length = sum(len(s) for s in valid_sentences) / len(valid_sentences)
            if 20 <= avg_sentence_length <= 80:  # 적절한 문장 길이
                score += 0.2
        
        # 구조적 명확성 (번호, 불릿 포인트 등)
        structure_indicators = [r'\d+\.', r'[-•]\s', r'첫째|둘째|셋째', r'먼저|다음|마지막']
        if any(re.search(pattern, answer) for pattern in structure_indicators):
            score += 0.15
        
        # 불명확한 표현 확인 (감점 요소)
        unclear_patterns = [r'아마', r'가능성', r'추정', r'애매', r'불분명']
        unclear_count = sum(1 for pattern in unclear_patterns 
                          if re.search(pattern, answer, re.IGNORECASE))
        score -= unclear_count * 0.05
        
        # 전문용어 대비 설명의 적절성
        technical_terms = len(re.findall(r'[A-Z]{2,}|[가-힣]*규정|[가-힣]*절차', answer))
        explanation_indicators = len(re.findall(r'\([^)]+\)|\s즉\s|\s예를\s들어', answer))
        
        if technical_terms > 0 and explanation_indicators / max(technical_terms, 1) >= 0.5:
            score += 0.15
        
        return max(0.1, min(score, 1.0))
    
    def _calculate_accuracy(self, answer: str, source_documents: List[Dict]) -> float:
        """정확성 점수 계산 (출처 기반)"""
        if not source_documents:
            return 0.5  # 출처가 없으면 중간 점수
        
        score = 0.3  # 기본 점수
        
        # 출처 문서와의 일치도 확인 (키워드 기반)
        answer_words = set(re.findall(r'[가-힣a-zA-Z0-9]+', answer.lower()))
        
        total_overlap = 0
        total_source_words = 0
        
        for doc in source_documents:
            content = (doc.get('content', '') or '') + ' ' + (doc.get('title', '') or '')
            source_words = set(re.findall(r'[가-힣a-zA-Z0-9]+', content.lower()))
            
            if source_words:
                overlap = answer_words.intersection(source_words)
                total_overlap += len(overlap)
                total_source_words += len(source_words)
        
        if total_source_words > 0:
            overlap_ratio = total_overlap / total_source_words
            score += min(overlap_ratio * 2, 0.4)  # 최대 0.4점 추가
        
        # 구체적 정보의 일관성 (숫자, 날짜 등)
        answer_numbers = re.findall(r'\d+', answer)
        source_numbers = []
        for doc in source_documents:
            content = (doc.get('content', '') or '')
            source_numbers.extend(re.findall(r'\d+', content))
        
        if answer_numbers and source_numbers:
            number_matches = sum(1 for num in answer_numbers if num in source_numbers)
            score += min(number_matches / len(answer_numbers) * 0.3, 0.3)
        
        return min(score, 1.0)
    
    def _generate_improvement_suggestions(self, relevance: float, completeness: float, 
                                        clarity: float, accuracy: float) -> List[str]:
        """개선 제안 생성"""
        suggestions = []
        
        if relevance < 0.6:
            suggestions.append("질문과 더 직접적으로 관련된 내용을 포함하세요")
        
        if completeness < 0.6:
            suggestions.append("더 구체적이고 상세한 정보를 제공하세요")
        
        if clarity < 0.6:
            suggestions.append("문장을 더 명확하고 이해하기 쉽게 구성하세요")
        
        if accuracy < 0.6:
            suggestions.append("출처 문서의 정확한 정보를 반영하세요")
        
        # 전체적으로 낮은 경우
        overall = (relevance + completeness + clarity + accuracy) / 4
        if overall < 0.5:
            suggestions.append("답변의 전반적인 품질 개선이 필요합니다")
        
        return suggestions[:3]  # 최대 3개 제안


# 전역 인스턴스들
_answer_quality_evaluator: Optional[AnswerQualityEvaluator] = None
_answer_style_adjuster: Optional[AnswerStyleAdjuster] = None


def get_answer_quality_evaluator(db_manager=None) -> AnswerQualityEvaluator:
    """답변 품질 평가기 싱글톤 반환"""
    global _answer_quality_evaluator
    if _answer_quality_evaluator is None:
        if db_manager is None:
            from app.core.database import get_database_manager
            db_manager = get_database_manager()
        _answer_quality_evaluator = AnswerQualityEvaluator(db_manager)
    return _answer_quality_evaluator


def get_answer_style_adjuster() -> AnswerStyleAdjuster:
    """답변 스타일 조정기 싱글톤 반환"""
    global _answer_style_adjuster
    if _answer_style_adjuster is None:
        _answer_style_adjuster = AnswerStyleAdjuster()
    return _answer_style_adjuster