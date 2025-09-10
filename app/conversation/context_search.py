#!/usr/bin/env python3
"""
컨텍스트 인식 검색 엔진
이전 대화 맥락을 고려한 검색 쿼리 생성 및 검색 결과 개선
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from app.conversation.session_manager import get_session_manager, ConversationTurn
from app.search.query_rewriter import get_query_rewriter

logger = logging.getLogger(__name__)


@dataclass
class SearchContext:
    """검색 컨텍스트 정보"""
    session_id: str
    original_query: str
    enhanced_query: str
    previous_queries: List[str]
    mentioned_entities: List[str]
    current_topics: List[str]
    reference_type: Optional[str] = None  # 'clarification', 'follow_up', 'new_topic'
    confidence: float = 1.0


@dataclass
class ContextualSearchResult:
    """컨텍스트를 포함한 검색 결과"""
    search_context: SearchContext
    search_results: List[Dict[str, Any]]
    context_explanation: str
    enhanced_query_used: str


class ContextAwareSearchEngine:
    """컨텍스트 인식 검색 엔진"""
    
    def __init__(self):
        self.session_manager = get_session_manager()
        self.query_rewriter = get_query_rewriter()
        self.pronoun_patterns = self._compile_pronoun_patterns()
        self.follow_up_patterns = self._compile_follow_up_patterns()
        self.clarification_patterns = self._compile_clarification_patterns()
    
    def _compile_pronoun_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """대명사 및 지시어 패턴 컴파일"""
        patterns = [
            (re.compile(r'(그것|그|이것|이|저것|저)'), 'pronoun'),
            (re.compile(r'(여기|거기|저기)'), 'location_pronoun'),
            (re.compile(r'(이거|그거|저거)'), 'demonstrative'),
            (re.compile(r'(이런|그런|저런)'), 'attributive'),
            (re.compile(r'(이렇게|그렇게|저렇게)'), 'adverbial'),
            (re.compile(r'(위의|앞의|전의|이전의)'), 'referential'),
        ]
        return patterns
    
    def _compile_follow_up_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """후속 질문 패턴 컴파일"""
        patterns = [
            (re.compile(r'(더|추가로|또한|그리고).*(자세히|설명|정보|내용)'), 'more_info'),
            (re.compile(r'(어떻게|어떤.*방법|방법은)'), 'how_to'),
            (re.compile(r'(왜|이유|원인)'), 'why'),
            (re.compile(r'(언제|시기|시점)'), 'when'),
            (re.compile(r'(어디|장소|위치)'), 'where'),
            (re.compile(r'(누가|누구|담당자)'), 'who'),
            (re.compile(r'(예시|예|사례|구체적)'), 'example'),
            (re.compile(r'(차이|비교|구별)'), 'comparison'),
        ]
        return patterns
    
    def _compile_clarification_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """명확화 요청 패턴 컴파일"""
        patterns = [
            (re.compile(r'\b(뭐|무엇|뭔가|무엇인가)\b.*\b(의미|뜻|말)\b'), 'meaning'),
            (re.compile(r'\b(설명해|알려줘|가르쳐|말해)\b'), 'explain'),
            (re.compile(r'\b(이해.*안.*돼|모르겠|헷갈려)\b'), 'confusion'),
            (re.compile(r'\b(확실|정확|맞)\b.*\b(한지|인지)\b'), 'confirmation'),
            (re.compile(r'\b(다시|한번\s*더)\b'), 'repeat'),
        ]
        return patterns
    
    def enhance_query_with_context(
        self,
        session_id: str,
        query: str,
        max_context_turns: int = 3
    ) -> SearchContext:
        """컨텍스트를 활용한 쿼리 개선
        
        Args:
            session_id: 세션 ID
            query: 원본 쿼리
            max_context_turns: 고려할 최대 컨텍스트 턴 수
            
        Returns:
            SearchContext: 개선된 검색 컨텍스트
        """
        # 이전 대화 내용 조회
        recent_turns = self.session_manager.get_session_turns(
            session_id,
            limit=max_context_turns
        )

        # LLM 재작성을 위한 대화 히스토리 구성
        conversation_history = [
            f"User: {t.user_message}\nAssistant: {t.assistant_message or ''}"
            for t in recent_turns[-max_context_turns:]
        ]

        # 기본 컨텍스트 초기화
        search_context = SearchContext(
            session_id=session_id,
            original_query=query,
            enhanced_query=query,
            previous_queries=[],
            mentioned_entities=[],
            current_topics=[],
            reference_type="new_topic"  # 기본값 설정
        )

        if recent_turns:
            # 이전 질문들 수집
            search_context.previous_queries = [
                turn.user_message for turn in recent_turns[-max_context_turns:]
            ]

            # 현재 주제들 수집
            session_topics = self.session_manager.get_session_topics(session_id)
            search_context.current_topics = [
                topic.topic_name for topic in session_topics if topic.is_active
            ]

            # 언급된 엔티티 추출
            search_context.mentioned_entities = self._extract_entities_from_turns(recent_turns)

            # 참조 타입 결정
            search_context.reference_type = self._determine_reference_type(
                query,
                recent_turns
            )

        # 쿼리 개선 (규칙 기반)
        enhanced_query = self._enhance_query(
            query,
            recent_turns,
            search_context
        )

        # LLM을 활용한 쿼리 재작성
        rewritten_query = self.query_rewriter.rewrite(
            enhanced_query,
            conversation_history
        )

        search_context.enhanced_query = rewritten_query
        search_context.confidence = self._calculate_context_confidence(
            query,
            recent_turns,
            search_context
        )

        logger.info(
            f"Enhanced query for session {session_id}: "
            f"'{query}' -> '{rewritten_query}' "
            f"(type: {search_context.reference_type}, confidence: {search_context.confidence:.2f})"
        )

        return search_context
    
    def _extract_entities_from_turns(self, turns: List[ConversationTurn]) -> List[str]:
        """대화 턴에서 엔티티 추출"""
        entities = []
        
        # 간단한 엔티티 추출 (향후 NER 모델로 대체 가능)
        entity_patterns = [
            r'\b[A-Z][a-zA-Z]+\b',  # 대문자로 시작하는 단어
            r'\b\d{4}년\b',  # 연도
            r'\b\d{1,2}월\b',  # 월
            r'\b\d{1,2}일\b',  # 일
            r'\b[가-힣]+은행\b',  # 은행명
            r'\b[가-힣]+지점\b',  # 지점명
            r'\b[가-힣]+부서\b',  # 부서명
        ]
        
        for turn in turns:
            text = f"{turn.user_message} {turn.assistant_message or ''}"
            
            for pattern in entity_patterns:
                matches = re.findall(pattern, text)
                entities.extend(matches)
        
        # 중복 제거 및 정리
        unique_entities = list(set(entities))
        
        # 너무 일반적인 단어들 제거
        common_words = {'그것', '이것', '저것', '여기', '거기', '저기'}
        entities = [entity for entity in unique_entities if entity not in common_words]
        
        return entities[:10]  # 최대 10개만 유지
    
    def _determine_reference_type(
        self, 
        query: str, 
        recent_turns: List[ConversationTurn]
    ) -> str:
        """참조 타입 결정"""
        if not recent_turns:
            return 'new_topic'
        
        query_lower = query.lower()
        
        # 대명사나 지시어가 있는지 확인
        has_pronouns = any(
            pattern.search(query_lower) for pattern, _ in self.pronoun_patterns
        )
        
        if has_pronouns:
            # 명확화 요청인지 확인
            for pattern, clarification_type in self.clarification_patterns:
                if pattern.search(query_lower):
                    return 'clarification'
            
            return 'follow_up'
        
        # 후속 질문 패턴 확인
        for pattern, follow_up_type in self.follow_up_patterns:
            if pattern.search(query_lower):
                return 'follow_up'
        
        # 이전 질문과의 유사도 확인 (간단한 키워드 기반)
        if recent_turns:
            last_query = recent_turns[-1].user_message.lower()
            common_keywords = set(query_lower.split()) & set(last_query.split())
            
            if len(common_keywords) >= 2:
                return 'follow_up'
        
        return 'new_topic'
    
    def _enhance_query(
        self,
        query: str,
        recent_turns: List[ConversationTurn],
        context: SearchContext
    ) -> str:
        """쿼리 개선 실행"""
        enhanced_query = query
        
        if context.reference_type == 'clarification':
            enhanced_query = self._handle_clarification(query, recent_turns, context)
        elif context.reference_type == 'follow_up':
            enhanced_query = self._handle_follow_up(query, recent_turns, context)
        elif context.reference_type == 'new_topic':
            enhanced_query = self._handle_new_topic(query, context)
        
        return enhanced_query
    
    def _handle_clarification(
        self,
        query: str,
        recent_turns: List[ConversationTurn],
        context: SearchContext
    ) -> str:
        """명확화 요청 처리"""
        if not recent_turns:
            return query
        
        last_turn = recent_turns[-1]
        
        # 대명사를 구체적인 내용으로 치환
        enhanced_query = query
        
        # "그것"이나 "이것" 등을 마지막 어시스턴트 응답의 주요 키워드로 치환
        if last_turn.assistant_message:
            # 간단한 키워드 추출 (향후 개선 가능)
            assistant_keywords = self._extract_key_terms(last_turn.assistant_message)
            
            for pattern, _ in self.pronoun_patterns:
                if pattern.search(query):
                    if assistant_keywords:
                        # 가장 중요해 보이는 키워드로 치환
                        main_keyword = assistant_keywords[0]
                        enhanced_query = pattern.sub(main_keyword, enhanced_query, count=1)
                        break
        
        # 컨텍스트 키워드 추가
        if context.current_topics:
            enhanced_query += f" {' '.join(context.current_topics)}"
        
        return enhanced_query.strip()
    
    def _handle_follow_up(
        self,
        query: str,
        recent_turns: List[ConversationTurn],
        context: SearchContext
    ) -> str:
        """후속 질문 처리"""
        enhanced_query = query
        
        # 이전 검색 쿼리에서 키워드 추출
        previous_keywords = []
        for turn in recent_turns[-2:]:  # 최근 2턴만 고려
            if turn.search_query:
                previous_keywords.extend(turn.search_query.split())
        
        # 중복 제거
        unique_keywords = list(set(previous_keywords))
        
        # 현재 쿼리에 없는 중요한 키워드 추가
        current_words = set(query.lower().split())
        additional_keywords = [
            kw for kw in unique_keywords 
            if kw.lower() not in current_words and len(kw) > 2
        ]
        
        if additional_keywords:
            enhanced_query += f" {' '.join(additional_keywords[:3])}"  # 최대 3개 추가
        
        # 현재 주제 키워드 추가
        if context.current_topics:
            topic_words = ' '.join(context.current_topics)
            if topic_words.lower() not in enhanced_query.lower():
                enhanced_query += f" {topic_words}"
        
        return enhanced_query.strip()
    
    def _handle_new_topic(
        self,
        query: str,
        context: SearchContext
    ) -> str:
        """새 주제 처리"""
        # 새 주제의 경우 원본 쿼리 유지하되, 약간의 개선만 수행
        enhanced_query = query
        
        # 언급된 엔티티 중 유용한 것들 추가
        if context.mentioned_entities:
            relevant_entities = [
                entity for entity in context.mentioned_entities
                if entity.lower() not in query.lower()
            ][:2]  # 최대 2개만 추가
            
            if relevant_entities:
                enhanced_query += f" {' '.join(relevant_entities)}"
        
        return enhanced_query.strip()
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """텍스트에서 주요 키워드 추출"""
        # 간단한 키워드 추출 (불용어 제거 + 길이 기준)
        stop_words = {
            '는', '은', '이', '가', '을', '를', '에', '에서', '으로', '로', '와', '과',
            '입니다', '습니다', '있습니다', '됩니다', '합니다', '해요', '이에요',
            '그리고', '하지만', '그러나', '또한', '따라서', '그래서', '의', '한도는',
            '연소득과', '신용등급에', '따라'
        }
        
        # 복합 키워드 우선 추출 (3글자 이상)
        compound_keywords = re.findall(r'[가-힣]{3,}', text)
        
        # 일반 한글 단어 추출 (2글자 이상)
        korean_words = re.findall(r'[가-힣]{2,}', text)
        
        # 복합 키워드를 우선하고, 불용어 제거
        all_words = compound_keywords + korean_words
        filtered_words = [word for word in all_words if word not in stop_words]
        
        # 빈도 계산 및 길이 가중치 적용
        word_freq = {}
        for word in filtered_words:
            weight = len(word) if len(word) >= 3 else 1  # 긴 단어에 가중치
            word_freq[word] = word_freq.get(word, 0) + weight
        
        # 빈도순으로 정렬하여 반환
        sorted_words = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)
        
        return sorted_words[:5]  # 상위 5개만 반환
    
    def _calculate_context_confidence(
        self,
        query: str,
        recent_turns: List[ConversationTurn],
        context: SearchContext
    ) -> float:
        """컨텍스트 활용 신뢰도 계산"""
        confidence = 1.0
        
        # 참조 타입에 따른 기본 신뢰도
        type_confidence = {
            'clarification': 0.9,
            'follow_up': 0.8,
            'new_topic': 1.0
        }
        confidence *= type_confidence.get(context.reference_type, 1.0)
        
        # 대명사나 지시어가 있으면서 컨텍스트가 없는 경우 신뢰도 하락
        has_pronouns = any(
            pattern.search(query.lower()) for pattern, _ in self.pronoun_patterns
        )
        
        if has_pronouns and not recent_turns:
            confidence *= 0.3
        
        # 이전 턴과의 시간 간격 고려 (시간이 오래 지났으면 신뢰도 하락)
        if recent_turns:
            import datetime
            last_turn_time = recent_turns[-1].created_at
            if last_turn_time:
                time_diff = (datetime.datetime.now() - last_turn_time).total_seconds()
                # 10분 이상 지났으면 신뢰도 감소
                if time_diff > 600:
                    confidence *= max(0.5, 1.0 - (time_diff - 600) / 3600)
        
        return max(0.1, min(1.0, confidence))
    
    def search_with_context(
        self,
        session_id: str,
        query: str,
        search_engine,  # 실제 검색 엔진 인스턴스
        max_context_turns: int = 3,
        **search_kwargs
    ) -> ContextualSearchResult:
        """컨텍스트를 고려한 검색 수행
        
        Args:
            session_id: 세션 ID
            query: 검색 쿼리
            search_engine: 실제 검색 엔진 객체
            max_context_turns: 고려할 최대 컨텍스트 턴 수
            **search_kwargs: 검색 엔진에 전달할 추가 인자
            
        Returns:
            ContextualSearchResult: 컨텍스트를 포함한 검색 결과
        """
        # 컨텍스트 분석 및 쿼리 개선
        search_context = self.enhance_query_with_context(
            session_id, 
            query, 
            max_context_turns
        )
        
        # 개선된 쿼리로 검색 수행
        try:
            search_results = search_engine.search(
                search_context.enhanced_query,
                original_query=search_context.original_query,
                **search_kwargs
            )
        except Exception as e:
            logger.error(f"Search failed with enhanced query, falling back to original: {e}")
            # 실패 시 원본 쿼리로 재시도
            search_results = search_engine.search(query, original_query=query, **search_kwargs)
            search_context.enhanced_query = query
            search_context.confidence *= 0.5
        
        # 컨텍스트 설명 생성
        context_explanation = self._generate_context_explanation(search_context)
        
        return ContextualSearchResult(
            search_context=search_context,
            search_results=search_results,
            context_explanation=context_explanation,
            enhanced_query_used=search_context.enhanced_query
        )
    
    def _generate_context_explanation(self, context: SearchContext) -> str:
        """컨텍스트 활용에 대한 설명 생성"""
        explanations = []
        
        if context.reference_type == 'clarification':
            explanations.append("이전 답변에 대한 명확화 요청으로 해석하여 관련 정보를 추가로 검색했습니다.")
        elif context.reference_type == 'follow_up':
            explanations.append("이전 대화의 연속선상에서 질문하신 것으로 파악하여 관련 맥락을 포함했습니다.")
        elif context.reference_type == 'new_topic':
            explanations.append("새로운 주제에 대한 질문으로 판단했습니다.")
        
        if context.current_topics:
            topics_str = ', '.join(context.current_topics)
            explanations.append(f"현재 대화 주제: {topics_str}")
        
        if context.enhanced_query != context.original_query:
            explanations.append(
                f"검색 쿼리를 '{context.original_query}'에서 "
                f"'{context.enhanced_query}'로 확장했습니다."
            )
        
        return ' '.join(explanations) if explanations else ""


# 전역 인스턴스
_context_search_engine = None

def get_context_search_engine() -> ContextAwareSearchEngine:
    """컨텍스트 검색 엔진 싱글톤 인스턴스 반환"""
    global _context_search_engine
    if _context_search_engine is None:
        _context_search_engine = ContextAwareSearchEngine()
    return _context_search_engine