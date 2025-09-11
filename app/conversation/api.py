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
from app.llm.ollama_client import get_ollama_client
from app.llm.chat_mode_client import get_chat_mode_client
from app.conversation.search_decision_agent import SearchDecisionAgent

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
    chat_mode: str = Field(default="quick")  # quick, precise, summary


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


class PreloadRequest(BaseModel):
    """모드 사전 로드 요청"""
    mode: str = Field(default="quick")  # quick, precise, summary

class PreloadResponse(BaseModel):
    """모드 사전 로드 응답"""
    mode: str
    model: str
    success: bool
    keep_alive: str


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
        
        # SearchDecisionAgent로 의도 분류
        search_results = []
        context_explanation = ""
        search_context_dict = None
        
        if request.include_context:
            try:
                # 이전 대화 맥락 구성
                recent_turns = session_manager.get_session_turns(session_id, limit=2)
                conversation_context = ""
                if recent_turns:
                    context_messages = []
                    for turn in recent_turns[-2:]:  # 최근 2턴만
                        context_messages.extend([
                            f"사용자: {turn.user_message}",
                            f"도우미: {turn.assistant_message}"
                        ])
                    conversation_context = "\n".join(context_messages[-4:])

                # SearchDecisionAgent로 의도 분류
                search_decision_agent = SearchDecisionAgent()
                decision_result = await search_decision_agent.should_search(
                    request.message, 
                    conversation_context if conversation_context else None
                )

                search_context_dict = {
                    "original_query": request.message,
                    "enhanced_query": request.message,
                    "reference_type": "info_request" if decision_result["requires_search"] else "small_talk",
                    "confidence": decision_result["confidence"],
                    "intent": decision_result["intent_type"],
                    "requires_search": decision_result["requires_search"],
                    "reasoning": decision_result["reasoning"],
                    "decision_method": "SearchDecisionAgent"
                }

                if not decision_result["requires_search"]:
                    context_explanation = f"일상 대화로 판단되어 검색을 생략했습니다. (신뢰도: {decision_result['confidence']:.2f})"
                else:
                    context_explanation = f"정보 요청으로 판단하여 검색을 수행합니다. (신뢰도: {decision_result['confidence']:.2f})"
                    # 실제 검색은 여기서 수행되어야 함
                    # search_results = actual_search_engine.search(request.message)

                logger.info(f"SearchDecisionAgent 결과 - 질문: '{request.message}', 분류: {decision_result['intent_type']}, 검색필요: {decision_result['requires_search']}, 신뢰도: {decision_result['confidence']:.2f}")

            except Exception as e:
                logger.error(f"SearchDecisionAgent failed: {e}")
                # 폴백: 기본적으로 일상 대화로 처리
                search_context_dict = {
                    "original_query": request.message,
                    "enhanced_query": request.message,
                    "reference_type": "small_talk",
                    "confidence": 0.5,
                    "intent": "small_talk", 
                    "requires_search": False,
                    "reasoning": "에이전트 오류로 인한 기본값",
                    "decision_method": "fallback"
                }
                context_explanation = "의도 분류 실패로 일반 대화로 처리합니다."
        
        # ChatModeClient를 사용한 LLM 호출
        try:
            chat_mode_client = get_chat_mode_client()
            
            # ChatModeClient로 응답 생성 (맥락은 이미 위에서 구성됨)
            assistant_message = await chat_mode_client.generate_response(
                mode=request.chat_mode,
                user_message=request.message,
                conversation_context=conversation_context if 'conversation_context' in locals() and conversation_context else None,
                search_context=search_context_dict
            )
        except Exception as e:
            logger.error(f"LLM generation failed, fallback to template: {e}")
            assistant_message = await _generate_assistant_response(
                request.message,
                search_results,
                dialog_context,
                search_context_dict,
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


@conversation_router.post("/preload", response_model=PreloadResponse)
async def preload_mode(request: PreloadRequest):
    """지정한 채팅 모드의 모델을 미리 로드"""
    try:
        chat_mode_client = get_chat_mode_client()
        keep_alive = "15m"
        ok = await chat_mode_client.preload_mode(request.mode, keep_alive=keep_alive)
        config = chat_mode_client.get_config(request.mode)
        return PreloadResponse(
            mode=request.mode,
            model=config["model"],
            success=ok,
            keep_alive=keep_alive,
        )
    except Exception as e:
        logger.error(f"Failed to preload mode {request.mode}: {e}")
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


@conversation_router.get("/sessions/{session_id}/turns")
async def get_turns(session_id: str):
    """프론트엔드 호환용: 세션의 턴 리스트 조회"""
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        turns = session_manager.get_session_turns(session_id)
        return [
            {
                "turn_id": t.id,
                "session_id": t.session_id,
                "query": t.user_message,
                "response": t.assistant_message,
                "sources": t.search_results or [],
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "processing_time": t.response_time_ms,
            }
            for t in turns
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get turns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AddTurnRequest(BaseModel):
    query: str = Field(..., min_length=1)


@conversation_router.post("/sessions/{session_id}/turns")
async def add_turn(session_id: str, req: AddTurnRequest):
    """프론트엔드 호환용: 메시지 전송 후 하나의 턴 레코드 반환"""
    sm_req = SendMessageRequest(message=req.query)
    resp = await send_message(session_id, sm_req)  # type: ignore[arg-type]
    return {
        "turn_id": None,
        "session_id": resp.session_id,
        "query": resp.user_message,
        "response": resp.assistant_message,
        "sources": resp.search_context or {},
        "created_at": datetime.utcnow().isoformat(),
        "processing_time": resp.response_time_ms,
    }


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


@conversation_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """세션 삭제 (관련 데이터 포함)"""
    try:
        session_manager = get_session_manager()
        deleted = session_manager.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
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
