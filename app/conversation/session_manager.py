#!/usr/bin/env python3
"""
대화 세션 매니저
멀티턴 대화의 세션 생성, 관리, 종료 및 컨텍스트 추적 담당
"""

import json
import uuid
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Tuple
import logging

from app.core.database import get_db_manager
from app.conversation.summary_agent import get_conversation_summarizer

logger = logging.getLogger(__name__)


@dataclass
class ConversationSession:
    """대화 세션 데이터 클래스"""
    session_id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    status: str = 'active'
    context_summary: Optional[str] = None
    current_topic: Optional[str] = None
    turn_count: int = 0
    max_turns: int = 5
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConversationTurn:
    """대화 턴 데이터 클래스"""
    session_id: str
    turn_number: int
    user_message: str
    assistant_message: Optional[str] = None
    search_query: Optional[str] = None
    search_results: Optional[List[Dict[str, Any]]] = None
    context_used: Optional[str] = None
    response_time_ms: Optional[int] = None
    confidence_score: Optional[float] = None
    feedback_rating: Optional[int] = None
    feedback_comment: Optional[str] = None
    created_at: Optional[datetime] = None
    id: Optional[int] = None


@dataclass
class ConversationTopic:
    """대화 주제 데이터 클래스"""
    session_id: str
    topic_name: str
    topic_keywords: List[str]
    start_turn: int
    end_turn: Optional[int] = None
    confidence: float = 1.0
    is_active: bool = True
    created_at: Optional[datetime] = None
    id: Optional[int] = None


class ConversationSessionManager:
    """대화 세션 관리자"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self._ensure_conversation_schema()
    
    def _ensure_conversation_schema(self):
        """대화 스키마가 존재하는지 확인하고 필요시 생성"""
        try:
            from app.core.conversation_schema import apply_conversation_migration
            apply_conversation_migration(self.db_manager)
        except Exception as e:
            logger.error(f"Failed to apply conversation schema: {e}")
            raise
    
    def create_session(
        self, 
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        max_turns: int = 5,
        session_duration_hours: int = 24,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationSession:
        """새 대화 세션 생성
        
        Args:
            user_id: 사용자 ID (선택적)
            title: 세션 제목 (선택적)
            max_turns: 최대 턴 수 (기본값: 5)
            session_duration_hours: 세션 유지 시간 (기본값: 24시간)
            metadata: 추가 메타데이터
            
        Returns:
            ConversationSession: 생성된 세션 객체
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(hours=session_duration_hours)
        
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            title=title or f"대화 {now.strftime('%Y-%m-%d %H:%M')}",
            status='active',
            max_turns=max_turns,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            metadata=metadata
        )
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conversation_sessions 
                (session_id, user_id, title, status, current_topic, turn_count, max_turns, 
                 created_at, updated_at, expires_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id, session.user_id, session.title, session.status,
                session.current_topic, session.turn_count, session.max_turns,
                session.created_at, session.updated_at, session.expires_at,
                json.dumps(session.metadata) if session.metadata else None
            ))
            
            conn.commit()
        
        logger.info(f"Created conversation session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """세션 정보 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            ConversationSession: 세션 객체 또는 None
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id, user_id, title, status, context_summary, current_topic,
                       turn_count, max_turns, created_at, updated_at, expires_at, metadata_json
                FROM conversation_sessions
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 만료 확인
            if row[10] and datetime.fromisoformat(row[10]) < datetime.now():
                self._expire_session(session_id)
                return None
            
            metadata = json.loads(row[11]) if row[11] else None
            
            return ConversationSession(
                session_id=row[0],
                user_id=row[1],
                title=row[2],
                status=row[3],
                context_summary=row[4],
                current_topic=row[5],
                turn_count=row[6],
                max_turns=row[7],
                created_at=datetime.fromisoformat(row[8]) if row[8] else None,
                updated_at=datetime.fromisoformat(row[9]) if row[9] else None,
                expires_at=datetime.fromisoformat(row[10]) if row[10] else None,
                metadata=metadata
            )
    
    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: Optional[str] = None,
        search_query: Optional[str] = None,
        search_results: Optional[List[Dict[str, Any]]] = None,
        context_used: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        confidence_score: Optional[float] = None
    ) -> ConversationTurn:
        """대화 턴 추가
        
        Args:
            session_id: 세션 ID
            user_message: 사용자 메시지
            assistant_message: 어시스턴트 응답
            search_query: 사용된 검색 쿼리
            search_results: 검색 결과
            context_used: 사용된 컨텍스트
            response_time_ms: 응답 시간 (밀리초)
            confidence_score: 신뢰도 점수
            
        Returns:
            ConversationTurn: 생성된 턴 객체
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        if session.status != 'active':
            raise ValueError(f"Session is not active: {session_id}")
        
        turn_number = session.turn_count + 1
        
        # 최대 턴 수 확인
        if turn_number > session.max_turns:
            self._complete_session(session_id, "Maximum turns reached")
            raise ValueError(f"Session has reached maximum turns: {session.max_turns}")
        
        turn = ConversationTurn(
            session_id=session_id,
            turn_number=turn_number,
            user_message=user_message,
            assistant_message=assistant_message,
            search_query=search_query,
            search_results=search_results,
            context_used=context_used,
            response_time_ms=response_time_ms,
            confidence_score=confidence_score,
            created_at=datetime.now()
        )
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conversation_turns
                (session_id, turn_number, user_message, assistant_message, search_query,
                 search_results_json, context_used, response_time_ms, confidence_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                turn.session_id, turn.turn_number, turn.user_message, turn.assistant_message,
                turn.search_query, json.dumps(turn.search_results) if turn.search_results else None,
                turn.context_used, turn.response_time_ms, turn.confidence_score, turn.created_at
            ))
            
            turn.id = cursor.lastrowid
            conn.commit()

        logger.info(f"Added turn {turn_number} to session {session_id}")

        # Update session summary after each turn
        try:
            summarizer = get_conversation_summarizer()
            summarizer.session_manager = self
            summary = summarizer.summarize_sync(session_id)
            if summary:
                self.update_session_context(session_id, context_summary=summary)
        except Exception as e:
            logger.error(f"Failed to update session summary: {e}")
        return turn
    
    def get_session_turns(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[ConversationTurn]:
        """세션의 모든 턴 조회
        
        Args:
            session_id: 세션 ID
            limit: 최대 조회 개수 (최신순)
            
        Returns:
            List[ConversationTurn]: 턴 리스트
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            sql = """
                SELECT id, session_id, turn_number, user_message, assistant_message,
                       search_query, search_results_json, context_used, response_time_ms,
                       confidence_score, feedback_rating, feedback_comment, created_at
                FROM conversation_turns
                WHERE session_id = ?
                ORDER BY turn_number DESC
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor.execute(sql, (session_id,))
            rows = cursor.fetchall()
            
            turns = []
            for row in rows:
                search_results = json.loads(row[6]) if row[6] else None
                
                turn = ConversationTurn(
                    id=row[0],
                    session_id=row[1],
                    turn_number=row[2],
                    user_message=row[3],
                    assistant_message=row[4],
                    search_query=row[5],
                    search_results=search_results,
                    context_used=row[7],
                    response_time_ms=row[8],
                    confidence_score=row[9],
                    feedback_rating=row[10],
                    feedback_comment=row[11],
                    created_at=datetime.fromisoformat(row[12]) if row[12] else None
                )
                turns.append(turn)
            
            # 시간순 정렬로 되돌리기
            turns.reverse()
            return turns
    
    def update_session_context(
        self,
        session_id: str,
        context_summary: Optional[str] = None,
        current_topic: Optional[str] = None
    ):
        """세션 컨텍스트 업데이트
        
        Args:
            session_id: 세션 ID
            context_summary: 컨텍스트 요약
            current_topic: 현재 주제
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE conversation_sessions
                SET context_summary = COALESCE(?, context_summary),
                    current_topic = COALESCE(?, current_topic),
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (context_summary, current_topic, session_id))
            
            conn.commit()
        
        logger.debug(f"Updated context for session {session_id}")
    
    def add_topic(
        self,
        session_id: str,
        topic_name: str,
        topic_keywords: List[str],
        start_turn: int,
        confidence: float = 1.0
    ) -> ConversationTopic:
        """대화 주제 추가
        
        Args:
            session_id: 세션 ID
            topic_name: 주제 이름
            topic_keywords: 주제 키워드
            start_turn: 시작 턴 번호
            confidence: 신뢰도
            
        Returns:
            ConversationTopic: 생성된 주제 객체
        """
        topic = ConversationTopic(
            session_id=session_id,
            topic_name=topic_name,
            topic_keywords=topic_keywords,
            start_turn=start_turn,
            confidence=confidence,
            created_at=datetime.now()
        )
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conversation_topics
                (session_id, topic_name, topic_keywords, start_turn, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                topic.session_id, topic.topic_name, ','.join(topic.topic_keywords),
                topic.start_turn, topic.confidence, topic.created_at
            ))
            
            topic.id = cursor.lastrowid
            conn.commit()
        
        # 세션의 현재 주제 업데이트
        self.update_session_context(session_id, current_topic=topic_name)
        
        logger.info(f"Added topic '{topic_name}' to session {session_id}")
        return topic
    
    def get_session_topics(self, session_id: str) -> List[ConversationTopic]:
        """세션의 모든 주제 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            List[ConversationTopic]: 주제 리스트
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, session_id, topic_name, topic_keywords, start_turn, end_turn,
                       confidence, is_active, created_at
                FROM conversation_topics
                WHERE session_id = ?
                ORDER BY start_turn ASC
            """, (session_id,))
            
            rows = cursor.fetchall()
            
            topics = []
            for row in rows:
                topic = ConversationTopic(
                    id=row[0],
                    session_id=row[1],
                    topic_name=row[2],
                    topic_keywords=row[3].split(',') if row[3] else [],
                    start_turn=row[4],
                    end_turn=row[5],
                    confidence=row[6],
                    is_active=bool(row[7]),
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None
                )
                topics.append(topic)
            
            return topics
    
    def extend_session(self, session_id: str, additional_hours: int = 24):
        """세션 만료 시간 연장
        
        Args:
            session_id: 세션 ID
            additional_hours: 연장할 시간 (시간)
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE conversation_sessions
                SET expires_at = datetime(expires_at, '+{} hours'),
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """.format(additional_hours), (session_id,))
            
            conn.commit()
        
        logger.info(f"Extended session {session_id} by {additional_hours} hours")
    
    def complete_session(self, session_id: str, reason: str = "User completed"):
        """세션 완료 처리
        
        Args:
            session_id: 세션 ID
            reason: 완료 사유
        """
        self._complete_session(session_id, reason)
    
    def _complete_session(self, session_id: str, reason: str):
        """내부 세션 완료 처리"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE conversation_sessions
                SET status = 'completed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))
            
            # 활성 주제 종료
            cursor.execute("""
                UPDATE conversation_topics
                SET is_active = FALSE,
                    end_turn = (
                        SELECT MAX(turn_number) 
                        FROM conversation_turns 
                        WHERE session_id = ?
                    )
                WHERE session_id = ? AND is_active = TRUE
            """, (session_id, session_id))
            
            conn.commit()
        
        logger.info(f"Completed session {session_id}: {reason}")
    
    def _expire_session(self, session_id: str):
        """세션 만료 처리"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE conversation_sessions
                SET status = 'expired',
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))
            
            conn.commit()
        
        logger.info(f"Expired session {session_id}")
    
    def get_active_sessions(
        self, 
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[ConversationSession]:
        """활성 세션 목록 조회
        
        Args:
            user_id: 특정 사용자의 세션만 조회 (선택적)
            limit: 최대 조회 개수
            
        Returns:
            List[ConversationSession]: 활성 세션 리스트
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            sql = """
                SELECT session_id, user_id, title, status, context_summary, current_topic,
                       turn_count, max_turns, created_at, updated_at, expires_at, metadata_json
                FROM conversation_sessions
                WHERE status = 'active' AND expires_at > CURRENT_TIMESTAMP
            """
            params = []
            
            if user_id:
                sql += " AND user_id = ?"
                params.append(user_id)
            
            sql += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            sessions = []
            for row in rows:
                metadata = json.loads(row[11]) if row[11] else None
                
                session = ConversationSession(
                    session_id=row[0],
                    user_id=row[1],
                    title=row[2],
                    status=row[3],
                    context_summary=row[4],
                    current_topic=row[5],
                    turn_count=row[6],
                    max_turns=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None,
                    updated_at=datetime.fromisoformat(row[9]) if row[9] else None,
                    expires_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    metadata=metadata
                )
                sessions.append(session)
            
            return sessions
    
    def cleanup_expired_sessions(self, days_old: int = 7) -> int:
        """만료된 세션 정리
        
        Args:
            days_old: 삭제할 세션의 나이 (일)
            
        Returns:
            int: 삭제된 세션 수
        """
        from app.core.conversation_schema import ConversationSchema
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            deleted_count = ConversationSchema.cleanup_expired_conversations(cursor, days_old)
            conn.commit()
            
            return deleted_count

    def update_turn_feedback(
        self,
        session_id: str,
        turn_number: int,
        rating: int,
        comment: Optional[str] = None
    ):
        """턴별 피드백 업데이트
        
        Args:
            session_id: 세션 ID
            turn_number: 턴 번호
            rating: 피드백 별점 (1-5)
            comment: 피드백 코멘트 (선택적)
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE conversation_turns
                SET feedback_rating = ?,
                    feedback_comment = ?,
                    created_at = CURRENT_TIMESTAMP -- 또는 updated_at 컬럼 추가
                WHERE session_id = ? AND turn_number = ?
            """, (rating, comment, session_id, turn_number))
            
            conn.commit()
        
        logger.info(f"Updated feedback for session {session_id}, turn {turn_number}")


# 전역 인스턴스
_session_manager = None

def get_session_manager() -> ConversationSessionManager:
    """세션 매니저 싱글톤 인스턴스 반환"""
    global _session_manager
    if _session_manager is None:
        _session_manager = ConversationSessionManager()
    return _session_manager