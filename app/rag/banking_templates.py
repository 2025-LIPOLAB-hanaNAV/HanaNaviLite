#!/usr/bin/env python3
"""
Banking Domain-Specific Answer Templates
Phase 2 고급 검색 기능 - 은행 업무 특화 답변 템플릿 및 용어 해설
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class BankingDomain(Enum):
    """은행 업무 도메인"""
    LENDING = "대출"           # 대출 업무
    DEPOSIT = "예적금"         # 예적금 업무
    CARD = "카드"             # 카드 업무
    INVESTMENT = "투자"        # 투자 업무
    FOREIGN_EXCHANGE = "외환"   # 외환 업무
    DIGITAL_BANKING = "디지털"  # 디지털 뱅킹
    COMPLIANCE = "컴플라이언스" # 준법감시
    RISK_MANAGEMENT = "위험관리" # 위험관리
    CUSTOMER_SERVICE = "고객서비스" # 고객 서비스
    OPERATIONS = "운영"        # 운영 업무
    GENERAL = "일반"          # 일반


class QuestionType(Enum):
    """질문 유형"""
    PROCEDURE = "절차"         # 절차 문의
    REQUIREMENT = "조건"       # 조건 문의
    DEFINITION = "정의"        # 정의 문의
    CALCULATION = "계산"       # 계산 문의
    COMPARISON = "비교"        # 비교 문의
    TROUBLESHOOT = "문제해결"  # 문제 해결
    REGULATION = "규정"        # 규정 문의
    CONTACT = "연락처"         # 연락처 문의


@dataclass
class AnswerTemplate:
    """답변 템플릿"""
    domain: BankingDomain
    question_type: QuestionType
    template_structure: List[str]
    required_fields: List[str]
    optional_fields: List[str] = field(default_factory=list)
    tone: str = "formal"
    sample_answer: str = ""


@dataclass
class TermDefinition:
    """용어 정의"""
    term: str
    definition: str
    domain: BankingDomain
    related_terms: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    english_term: Optional[str] = None


@dataclass
class StructuredAnswer:
    """구조화된 답변"""
    main_answer: str
    template_used: str
    domain: BankingDomain
    question_type: QuestionType
    explained_terms: List[TermDefinition]
    additional_info: Dict[str, str] = field(default_factory=dict)
    disclaimers: List[str] = field(default_factory=list)


class BankingTerminologyDictionary:
    """은행 업무 전문 용어 사전"""
    
    def __init__(self):
        self.terms = self._initialize_banking_terms()
        self.term_patterns = self._initialize_term_patterns()
    
    def _initialize_banking_terms(self) -> Dict[str, TermDefinition]:
        """은행 업무 전문 용어 초기화"""
        terms = {}
        
        # 대출 관련 용어
        lending_terms = [
            TermDefinition(
                term="DSR",
                definition="총부채원리금상환비율로, 개인이 대출받을 수 있는 한도를 결정하는 지표입니다. 연소득 대비 모든 대출의 원리금 상환액 비율을 말합니다.",
                domain=BankingDomain.LENDING,
                related_terms=["DTI", "LTV", "대출한도"],
                examples=["DSR 40% → 연소득 5000만원인 경우 연간 원리금 상환액이 2000만원까지 가능"],
                english_term="Debt Service Ratio"
            ),
            
            TermDefinition(
                term="DTI",
                definition="총부채상환비율로, 연소득 대비 총 대출 상환액의 비율을 나타내는 지표입니다.",
                domain=BankingDomain.LENDING,
                related_terms=["DSR", "LTV"],
                examples=["DTI 60% 규제 → 연소득 대비 총 대출 상환액이 60%를 초과할 수 없음"],
                english_term="Debt To Income"
            ),
            
            TermDefinition(
                term="LTV",
                definition="주택담보대출비율로, 주택 담보가치 대비 대출금액의 비율을 나타냅니다.",
                domain=BankingDomain.LENDING,
                related_terms=["DSR", "DTI", "담보비율"],
                examples=["LTV 70% → 5억원 아파트에 최대 3.5억원까지 대출 가능"],
                english_term="Loan To Value"
            ),
            
            TermDefinition(
                term="신용등급",
                definition="개인의 신용상태를 평가한 등급으로, 1등급부터 10등급까지 구분됩니다. 등급이 높을수록 금리 우대 혜택을 받을 수 있습니다.",
                domain=BankingDomain.LENDING,
                related_terms=["신용점수", "NICE", "KCB"],
                examples=["1-3등급: 우량, 4-6등급: 일반, 7-10등급: 주의"]
            )
        ]
        
        # 예적금 관련 용어
        deposit_terms = [
            TermDefinition(
                term="복리",
                definition="원금에 대한 이자가 다시 원금에 포함되어 이자가 계산되는 방식입니다.",
                domain=BankingDomain.DEPOSIT,
                related_terms=["단리", "연복리", "월복리"],
                examples=["100만원을 연 5% 복리로 2년 예치 → 110만 5천원"]
            ),
            
            TermDefinition(
                term="단리",
                definition="원금에 대해서만 이자를 계산하는 방식입니다.",
                domain=BankingDomain.DEPOSIT,
                related_terms=["복리", "이자계산"],
                examples=["100만원을 연 5% 단리로 2년 예치 → 110만원"]
            ),
            
            TermDefinition(
                term="중도해지",
                definition="예적금 만기 이전에 해지하는 것을 말합니다. 일반적으로 중도해지이율이 적용되어 이자가 감소합니다.",
                domain=BankingDomain.DEPOSIT,
                related_terms=["만기", "중도해지이율", "위약금"],
                examples=["정기예금 1년 만기를 6개월에 중도해지 시 낮은 이율 적용"]
            )
        ]
        
        # 카드 관련 용어
        card_terms = [
            TermDefinition(
                term="연회비",
                definition="신용카드 사용을 위해 매년 지불하는 수수료입니다.",
                domain=BankingDomain.CARD,
                related_terms=["카드혜택", "면제조건"],
                examples=["골드카드 연회비 10만원, 연 300만원 이상 사용시 면제"]
            ),
            
            TermDefinition(
                term="캐시백",
                definition="카드 사용금액의 일정 비율을 현금으로 돌려주는 혜택입니다.",
                domain=BankingDomain.CARD,
                related_terms=["포인트", "마일리지", "할인"],
                examples=["생활비 결제 1% 캐시백 → 100만원 사용 시 1만원 적립"]
            )
        ]
        
        # 투자 관련 용어
        investment_terms = [
            TermDefinition(
                term="펀드",
                definition="여러 투자자로부터 자금을 모아 전문가가 대신 투자하는 상품입니다.",
                domain=BankingDomain.INVESTMENT,
                related_terms=["ETF", "수익률", "위험도"],
                examples=["주식형 펀드, 채권형 펀드, 혼합형 펀드"]
            ),
            
            TermDefinition(
                term="변동성",
                definition="투자상품 가격의 변동 정도를 나타내는 지표입니다. 변동성이 클수록 위험도가 높습니다.",
                domain=BankingDomain.INVESTMENT,
                related_terms=["위험도", "수익률", "표준편차"],
                examples=["주식 > 펀드 > 채권 > 예금 순으로 변동성 높음"]
            )
        ]
        
        # 디지털 뱅킹 관련 용어
        digital_terms = [
            TermDefinition(
                term="오픈뱅킹",
                definition="금융결제원이 제공하는 서비스로, 하나의 앱에서 여러 은행 계좌를 조회하고 이체할 수 있습니다.",
                domain=BankingDomain.DIGITAL_BANKING,
                related_terms=["API", "핀테크", "계좌연결"],
                examples=["토스, 카카오페이 등에서 타행 계좌 조회 가능"]
            ),
            
            TermDefinition(
                term="생체인증",
                definition="지문, 얼굴, 음성 등 생체정보를 이용한 본인확인 방법입니다.",
                domain=BankingDomain.DIGITAL_BANKING,
                related_terms=["본인확인", "보안", "인증"],
                examples=["지문인증, FaceID, 음성인증"]
            )
        ]
        
        # 컴플라이언스 관련 용어
        compliance_terms = [
            TermDefinition(
                term="KYC",
                definition="고객확인절차로, 금융기관이 고객의 신원을 확인하고 자금세탁을 방지하기 위한 절차입니다.",
                domain=BankingDomain.COMPLIANCE,
                related_terms=["AML", "CDD", "본인확인"],
                examples=["계좌 개설 시 신분증 확인, 자금 출처 확인"],
                english_term="Know Your Customer"
            ),
            
            TermDefinition(
                term="AML",
                definition="자금세탁방지를 위한 규제 및 절차입니다.",
                domain=BankingDomain.COMPLIANCE,
                related_terms=["KYC", "STR", "의심거래"],
                examples=["고액 현금거래 신고, 의심거래 모니터링"],
                english_term="Anti-Money Laundering"
            )
        ]
        
        # 모든 용어를 딕셔너리로 변환
        all_terms = lending_terms + deposit_terms + card_terms + investment_terms + digital_terms + compliance_terms
        
        for term_def in all_terms:
            terms[term_def.term.lower()] = term_def
        
        return terms
    
    def _initialize_term_patterns(self) -> Dict[str, str]:
        """용어 인식 패턴"""
        return {
            r'\bDSR\b': 'dsr',
            r'\bDTI\b': 'dti', 
            r'\bLTV\b': 'ltv',
            r'\bKYC\b': 'kyc',
            r'\bAML\b': 'aml',
            r'신용등급': '신용등급',
            r'복리': '복리',
            r'단리': '단리',
            r'중도해지': '중도해지',
            r'연회비': '연회비',
            r'캐시백': '캐시백',
            r'펀드': '펀드',
            r'변동성': '변동성',
            r'오픈뱅킹': '오픈뱅킹',
            r'생체인증': '생체인증'
        }
    
    def get_term_definition(self, term: str) -> Optional[TermDefinition]:
        """용어 정의 조회"""
        return self.terms.get(term.lower())
    
    def find_terms_in_text(self, text: str) -> List[TermDefinition]:
        """텍스트에서 전문 용어 찾기"""
        found_terms = []
        
        for pattern, term_key in self.term_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                term_def = self.terms.get(term_key)
                if term_def:
                    found_terms.append(term_def)
        
        return found_terms


class BankingAnswerTemplateEngine:
    """은행 업무 답변 템플릿 엔진"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.terminology = BankingTerminologyDictionary()
        self.domain_classifiers = self._initialize_domain_classifiers()
        self.question_classifiers = self._initialize_question_classifiers()
    
    def _initialize_templates(self) -> Dict[Tuple[BankingDomain, QuestionType], AnswerTemplate]:
        """답변 템플릿 초기화"""
        templates = {}
        
        # 대출 절차 템플릿
        templates[(BankingDomain.LENDING, QuestionType.PROCEDURE)] = AnswerTemplate(
            domain=BankingDomain.LENDING,
            question_type=QuestionType.PROCEDURE,
            template_structure=[
                "[대출종류] 신청 절차는 다음과 같습니다:",
                "1. 필요서류 준비: [required_documents]",
                "2. 신청방법: [application_method]",
                "3. 심사과정: [review_process]", 
                "4. 승인 후 처리: [approval_process]",
                "",
                "※ 자세한 사항은 [contact_info]로 문의하시기 바랍니다."
            ],
            required_fields=["대출종류", "required_documents", "application_method"],
            optional_fields=["review_process", "approval_process", "contact_info"],
            tone="formal"
        )
        
        # 대출 조건 템플릿
        templates[(BankingDomain.LENDING, QuestionType.REQUIREMENT)] = AnswerTemplate(
            domain=BankingDomain.LENDING,
            question_type=QuestionType.REQUIREMENT,
            template_structure=[
                "[대출종류]의 대출 조건은 다음과 같습니다:",
                "",
                "▶ 대출대상: [target_customer]",
                "▶ 대출한도: [loan_limit]",
                "▶ 대출금리: [interest_rate]",
                "▶ 대출기간: [loan_term]",
                "▶ 상환방법: [repayment_method]",
                "",
                "※ 상기 조건은 고객의 신용등급 및 기타 조건에 따라 달라질 수 있습니다."
            ],
            required_fields=["대출종류", "target_customer", "loan_limit", "interest_rate"],
            optional_fields=["loan_term", "repayment_method"],
            tone="formal"
        )
        
        # 예적금 비교 템플릿
        templates[(BankingDomain.DEPOSIT, QuestionType.COMPARISON)] = AnswerTemplate(
            domain=BankingDomain.DEPOSIT,
            question_type=QuestionType.COMPARISON,
            template_structure=[
                "[product1]과 [product2]의 주요 차이점은 다음과 같습니다:",
                "",
                "구분 | [product1] | [product2]",
                "---|---|---",
                "금리 | [rate1] | [rate2]",
                "가입조건 | [condition1] | [condition2]",
                "특징 | [feature1] | [feature2]",
                "",
                "▶ 추천: [recommendation]"
            ],
            required_fields=["product1", "product2", "rate1", "rate2"],
            optional_fields=["condition1", "condition2", "feature1", "feature2", "recommendation"],
            tone="informative"
        )
        
        # 카드 혜택 템플릿
        templates[(BankingDomain.CARD, QuestionType.DEFINITION)] = AnswerTemplate(
            domain=BankingDomain.CARD,
            question_type=QuestionType.DEFINITION,
            template_structure=[
                "[card_name] 카드의 주요 혜택은 다음과 같습니다:",
                "",
                "🎯 주요 혜택:",
                "• [benefit1]",
                "• [benefit2]", 
                "• [benefit3]",
                "",
                "💰 연회비: [annual_fee]",
                "📋 가입조건: [eligibility]",
                "",
                "※ 자세한 혜택 내용은 카드 상품설명서를 확인하시기 바랍니다."
            ],
            required_fields=["card_name", "benefit1", "annual_fee"],
            optional_fields=["benefit2", "benefit3", "eligibility"],
            tone="friendly"
        )
        
        # 투자 위험도 템플릿
        templates[(BankingDomain.INVESTMENT, QuestionType.DEFINITION)] = AnswerTemplate(
            domain=BankingDomain.INVESTMENT,
            question_type=QuestionType.DEFINITION,
            template_structure=[
                "[product_name]의 투자 위험도와 특징을 안내드립니다:",
                "",
                "📊 위험등급: [risk_level] (1단계:매우낮음 ~ 5단계:매우높음)",
                "📈 기대수익률: [expected_return]",
                "⚠️ 주요 위험요소:",
                "• [risk1]",
                "• [risk2]",
                "",
                "💡 투자 시 주의사항:",
                "• 투자원금의 손실이 발생할 수 있습니다",
                "• 과거 수익률이 미래 수익을 보장하지 않습니다",
                "• [additional_warning]"
            ],
            required_fields=["product_name", "risk_level", "expected_return", "risk1"],
            optional_fields=["risk2", "additional_warning"],
            tone="cautious"
        )
        
        # 디지털 뱅킹 문제해결 템플릿
        templates[(BankingDomain.DIGITAL_BANKING, QuestionType.TROUBLESHOOT)] = AnswerTemplate(
            domain=BankingDomain.DIGITAL_BANKING,
            question_type=QuestionType.TROUBLESHOOT,
            template_structure=[
                "[issue_description] 문제 해결방법을 안내드립니다:",
                "",
                "🔧 해결방법:",
                "1단계: [step1]",
                "2단계: [step2]",
                "3단계: [step3]",
                "",
                "🔄 그래도 해결되지 않는다면:",
                "• [alternative1]",
                "• [alternative2]",
                "",
                "📞 추가 도움이 필요하시면 고객센터([phone])로 연락주세요."
            ],
            required_fields=["issue_description", "step1", "step2"],
            optional_fields=["step3", "alternative1", "alternative2", "phone"],
            tone="helpful"
        )
        
        # 컴플라이언스 규정 템플릿
        templates[(BankingDomain.COMPLIANCE, QuestionType.REGULATION)] = AnswerTemplate(
            domain=BankingDomain.COMPLIANCE,
            question_type=QuestionType.REGULATION,
            template_structure=[
                "[regulation_name]에 대해 안내드립니다:",
                "",
                "📋 규정 개요: [overview]",
                "🎯 적용 대상: [target]",
                "📝 주요 내용:",
                "• [content1]",
                "• [content2]",
                "• [content3]",
                "",
                "⚖️ 위반 시 제재: [penalty]",
                "📅 시행일: [effective_date]",
                "",
                "※ 자세한 규정은 관련 법령을 확인하시기 바랍니다."
            ],
            required_fields=["regulation_name", "overview", "target", "content1"],
            optional_fields=["content2", "content3", "penalty", "effective_date"],
            tone="formal"
        )
        
        # 일반 정의 템플릿
        templates[(BankingDomain.GENERAL, QuestionType.DEFINITION)] = AnswerTemplate(
            domain=BankingDomain.GENERAL,
            question_type=QuestionType.DEFINITION,
            template_structure=[
                "[term]에 대해 설명드리겠습니다:",
                "",
                "📖 정의: [definition]",
                "🔍 특징: [features]",
                "💡 예시: [examples]",
                "",
                "관련 정보가 더 필요하시면 언제든 문의해주세요."
            ],
            required_fields=["term", "definition"],
            optional_fields=["features", "examples"],
            tone="educational"
        )
        
        return templates
    
    def _initialize_domain_classifiers(self) -> Dict[BankingDomain, List[str]]:
        """도메인 분류 키워드"""
        return {
            BankingDomain.LENDING: [
                "대출", "융자", "차입", "신용대출", "담보대출", "주택담보대출",
                "DSR", "DTI", "LTV", "신용등급", "금리", "한도", "상환"
            ],
            BankingDomain.DEPOSIT: [
                "예금", "적금", "정기예금", "자유적금", "정기적금",
                "이자", "복리", "단리", "만기", "중도해지"
            ],
            BankingDomain.CARD: [
                "카드", "신용카드", "체크카드", "연회비", "포인트",
                "마일리지", "캐시백", "할인", "결제", "승인"
            ],
            BankingDomain.INVESTMENT: [
                "투자", "펀드", "주식", "채권", "ETF", "수익률",
                "위험도", "변동성", "포트폴리오", "분산투자"
            ],
            BankingDomain.FOREIGN_EXCHANGE: [
                "외환", "환율", "달러", "원화", "외화", "환전",
                "송금", "해외송금", "외화예금"
            ],
            BankingDomain.DIGITAL_BANKING: [
                "인터넷뱅킹", "모바일뱅킹", "앱", "디지털", "온라인",
                "오픈뱅킹", "간편결제", "생체인증", "공동인증서"
            ],
            BankingDomain.COMPLIANCE: [
                "컴플라이언스", "준법", "규정", "규제", "KYC", "AML",
                "자금세탁", "내부통제", "감시", "보고"
            ],
            BankingDomain.RISK_MANAGEMENT: [
                "리스크", "위험", "위험관리", "신용위험", "시장위험",
                "운영위험", "스트레스테스트", "자본적정성"
            ],
            BankingDomain.CUSTOMER_SERVICE: [
                "고객서비스", "상담", "문의", "민원", "불만", "개선",
                "서비스", "지원", "도움", "안내"
            ],
            BankingDomain.OPERATIONS: [
                "운영", "업무", "시스템", "프로세스", "절차", "처리",
                "정산", "결산", "관리", "모니터링"
            ]
        }
    
    def _initialize_question_classifiers(self) -> Dict[QuestionType, List[str]]:
        """질문 유형 분류 키워드"""
        return {
            QuestionType.PROCEDURE: [
                "절차", "방법", "어떻게", "단계", "과정", "진행",
                "신청", "처리", "접수", "순서"
            ],
            QuestionType.REQUIREMENT: [
                "조건", "자격", "기준", "요건", "필요", "해당",
                "대상", "가능", "자격요건", "신청자격"
            ],
            QuestionType.DEFINITION: [
                "무엇", "정의", "의미", "뜻", "이란", "란",
                "설명", "개념", "내용", "특징"
            ],
            QuestionType.CALCULATION: [
                "계산", "산출", "구하", "얼마", "금액", "비용",
                "수수료", "이자", "세금", "요금"
            ],
            QuestionType.COMPARISON: [
                "비교", "차이", "다른", "구분", "vs", "대비",
                "어느", "선택", "추천", "좋은"
            ],
            QuestionType.TROUBLESHOOT: [
                "문제", "오류", "안됨", "실패", "에러", "고장",
                "작동", "해결", "복구", "수정"
            ],
            QuestionType.REGULATION: [
                "규정", "규칙", "법", "제재", "처벌", "위반",
                "준수", "의무", "금지", "허용"
            ],
            QuestionType.CONTACT: [
                "연락처", "전화", "문의", "상담", "지점", "센터",
                "번호", "주소", "위치", "찾기"
            ]
        }
    
    def classify_question(self, question: str) -> Tuple[BankingDomain, QuestionType]:
        """질문 분류"""
        question_lower = question.lower()
        
        # 도메인 분류
        domain_scores = {}
        for domain, keywords in self.domain_classifiers.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > 0:
                domain_scores[domain] = score
        
        best_domain = max(domain_scores.keys(), key=lambda k: domain_scores[k]) if domain_scores else BankingDomain.GENERAL
        
        # 질문 유형 분류
        type_scores = {}
        for q_type, keywords in self.question_classifiers.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > 0:
                type_scores[q_type] = score
        
        best_type = max(type_scores.keys(), key=lambda k: type_scores[k]) if type_scores else QuestionType.DEFINITION
        
        return best_domain, best_type
    
    def generate_structured_answer(self, question: str, base_answer: str, 
                                 source_documents: List[Dict]) -> StructuredAnswer:
        """구조화된 답변 생성"""
        try:
            # 질문 분류
            domain, question_type = self.classify_question(question)
            
            # 해당 템플릿 찾기
            template = self.templates.get((domain, question_type))
            if not template:
                # 일반 템플릿으로 대체
                template = self.templates.get((BankingDomain.GENERAL, QuestionType.DEFINITION))
                if not template:
                    return self._create_fallback_answer(question, base_answer, domain, question_type)
            
            # 답변에서 전문 용어 찾기
            explained_terms = self.terminology.find_terms_in_text(base_answer + " " + question)
            
            # 템플릿 적용하여 구조화된 답변 생성
            structured_content = self._apply_template(template, base_answer, source_documents)
            
            # 면책 조항 추가
            disclaimers = self._generate_disclaimers(domain, question_type)
            
            # 추가 정보 생성
            additional_info = self._generate_additional_info(domain, question_type, source_documents)
            
            return StructuredAnswer(
                main_answer=structured_content,
                template_used=f"{domain.value}_{question_type.value}",
                domain=domain,
                question_type=question_type,
                explained_terms=explained_terms,
                additional_info=additional_info,
                disclaimers=disclaimers
            )
            
        except Exception as e:
            logger.error(f"Structured answer generation failed: {e}")
            return self._create_fallback_answer(question, base_answer, BankingDomain.GENERAL, QuestionType.DEFINITION)
    
    def _apply_template(self, template: AnswerTemplate, base_answer: str, 
                       source_documents: List[Dict]) -> str:
        """템플릿 적용"""
        try:
            # 기본 답변에서 정보 추출
            extracted_info = self._extract_information(base_answer, source_documents, template.required_fields)
            
            # 템플릿 구조를 실제 내용으로 채우기
            filled_template = []
            
            for line in template.template_structure:
                filled_line = line
                
                # 플레이스홀더 교체
                for field in template.required_fields + template.optional_fields:
                    placeholder = f"[{field}]"
                    if placeholder in filled_line:
                        value = extracted_info.get(field, "정보 없음")
                        filled_line = filled_line.replace(placeholder, value)
                
                filled_template.append(filled_line)
            
            return "\n".join(filled_template)
            
        except Exception as e:
            logger.error(f"Template application failed: {e}")
            return base_answer
    
    def _extract_information(self, base_answer: str, source_documents: List[Dict], 
                           required_fields: List[str]) -> Dict[str, str]:
        """기본 답변에서 정보 추출"""
        extracted = {}
        
        # 간단한 정보 추출 (키워드 기반)
        answer_lower = base_answer.lower()
        
        # 필드별 추출 로직
        field_extractors = {
            "대출종류": lambda text: self._extract_loan_type(text),
            "required_documents": lambda text: "신분증, 소득증명서, 재직증명서 등",
            "application_method": lambda text: "영업점 방문, 인터넷뱅킹, 모바일앱",
            "interest_rate": lambda text: self._extract_interest_rate(text),
            "loan_limit": lambda text: self._extract_loan_limit(text),
            "target_customer": lambda text: "만 19세 이상 소득이 있는 개인",
            "contact_info": lambda text: "고객센터 1588-0000",
            "term": lambda text: self._extract_main_term(text),
            "definition": lambda text: self._extract_definition(text)
        }
        
        for field in required_fields:
            if field in field_extractors:
                try:
                    extracted[field] = field_extractors[field](base_answer)
                except:
                    extracted[field] = "정보 확인 필요"
            else:
                extracted[field] = "상세 내용은 문의 바랍니다"
        
        return extracted
    
    def _extract_loan_type(self, text: str) -> str:
        """대출 종류 추출"""
        loan_types = ["신용대출", "담보대출", "주택담보대출", "전세자금대출", "마이너스통장"]
        for loan_type in loan_types:
            if loan_type in text:
                return loan_type
        return "개인대출"
    
    def _extract_interest_rate(self, text: str) -> str:
        """금리 정보 추출"""
        rate_pattern = r'(\d+\.?\d*)%'
        matches = re.findall(rate_pattern, text)
        if matches:
            return f"{matches[0]}% (변동금리 적용)"
        return "금리는 고객 신용도에 따라 차등 적용"
    
    def _extract_loan_limit(self, text: str) -> str:
        """대출 한도 추출"""
        limit_patterns = [r'(\d+,?\d*)\s*만원', r'(\d+)\s*억', r'최대\s*(\d+,?\d*)']
        for pattern in limit_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return f"최대 {matches[0]} 한도 내"
        return "개인별 심사를 통해 결정"
    
    def _extract_main_term(self, text: str) -> str:
        """주요 용어 추출"""
        # 첫 번째 문장에서 주요 용어 추출 시도
        first_sentence = text.split('.')[0] if '.' in text else text
        
        # 전문용어 패턴 매칭
        for term in self.terminology.terms.keys():
            if term in first_sentence.lower():
                return self.terminology.terms[term].term
        
        return "관련 용어"
    
    def _extract_definition(self, text: str) -> str:
        """정의 추출"""
        # 첫 번째 문장을 정의로 사용
        sentences = text.split('.')
        if sentences:
            return sentences[0].strip() + "."
        return text[:200] + "..." if len(text) > 200 else text
    
    def _generate_disclaimers(self, domain: BankingDomain, question_type: QuestionType) -> List[str]:
        """면책 조항 생성"""
        disclaimers = []
        
        if domain == BankingDomain.LENDING:
            disclaimers.extend([
                "대출 조건은 개인 신용도 및 소득에 따라 달라질 수 있습니다.",
                "상기 내용은 일반적인 안내사항이며, 정확한 조건은 상담을 통해 확인하시기 바랍니다."
            ])
        
        elif domain == BankingDomain.INVESTMENT:
            disclaimers.extend([
                "투자상품은 예금자보호법에 따라 보호되지 않습니다.",
                "투자 시 원금손실의 위험이 있으며, 과거 수익률이 미래 수익을 보장하지 않습니다."
            ])
        
        elif domain == BankingDomain.CARD:
            disclaimers.append("카드 혜택은 카드사 정책에 따라 변경될 수 있습니다.")
        
        elif domain == BankingDomain.COMPLIANCE:
            disclaimers.append("상기 내용은 안내 목적이며, 정확한 규정은 관련 법령을 확인하시기 바랍니다.")
        
        return disclaimers
    
    def _generate_additional_info(self, domain: BankingDomain, question_type: QuestionType, 
                                source_documents: List[Dict]) -> Dict[str, str]:
        """추가 정보 생성"""
        additional = {}
        
        if domain == BankingDomain.LENDING:
            additional["관련_서비스"] = "대출 상담, 대출계산기, 한도조회 서비스"
            additional["유의사항"] = "과도한 대출은 신용도 하락의 원인이 됩니다"
        
        elif domain == BankingDomain.INVESTMENT:
            additional["투자_교육"] = "투자 전 충분한 상품 이해와 위험도 검토가 필요합니다"
            additional["관련_상품"] = "적립식 펀드, 연금저축, ISA 계좌"
        
        if source_documents:
            additional["참고_문서"] = f"총 {len(source_documents)}개 문서 참조"
            recent_docs = [doc for doc in source_documents if "2024" in str(doc.get("created_at", ""))]
            if recent_docs:
                additional["최신_정보"] = f"{len(recent_docs)}개 최신 문서 포함"
        
        return additional
    
    def _create_fallback_answer(self, question: str, base_answer: str, 
                              domain: BankingDomain, question_type: QuestionType) -> StructuredAnswer:
        """대체 답변 생성"""
        return StructuredAnswer(
            main_answer=base_answer,
            template_used="fallback",
            domain=domain,
            question_type=question_type,
            explained_terms=[],
            additional_info={"상태": "템플릿 적용 실패"},
            disclaimers=["정확한 정보는 고객센터를 통해 확인하시기 바랍니다."]
        )
    
    def add_custom_template(self, domain: BankingDomain, question_type: QuestionType, 
                          template: AnswerTemplate) -> bool:
        """사용자 정의 템플릿 추가"""
        try:
            self.templates[(domain, question_type)] = template
            logger.info(f"Custom template added for {domain.value}_{question_type.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to add custom template: {e}")
            return False
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """사용 가능한 템플릿 목록"""
        return [
            {
                "domain": key[0].value,
                "question_type": key[1].value,
                "template_id": f"{key[0].value}_{key[1].value}"
            }
            for key in self.templates.keys()
        ]


# 전역 인스턴스
_banking_template_engine: Optional[BankingAnswerTemplateEngine] = None


def get_banking_template_engine() -> BankingAnswerTemplateEngine:
    """은행 업무 답변 템플릿 엔진 싱글톤 반환"""
    global _banking_template_engine
    if _banking_template_engine is None:
        _banking_template_engine = BankingAnswerTemplateEngine()
    return _banking_template_engine