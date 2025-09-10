#!/usr/bin/env python3
"""
대화 시스템 API
멀티턴 대화, 세션 관리, 컨텍스트 인식 검색을 위한 REST API
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
import logging

from app.conversation.session_manager import (
    get_session_manager, 
    ConversationSession, 
    ConversationTurn
)
from app.conversation.context_search import (
    get_context_search_engine,
    SearchContext,
    ContextualSearchResult
)
from app.conversation.dialog_state import (
    get_dialog_state_manager,
    DialogState,
    DialogContext
)

logger = logging.getLogger(__name__)

# API 라우터 생성
conversation_router = APIRouter(prefix="/conversation")


# Pydantic 모델 정의
class CreateSessionRequest(BaseModel):
    """세션 생성 요청"""
    user_id: Optional[str] = None
    title: Optional[str] = None
    max_turns: int = Field(default=5, ge=1, le=20)
    session_duration_hours: int = Field(default=24, ge=1, le=168)  # 최대 7일
    metadata: Optional[Dict[str, Any]] = None


class CreateSessionResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str
    title: str
    max_turns: int
    expires_at: datetime
    created_at: datetime


class SendMessageRequest(BaseModel):
    """메시지 전송 요청"""
    message: str = Field(..., min_length=1, max_length=2000)
    search_engine_type: str = Field(default="hybrid")  # hybrid, vector, ir
    include_context: bool = Field(default=True)
    max_context_turns: int = Field(default=3, ge=1, le=5)


class SendMessageResponse(BaseModel):
    """메시지 전송 응답"""
    session_id: str
    turn_number: int
    user_message: str
    assistant_message: str
    search_context: Optional[Dict[str, Any]] = None
    context_explanation: str = ""
    response_time_ms: int
    confidence_score: Optional[float] = None
    dialog_state: str
    current_topics: List[str] = []


class SessionInfoResponse(BaseModel):
    """세션 정보 응답"""
    session_id: str
    user_id: Optional[str]
    title: str
    status: str
    current_topic: Optional[str]
    turn_count: int
    max_turns: int
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    dialog_state: str
    active_topics: List[Dict[str, Any]] = []


class ConversationHistoryResponse(BaseModel):
    """대화 기록 응답"""
    session_id: str
    turns: List[Dict[str, Any]]
    total_turns: int


class SessionListResponse(BaseModel):
    """세션 목록 응답"""
    sessions: List[SessionInfoResponse]
    total_count: int


# API 엔드포인트 구현
@conversation_router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """새 대화 세션 생성"""
    try:
        session_manager = get_session_manager()
        dialog_manager = get_dialog_state_manager()
        
        # 세션 생성
        session = session_manager.create_session(
            user_id=request.user_id,
            title=request.title,
            max_turns=request.max_turns,
            session_duration_hours=request.session_duration_hours,
            metadata=request.metadata
        )
        
        # 대화 상태 초기화
        dialog_manager.initialize_session_state(session.session_id)
        
        return CreateSessionResponse(
            session_id=session.session_id,
            title=session.title,
            max_turns=session.max_turns,
            expires_at=session.expires_at,
            created_at=session.created_at
        )
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@conversation_router.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    """세션 정보 조회"""
    try:
        session_manager = get_session_manager()
        dialog_manager = get_dialog_state_manager()
        
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        dialog_context = dialog_manager.get_session_context(session_id)
        dialog_state = dialog_context.current_state.value if dialog_context else "unknown"
        
        # 활성 주제 정보
        active_topics = []
        if dialog_context and dialog_context.current_topics:
            active_topics = [
                {
                    "name": topic.name,
                    "keywords": topic.keywords,
                    "confidence": topic.confidence,
                    "mention_count": topic.mention_count
                }
                for topic in dialog_context.current_topics
            ]
        
        return SessionInfoResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            title=session.title,
            status=session.status,
            current_topic=session.current_topic,
            turn_count=session.turn_count,
            max_turns=session.max_turns,
            created_at=session.created_at,
            updated_at=session.updated_at,
            expires_at=session.expires_at,
            dialog_state=dialog_state,
            active_topics=active_topics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@conversation_router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """메시지 전송 및 응답 생성"""
    start_time = datetime.now()
    
    try:
        session_manager = get_session_manager()
        dialog_manager = get_dialog_state_manager()
        context_search = get_context_search_engine()
        
        # 세션 확인
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.status != 'active':
            raise HTTPException(status_code=400, detail=f"Session is {session.status}")
        
        # 대화 상태 업데이트
        turn_number = session.turn_count + 1
        dialog_context = dialog_manager.process_user_message(
            session_id, 
            request.message,
            turn_number
        )
        
        # 컨텍스트 인식 검색 수행 (실제 검색 엔진 연동 필요)
        search_results = []
        context_explanation = ""
        search_context_dict = None
        
        if request.include_context:
            try:
                # 여기서 실제 검색 엔진을 연동해야 함
                # 현재는 모의 구현
                search_context = context_search.enhance_query_with_context(
                    session_id,
                    request.message,
                    request.max_context_turns
                )
                
                search_context_dict = {
                    "original_query": search_context.original_query,
                    "enhanced_query": search_context.enhanced_query,
                    "reference_type": search_context.reference_type,
                    "confidence": search_context.confidence,
                    "previous_queries": search_context.previous_queries,
                    "mentioned_entities": search_context.mentioned_entities,
                    "current_topics": search_context.current_topics
                }
                
                context_explanation = f"컨텍스트를 고려하여 검색을 수행했습니다. (참조 타입: {search_context.reference_type})"
                
                # 실제 검색은 여기서 수행되어야 함
                # search_results = actual_search_engine.search(search_context.enhanced_query)
                
            except Exception as e:
                logger.warning(f"Context search failed, using fallback: {e}")
                context_explanation = "기본 검색을 수행했습니다."
        
        # 모의 응답 생성 (실제로는 LLM 서비스 호출)
        assistant_message = await _generate_assistant_response(
            request.message, 
            search_results, 
            dialog_context,
            search_context_dict
        )
        
        # 응답 시간 계산
        response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # 대화 턴 저장
        turn = session_manager.add_turn(
            session_id=session_id,
            user_message=request.message,
            assistant_message=assistant_message,
            search_query=search_context_dict.get("enhanced_query") if search_context_dict else request.message,
            search_results=search_results,
            context_used=context_explanation,
            response_time_ms=response_time_ms,
            confidence_score=search_context_dict.get("confidence") if search_context_dict else None
        )
        
        # 현재 주제 목록
        current_topics = [topic.name for topic in dialog_context.current_topics]
        
        return SendMessageResponse(
            session_id=session_id,
            turn_number=turn.turn_number,
            user_message=request.message,
            assistant_message=assistant_message,
            search_context=search_context_dict,
            context_explanation=context_explanation,
            response_time_ms=response_time_ms,
            confidence_score=search_context_dict.get("confidence") if search_context_dict else None,
            dialog_state=dialog_context.current_state.value,
            current_topics=current_topics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@conversation_router.get("/sessions/{session_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str, 
    limit: Optional[int] = None,
    offset: int = 0
):
    """대화 기록 조회"""
    try:
        session_manager = get_session_manager()
        
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        turns = session_manager.get_session_turns(session_id, limit)
        
        # offset 적용
        if offset > 0:
            turns = turns[offset:]
        
        turn_data = []
        for turn in turns:
            turn_info = {
                "turn_number": turn.turn_number,
                "user_message": turn.user_message,
                "assistant_message": turn.assistant_message,
                "search_query": turn.search_query,
                "context_used": turn.context_used,
                "response_time_ms": turn.response_time_ms,
                "confidence_score": turn.confidence_score,
                "created_at": turn.created_at.isoformat() if turn.created_at else None,
                "feedback_rating": turn.feedback_rating,
                "feedback_comment": turn.feedback_comment
            }
            turn_data.append(turn_info)
        
        return ConversationHistoryResponse(
            session_id=session_id,
            turns=turn_data,
            total_turns=len(turn_data)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@conversation_router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
):
    """세션 목록 조회"""
    try:
        session_manager = get_session_manager()
        dialog_manager = get_dialog_state_manager()
        
        # 활성 세션 조회
        sessions = session_manager.get_active_sessions(user_id, limit + offset)
        
        # 상태 필터링
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        # offset 적용
        if offset > 0:
            sessions = sessions[offset:]
        
        # limit 적용
        sessions = sessions[:limit]
        
        session_infos = []
        for session in sessions:
            dialog_context = dialog_manager.get_session_context(session.session_id)
            dialog_state = dialog_context.current_state.value if dialog_context else "unknown"
            
            # 활성 주제 정보
            active_topics = []
            if dialog_context and dialog_context.current_topics:
                active_topics = [
                    {
                        "name": topic.name,
                        "keywords": topic.keywords,
                        "confidence": topic.confidence
                    }
                    for topic in dialog_context.current_topics
                ]
            
            session_info = SessionInfoResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                title=session.title,
                status=session.status,
                current_topic=session.current_topic,
                turn_count=session.turn_count,
                max_turns=session.max_turns,
                created_at=session.created_at,
                updated_at=session.updated_at,
                expires_at=session.expires_at,
                dialog_state=dialog_state,
                active_topics=active_topics
            )
            session_infos.append(session_info)
        
        return SessionListResponse(
            sessions=session_infos,
            total_count=len(session_infos)
        )
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@conversation_router.post("/sessions/{session_id}/complete")
async def complete_session(session_id: str):
    """세션 완료 처리"""
    try:
        session_manager = get_session_manager()
        dialog_manager = get_dialog_state_manager()
        
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 세션 완료
        session_manager.complete_session(session_id, "Manually completed")
        
        # 대화 상태 업데이트
        dialog_context = dialog_manager.get_session_context(session_id)
        if dialog_context:
            dialog_context.current_state = DialogState.ENDING
        
        return {"message": "Session completed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@conversation_router.post("/sessions/{session_id}/extend")
async def extend_session(session_id: str, additional_hours: int = 24):
    """세션 만료 시간 연장"""
    try:
        session_manager = get_session_manager()
        
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.status != 'active':
            raise HTTPException(status_code=400, detail="Cannot extend inactive session")
        
        session_manager.extend_session(session_id, additional_hours)
        
        return {"message": f"Session extended by {additional_hours} hours"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extend session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@conversation_router.post("/sessions/{session_id}/feedback")
async def submit_feedback(
    session_id: str,
    turn_number: int = Query(...),
    rating: int = Query(..., ge=1, le=5),
    comment: Optional[str] = Query(None)
):
    """턴별 피드백 제출"""
    try:
        session_manager = get_session_manager()
        
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 피드백 업데이트 (실제 구현 필요)
        session_manager.update_turn_feedback(session_id, turn_number, rating, comment)
        
        return {"message": "Feedback submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@conversation_router.get("/sessions/{session_id}/state")
async def get_dialog_state(session_id: str):
    """대화 상태 조회"""
    try:
        dialog_manager = get_dialog_state_manager()
        
        state_summary = dialog_manager.get_session_summary(session_id)
        if "error" in state_summary:
            raise HTTPException(status_code=404, detail=state_summary["error"])
        
        return state_summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dialog state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@conversation_router.post("/maintenance/cleanup")
async def cleanup_expired_sessions(
    background_tasks: BackgroundTasks,
    days_old: int = 7
):
    """만료된 세션 정리 (백그라운드 작업)"""
    try:
        def cleanup_task():
            session_manager = get_session_manager()
            dialog_manager = get_dialog_state_manager()
            
            # 만료된 세션 정리
            deleted_count = session_manager.cleanup_expired_sessions(days_old)
            
            # 타임아웃된 대화 상태 정리
            dialog_manager.check_session_timeouts(timeout_minutes=30)
            
            logger.info(f"Cleanup completed: {deleted_count} sessions deleted")
        
        background_tasks.add_task(cleanup_task)
        
        return {"message": "Cleanup task scheduled"}
        
    except Exception as e:
        logger.error(f"Failed to schedule cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper 함수
async def _generate_assistant_response(
    user_message: str,
    search_results: List[Dict[str, Any]],
    dialog_context: DialogContext,
    search_context: Optional[Dict[str, Any]] = None
) -> str:
    """어시스턴트 응답 생성 (모의 구현)
    
    실제로는 LLM 서비스 호출이 필요
    """
    # 모의 응답 생성
    response_templates = {
        DialogState.INITIAL: "안녕하세요! 무엇을 도와드릴까요?",
        DialogState.ACTIVE: f"'{user_message}'에 대해 설명드리겠습니다.",
        DialogState.CLARIFYING: f"'{user_message}'에 대해 더 자세히 설명해드리겠습니다.",
        DialogState.TOPIC_SHIFT: f"새로운 주제 '{user_message}'에 대해 알아보겠습니다.",
        DialogState.ENDING: "대화를 마치겠습니다. 감사합니다!"
    }
    
    base_response = response_templates.get(
        dialog_context.current_state,
        f"'{user_message}'에 대한 정보를 찾아보겠습니다."
    )
    
    # 컨텍스트 정보 추가
    if search_context and search_context.get("reference_type") == "follow_up":
        base_response += " (이전 질문의 연관된 내용입니다)"
    elif search_context and search_context.get("reference_type") == "clarification":
        base_response += " (이전 답변에 대한 추가 설명입니다)"
    
    # 현재 주제 언급
    if dialog_context.current_topics:
        topic_names = [topic.name for topic in dialog_context.current_topics]
        base_response += f"\n\n현재 대화 주제: {', '.join(topic_names)}"
    
    return base_response