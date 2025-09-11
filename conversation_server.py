#!/usr/bin/env python3
"""
기존 conversation API 사용하는 서버
"""

import sys
import os

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.abspath('.'))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import uuid
import httpx
from datetime import datetime
import logging

# 기존 conversation 모듈 임포트
from app.conversation.intent_classifier import IntentClassifier
from app.conversation.session_manager import get_session_manager, ConversationSession
from app.conversation.search_decision_agent import SearchDecisionAgent
from app.llm.ollama_client import get_ollama_client

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HanaNavi Conversation API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateSessionRequest(BaseModel):
    title: str = "새 대화"
    max_turns: int = 20
    session_duration_hours: int = 24
    user_id: str = None
    metadata: dict = None

class CreateSessionResponse(BaseModel):
    session_id: str
    title: str
    max_turns: int
    expires_at: str
    created_at: str

class SendMessageRequest(BaseModel):
    message: str
    search_engine_type: str = "hybrid"
    include_context: bool = True
    max_context_turns: int = 3

class SendMessageResponse(BaseModel):
    session_id: str
    turn_number: int
    user_message: str
    assistant_message: str
    summary: str = None  # 요약 추가
    search_context: dict = None
    context_explanation: str = ""
    response_time_ms: int
    confidence_score: float = None
    dialog_state: str = "active"
    current_topics: list = []

@app.post("/conversation/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """새 대화 세션 생성"""
    try:
        session_manager = get_session_manager()
        
        # 세션 생성
        session = session_manager.create_session(
            user_id=request.user_id,
            title=request.title,
            max_turns=request.max_turns,
            session_duration_hours=request.session_duration_hours,
            metadata=request.metadata
        )
        
        logger.info(f"Created session: {session.session_id}")
        
        return CreateSessionResponse(
            session_id=session.session_id,
            title=session.title,
            max_turns=session.max_turns,
            expires_at=session.expires_at.isoformat(),
            created_at=session.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/conversation/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """메시지 전송 및 응답 생성"""
    start_time = time.time()
    
    try:
        session_manager = get_session_manager()
        search_decision_agent = SearchDecisionAgent()
        
        # 세션 확인
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.status != 'active':
            raise HTTPException(status_code=400, detail=f"Session is {session.status}")
        
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
        
        # AI 에이전트로 검색 필요성 판단
        decision_result = await search_decision_agent.should_search(
            request.message, 
            conversation_context if conversation_context else None
        )
        
        user_intent = decision_result["intent_type"]
        requires_search = decision_result["requires_search"]
        confidence = decision_result["confidence"]
        reasoning = decision_result["reasoning"]
        
        turn_number = session.turn_count + 1
        
        logger.info(f"Session {session_id}: SearchDecision={requires_search}, Intent={user_intent}, Confidence={confidence:.2f}, Reasoning={reasoning}")
        
        # LLM 응답 생성
        try:
            llm = get_ollama_client()
            
            # 시스템 프롬프트 생성
            if user_intent == "small_talk":
                system_hint = """당신은 친근한 사내 도우미입니다. 
간단한 인사나 일상 대화에는 자연스럽고 친근하게 대답하세요. 
복잡한 설명이나 근거 자료는 필요하지 않습니다.
답변은 간단하고 자연스럽게 해주세요."""
                context_explanation = f"AI 에이전트가 일상 대화로 판단했습니다. (신뢰도: {confidence:.1f})"
            elif requires_search:
                system_hint = """당신은 사내 지식베이스 도우미입니다. 
정확하고 도움이 되는 정보를 한국어로 제공하세요.
회사 정책, 업무 프로세스, HR 관련 질문에 전문적으로 답변하세요.

답변 형식:
- 중요한 정보는 **굵게** 표시
- 여러 항목이 있을 때는 번호나 불릿 포인트 사용
- 절차나 단계는 명확하게 구분하여 설명
- 연락처나 담당부서 정보 포함

만약 정확한 정보가 없다면 "정확한 답변을 위해 관련 부서에 문의해 주세요"라고 안내하세요."""
                context_explanation = f"AI 에이전트가 문서 검색이 필요한 정보 요청으로 판단했습니다. (신뢰도: {confidence:.1f})"
            else:
                system_hint = """당신은 친근한 사내 도우미입니다. 
사용자의 질문에 도움이 되도록 답변하되, 확실하지 않은 회사 정책이나 규정에 대해서는 
관련 부서나 담당자에게 문의하라고 안내하세요.
답변은 친근하고 도움이 되는 톤으로 작성해주세요."""
                context_explanation = f"AI 에이전트가 일반 대화로 판단했습니다. (신뢰도: {confidence:.1f})"
            
            # 이전 대화 맥락 (최근 3턴)
            recent_turns = session_manager.get_session_turns(session_id, limit=3)
            context_messages = []
            for turn in recent_turns[-2:]:  # 최근 2턴만 사용
                context_messages.extend([
                    f"사용자: {turn.user_message}",
                    f"도우미: {turn.assistant_message}"
                ])
            
            context_hint = ""
            if context_messages:
                context_hint = f"\n[이전 대화]\n" + "\n".join(context_messages[-4:]) + "\n"
            
            prompt = f"{system_hint}{context_hint}\n\n[현재 질문]\n{request.message}\n\n답변:"
            
            llm_resp = await llm.generate(prompt)
            assistant_message = llm_resp.get("response") or llm_resp.get("message") or ""
            
            if not assistant_message:
                assistant_message = "죄송합니다. 현재 답변을 생성할 수 없습니다."
            
            # 정보 요청일 때만 요약 생성
            summary_text = assistant_message  # 기본값은 전체 응답
            if requires_search and assistant_message:
                try:
                    summary_prompt = f"""다음 답변을 2-3문장으로 핵심만 간단히 요약해주세요:

{assistant_message}

요약 (핵심만 2-3문장):"""
                    
                    summary_resp = await llm.generate(summary_prompt, max_tokens=150, temperature=0.3)
                    summary_result = summary_resp.get("response") or summary_resp.get("message") or ""
                    
                    if summary_result and len(summary_result.strip()) > 10:
                        summary_text = summary_result.strip()
                        logger.info(f"Generated summary: {len(summary_text)} chars vs original: {len(assistant_message)} chars")
                    
                except Exception as e:
                    logger.warning(f"Failed to generate summary: {e}")
                    # 폴백: 첫 번째 문단만 사용
                    first_paragraph = assistant_message.split('\n\n')[0]
                    if len(first_paragraph) < len(assistant_message) * 0.7:  # 70%보다 짧으면 요약으로 사용
                        summary_text = first_paragraph
                
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # 폴백 응답
            if user_intent == "small_talk":
                assistant_message = "안녕하세요! 무엇을 도와드릴까요?"
                summary_text = assistant_message
            else:
                assistant_message = "죄송합니다. 현재 시스템에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
                summary_text = "시스템 오류로 답변을 생성할 수 없습니다."
            context_explanation = "시스템 오류로 인해 기본 응답을 제공했습니다."
        
        # 응답 시간 계산
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 대화 턴 저장
        turn = session_manager.add_turn(
            session_id=session_id,
            user_message=request.message,
            assistant_message=assistant_message,
            search_query=request.message if requires_search else None,
            search_results=[],
            context_used=context_explanation,
            response_time_ms=response_time_ms,
            confidence_score=0.9 if user_intent != "unknown" else 0.5
        )
        
        # search_context 구성
        search_context = {
            "intent": user_intent,
            "requires_search": requires_search,
            "confidence": confidence,
            "reference_type": "info_request" if requires_search else user_intent,
            "original_query": request.message,
            "enhanced_query": request.message,
            "decision_reasoning": reasoning,
            "ai_agent_decision": True
        }
        
        logger.info(f"Session {session_id}, Turn {turn_number}: Intent={user_intent}, RequiresSearch={requires_search}")
        
        return SendMessageResponse(
            session_id=session_id,
            turn_number=turn.turn_number,
            user_message=request.message,
            assistant_message=assistant_message,
            summary=summary_text if requires_search else None,  # 정보 요청일 때만 요약 제공
            search_context=search_context,
            context_explanation=context_explanation,
            response_time_ms=response_time_ms,
            confidence_score=search_context["confidence"],
            dialog_state="active",
            current_topics=["일상 대화"] if user_intent == "small_talk" else ["업무 문의"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check"""
    try:
        session_manager = get_session_manager()
        active_sessions = len(session_manager.get_active_sessions())
        
        # Ollama 연결 확인
        try:
            llm = get_ollama_client()
            # 간단한 테스트 호출
            test_resp = await llm.generate("test", max_tokens=1)
            ollama_status = "connected"
        except Exception:
            ollama_status = "disconnected"
        
        return {
            "status": "ok",
            "message": "HanaNavi Conversation API",
            "active_sessions": active_sessions,
            "ollama_status": ollama_status
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "active_sessions": 0,
            "ollama_status": "unknown"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)