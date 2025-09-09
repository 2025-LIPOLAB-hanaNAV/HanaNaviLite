#!/usr/bin/env python3
"""
대화 상태 관리 시스템
주제 변경 감지, 세션 타임아웃 처리, 대화 초기화 기능
"""

import re
import json
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

from app.conversation.session_manager import (
    get_session_manager, 
    ConversationSession, 
    ConversationTurn
)

logger = logging.getLogger(__name__)


class DialogState(Enum):
    """대화 상태 열거형"""
    INITIAL = "initial"           # 시작 상태
    ACTIVE = "active"            # 활성 대화 중
    WAITING = "waiting"          # 응답 대기 중
    TOPIC_SHIFT = "topic_shift"  # 주제 전환
    CLARIFYING = "clarifying"    # 명확화 중
    ENDING = "ending"            # 대화 종료 중
    EXPIRED = "expired"          # 세션 만료
    ERROR = "error"              # 오류 상태


@dataclass
class TopicInfo:
    """주제 정보"""
    name: str
    keywords: List[str]
    confidence: float
    start_turn: int
    last_mention_turn: int
    mention_count: int = 1


@dataclass
class DialogContext:
    """대화 컨텍스트"""
    session_id: str
    current_state: DialogState
    current_topics: List[TopicInfo]
    previous_state: Optional[DialogState] = None
    state_changed_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class TopicDetector:
    """주제 감지기"""
    
    def __init__(self):
        # 은행/금융 도메인 키워드 사전
        self.domain_keywords = {
            '대출': ['대출', '대여', '융자', '신용', '담보', '한도'],
            '예금': ['예금', '적금', '정기예금', '자유적금', '저축'],
            '카드': ['카드', '신용카드', '체크카드', '결제'],
            '계좌': ['계좌', '통장', '입금', '출금', '이체', '송금'],
            '투자': ['투자', '펀드', '주식', '채권', '투자상품'],
            '보험': ['보험', '생명보험', '손해보험', '연금보험'],
            '환율': ['환율', '외환', '달러', '엔화', '유로'],
            '수수료': ['수수료', '이자', '금리', '수수료율'],
            '인터넷뱅킹': ['인터넷뱅킹', '모바일뱅킹', '온라인'],
            '지점': ['지점', '영업점', 'ATM', '창구']
        }
        
        # 주제 전환 신호 키워드
        self.topic_shift_signals = [
            '그런데', '그러면', '다른', '또', '또한', '아니면',
            '바꿔서', '대신', '혹시', '그보다', '그리고'
        ]
    
    def detect_topics(self, text: str) -> List[TopicInfo]:
        """텍스트에서 주제 감지
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            List[TopicInfo]: 감지된 주제 리스트
        """
        detected_topics = []
        text_lower = text.lower()
        
        for topic_name, keywords in self.domain_keywords.items():
            matches = []
            for keyword in keywords:
                if keyword in text_lower:
                    matches.append(keyword)
            
            if matches:
                confidence = min(1.0, len(matches) / len(keywords) * 2)  # 최대 1.0
                
                topic_info = TopicInfo(
                    name=topic_name,
                    keywords=matches,
                    confidence=confidence,
                    start_turn=0,  # 호출자가 설정
                    last_mention_turn=0  # 호출자가 설정
                )
                detected_topics.append(topic_info)
        
        return detected_topics
    
    def calculate_topic_similarity(self, topic1: TopicInfo, topic2: TopicInfo) -> float:
        """두 주제 간 유사도 계산
        
        Args:
            topic1: 첫 번째 주제
            topic2: 두 번째 주제
            
        Returns:
            float: 유사도 (0.0 ~ 1.0)
        """
        if topic1.name == topic2.name:
            return 1.0
        
        keywords1 = set(topic1.keywords)
        keywords2 = set(topic2.keywords)
        
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        
        if union == 0:
            return 0.0
        
        jaccard_similarity = intersection / union
        
        # 도메인 지식 기반 유사도 보정
        related_topics = {
            '대출': ['예금', '계좌'],
            '예금': ['대출', '계좌'],
            '카드': ['계좌', '수수료'],
            '계좌': ['예금', '대출', '카드', '이체'],
            '투자': ['계좌', '수수료'],
            '보험': ['투자'],
            '환율': [],
            '수수료': ['카드', '투자', '계좌'],
            '인터넷뱅킹': ['계좌', '카드'],
            '지점': ['계좌', '카드']
        }
        
        if topic2.name in related_topics.get(topic1.name, []):
            jaccard_similarity += 0.2  # 관련 주제 보너스
        
        return min(1.0, jaccard_similarity)
    
    def detect_topic_shift(self, current_text: str, previous_topics: List[TopicInfo]) -> bool:
        """주제 전환 감지
        
        Args:
            current_text: 현재 텍스트
            previous_topics: 이전 주제들
            
        Returns:
            bool: 주제 전환 여부
        """
        # 주제 전환 신호어 확인
        text_lower = current_text.lower()
        has_shift_signals = any(
            signal in text_lower for signal in self.topic_shift_signals
        )
        
        if has_shift_signals:
            return True
        
        # 현재 텍스트의 주제 감지
        current_topics = self.detect_topics(current_text)
        
        if not current_topics or not previous_topics:
            return False
        
        # 주제 유사도 계산
        max_similarity = 0.0
        for current_topic in current_topics:
            for prev_topic in previous_topics:
                similarity = self.calculate_topic_similarity(current_topic, prev_topic)
                max_similarity = max(max_similarity, similarity)
        
        # 유사도가 낮으면 주제 전환으로 판단
        return max_similarity < 0.3


class DialogStateManager:
    """대화 상태 관리자"""
    
    def __init__(self):
        self.session_manager = get_session_manager()
        self.topic_detector = TopicDetector()
        self.active_contexts: Dict[str, DialogContext] = {}
        
        # 상태 전환 규칙
        self.state_transitions = {
            DialogState.INITIAL: [DialogState.ACTIVE, DialogState.ERROR],
            DialogState.ACTIVE: [DialogState.WAITING, DialogState.TOPIC_SHIFT, DialogState.CLARIFYING, DialogState.ENDING, DialogState.EXPIRED, DialogState.ERROR],
            DialogState.WAITING: [DialogState.ACTIVE, DialogState.EXPIRED, DialogState.ERROR],
            DialogState.TOPIC_SHIFT: [DialogState.ACTIVE, DialogState.ENDING, DialogState.ERROR],
            DialogState.CLARIFYING: [DialogState.ACTIVE, DialogState.ENDING, DialogState.ERROR],
            DialogState.ENDING: [DialogState.INITIAL, DialogState.ERROR],
            DialogState.EXPIRED: [DialogState.INITIAL],
            DialogState.ERROR: [DialogState.INITIAL, DialogState.ACTIVE]
        }
    
    def initialize_session_state(self, session_id: str) -> DialogContext:
        """세션 상태 초기화
        
        Args:
            session_id: 세션 ID
            
        Returns:
            DialogContext: 초기화된 대화 컨텍스트
        """
        context = DialogContext(
            session_id=session_id,
            current_state=DialogState.INITIAL,
            current_topics=[],
            state_changed_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.active_contexts[session_id] = context
        logger.info(f"Initialized dialog state for session {session_id}")
        
        return context
    
    def get_session_context(self, session_id: str) -> Optional[DialogContext]:
        """세션 컨텍스트 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            DialogContext: 대화 컨텍스트 또는 None
        """
        if session_id in self.active_contexts:
            return self.active_contexts[session_id]
        
        # 세션이 존재하는지 확인
        session = self.session_manager.get_session(session_id)
        if session:
            # 기존 세션에 대한 컨텍스트 복원
            return self._restore_session_context(session)
        
        return None
    
    def process_user_message(
        self, 
        session_id: str, 
        user_message: str,
        turn_number: int
    ) -> DialogContext:
        """사용자 메시지 처리 및 상태 업데이트
        
        Args:
            session_id: 세션 ID
            user_message: 사용자 메시지
            turn_number: 턴 번호
            
        Returns:
            DialogContext: 업데이트된 대화 컨텍스트
        """
        context = self.get_session_context(session_id)
        if not context:
            context = self.initialize_session_state(session_id)
        
        # 활동 시간 업데이트
        context.last_activity = datetime.now()
        
        # 주제 감지
        detected_topics = self.topic_detector.detect_topics(user_message)
        
        # 주제 전환 감지
        topic_shift_detected = False
        if context.current_topics and detected_topics:
            topic_shift_detected = self.topic_detector.detect_topic_shift(
                user_message, 
                context.current_topics
            )
        
        # 상태 전환 처리
        new_state = self._determine_new_state(
            context, 
            user_message, 
            detected_topics,
            topic_shift_detected
        )
        
        if new_state != context.current_state:
            self._transition_state(context, new_state)
        
        # 주제 업데이트
        self._update_topics(context, detected_topics, turn_number)
        
        # 세션 매니저에 주제 정보 동기화
        self._sync_topics_with_session(context)
        
        logger.debug(
            f"Processed message for session {session_id}: "
            f"state={context.current_state.value}, "
            f"topics={[t.name for t in context.current_topics]}"
        )
        
        return context
    
    def _determine_new_state(
        self,
        context: DialogContext,
        user_message: str,
        detected_topics: List[TopicInfo],
        topic_shift_detected: bool
    ) -> DialogState:
        """새로운 상태 결정
        
        Args:
            context: 현재 컨텍스트
            user_message: 사용자 메시지
            detected_topics: 감지된 주제들
            topic_shift_detected: 주제 전환 감지 여부
            
        Returns:
            DialogState: 새로운 상태
        """
        current_state = context.current_state
        message_lower = user_message.lower()
        
        # 종료 신호 확인
        end_signals = ['끝', '종료', '마침', '그만', '나가기', '종료해줘']
        if any(signal in message_lower for signal in end_signals):
            return DialogState.ENDING
        
        # 명확화 요청 확인
        clarification_signals = ['뭐야', '무슨', '설명해', '모르겠', '이해 안', '다시']
        if any(signal in message_lower for signal in clarification_signals):
            return DialogState.CLARIFYING
        
        # 주제 전환 감지
        if topic_shift_detected:
            return DialogState.TOPIC_SHIFT
        
        # 상태별 전환 로직
        if current_state == DialogState.INITIAL:
            if detected_topics:
                return DialogState.ACTIVE
        
        elif current_state == DialogState.WAITING:
            return DialogState.ACTIVE
        
        elif current_state in [DialogState.TOPIC_SHIFT, DialogState.CLARIFYING]:
            return DialogState.ACTIVE
        
        return current_state
    
    def _transition_state(self, context: DialogContext, new_state: DialogState):
        """상태 전환 실행
        
        Args:
            context: 대화 컨텍스트
            new_state: 새로운 상태
        """
        # 전환 규칙 확인
        if new_state not in self.state_transitions.get(context.current_state, []):
            logger.warning(
                f"Invalid state transition: {context.current_state.value} -> {new_state.value}"
            )
            return
        
        old_state = context.current_state
        context.previous_state = old_state
        context.current_state = new_state
        context.state_changed_at = datetime.now()
        
        logger.info(
            f"State transition for session {context.session_id}: "
            f"{old_state.value} -> {new_state.value}"
        )
        
        # 상태별 후처리
        self._handle_state_change(context, old_state, new_state)
    
    def _handle_state_change(
        self, 
        context: DialogContext, 
        old_state: DialogState, 
        new_state: DialogState
    ):
        """상태 변경 후처리
        
        Args:
            context: 대화 컨텍스트
            old_state: 이전 상태
            new_state: 새로운 상태
        """
        if new_state == DialogState.ENDING:
            # 대화 종료 처리
            self.session_manager.complete_session(
                context.session_id, 
                "User requested to end conversation"
            )
            
        elif new_state == DialogState.TOPIC_SHIFT:
            # 이전 주제들을 비활성화
            for topic in context.current_topics:
                # 세션 매니저를 통해 주제 종료 처리
                pass  # 구현 필요시 추가
        
        elif new_state == DialogState.EXPIRED:
            # 세션 만료 처리
            if context.session_id in self.active_contexts:
                del self.active_contexts[context.session_id]
    
    def _update_topics(
        self, 
        context: DialogContext, 
        detected_topics: List[TopicInfo],
        turn_number: int
    ):
        """주제 정보 업데이트
        
        Args:
            context: 대화 컨텍스트
            detected_topics: 새로 감지된 주제들
            turn_number: 현재 턴 번호
        """
        # 기존 주제 업데이트
        for topic in context.current_topics:
            # 현재 턴에서 언급되었는지 확인
            mentioned = any(
                dt.name == topic.name for dt in detected_topics
            )
            
            if mentioned:
                topic.last_mention_turn = turn_number
                topic.mention_count += 1
                # 감지된 주제에서 키워드 업데이트
                for dt in detected_topics:
                    if dt.name == topic.name:
                        # 새로운 키워드 추가
                        new_keywords = set(dt.keywords) - set(topic.keywords)
                        topic.keywords.extend(list(new_keywords))
                        topic.confidence = max(topic.confidence, dt.confidence)
                        break
        
        # 새로운 주제 추가
        existing_topic_names = {topic.name for topic in context.current_topics}
        
        for detected_topic in detected_topics:
            if detected_topic.name not in existing_topic_names:
                detected_topic.start_turn = turn_number
                detected_topic.last_mention_turn = turn_number
                context.current_topics.append(detected_topic)
        
        # 오래된 주제 정리 (5턴 이상 언급되지 않은 주제)
        context.current_topics = [
            topic for topic in context.current_topics
            if turn_number - topic.last_mention_turn <= 5
        ]
    
    def _sync_topics_with_session(self, context: DialogContext):
        """세션 매니저와 주제 정보 동기화
        
        Args:
            context: 대화 컨텍스트
        """
        if context.current_topics:
            current_topic_names = [topic.name for topic in context.current_topics]
            primary_topic = context.current_topics[0].name  # 가장 최근 주제
            
            self.session_manager.update_session_context(
                context.session_id,
                current_topic=primary_topic
            )
    
    def _restore_session_context(self, session: ConversationSession) -> DialogContext:
        """세션으로부터 컨텍스트 복원
        
        Args:
            session: 대화 세션
            
        Returns:
            DialogContext: 복원된 컨텍스트
        """
        # 세션 상태에 따른 다이얼로그 상태 매핑
        state_mapping = {
            'active': DialogState.ACTIVE,
            'completed': DialogState.ENDING,
            'expired': DialogState.EXPIRED
        }
        
        dialog_state = state_mapping.get(session.status, DialogState.ACTIVE)
        
        # 주제 정보 복원
        topics = []
        session_topics = self.session_manager.get_session_topics(session.session_id)
        
        for session_topic in session_topics:
            if session_topic.is_active:
                topic_info = TopicInfo(
                    name=session_topic.topic_name,
                    keywords=session_topic.topic_keywords,
                    confidence=session_topic.confidence,
                    start_turn=session_topic.start_turn,
                    last_mention_turn=session_topic.end_turn or session_topic.start_turn
                )
                topics.append(topic_info)
        
        context = DialogContext(
            session_id=session.session_id,
            current_state=dialog_state,
            current_topics=topics,
            last_activity=session.updated_at
        )
        
        self.active_contexts[session.session_id] = context
        
        logger.info(f"Restored dialog context for session {session.session_id}")
        return context
    
    def check_session_timeouts(self, timeout_minutes: int = 30):
        """세션 타임아웃 확인 및 처리
        
        Args:
            timeout_minutes: 타임아웃 시간 (분)
        """
        current_time = datetime.now()
        timeout_threshold = current_time - timedelta(minutes=timeout_minutes)
        
        expired_sessions = []
        
        for session_id, context in self.active_contexts.items():
            if (context.last_activity and 
                context.last_activity < timeout_threshold and
                context.current_state not in [DialogState.ENDING, DialogState.EXPIRED]):
                
                expired_sessions.append(session_id)
        
        # 만료된 세션 처리
        for session_id in expired_sessions:
            context = self.active_contexts[session_id]
            self._transition_state(context, DialogState.EXPIRED)
            
            logger.info(f"Session {session_id} expired due to inactivity")
    
    def reset_session_state(self, session_id: str):
        """세션 상태 초기화
        
        Args:
            session_id: 세션 ID
        """
        if session_id in self.active_contexts:
            context = self.active_contexts[session_id]
            context.current_state = DialogState.INITIAL
            context.current_topics.clear()
            context.state_changed_at = datetime.now()
            context.last_activity = datetime.now()
            
            logger.info(f"Reset dialog state for session {session_id}")
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """세션 상태 요약 정보 반환
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Dict[str, Any]: 상태 요약
        """
        context = self.get_session_context(session_id)
        if not context:
            return {"error": "Session not found"}
        
        return {
            "session_id": session_id,
            "current_state": context.current_state.value,
            "previous_state": context.previous_state.value if context.previous_state else None,
            "active_topics": [
                {
                    "name": topic.name,
                    "keywords": topic.keywords,
                    "confidence": topic.confidence,
                    "mention_count": topic.mention_count
                }
                for topic in context.current_topics
            ],
            "last_activity": context.last_activity.isoformat() if context.last_activity else None,
            "state_changed_at": context.state_changed_at.isoformat() if context.state_changed_at else None
        }


# 전역 인스턴스
_dialog_state_manager = None

def get_dialog_state_manager() -> DialogStateManager:
    """대화 상태 매니저 싱글톤 인스턴스 반환"""
    global _dialog_state_manager
    if _dialog_state_manager is None:
        _dialog_state_manager = DialogStateManager()
    return _dialog_state_manager