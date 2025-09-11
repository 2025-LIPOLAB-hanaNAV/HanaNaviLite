#!/usr/bin/env python3
"""
Ollama 연동 서버 - 실제 conversation API와 Ollama를 사용
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import uuid
import httpx
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ollama Chat API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
sessions = {}
OLLAMA_BASE_URL = "http://localhost:11434"

class CreateSessionRequest(BaseModel):
    title: str = "새 대화"
    max_turns: int = 20
    session_duration_hours: int = 24

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
    search_context: dict = None
    context_explanation: str = ""
    response_time_ms: int
    confidence_score: float = None
    dialog_state: str = "active"
    current_topics: list = []

async def call_ollama(prompt: str, model: str = "gemma3:4b-it-qat") -> str:
    """Ollama API 호출"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 512
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "죄송합니다. 응답을 생성할 수 없습니다.")
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return "죄송합니다. 현재 AI 서비스에 일시적인 문제가 발생했습니다."
                
    except httpx.TimeoutException:
        logger.error("Ollama API timeout")
        return "응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
    except Exception as e:
        logger.error(f"Ollama API call failed: {e}")
        return "죄송합니다. 현재 AI 서비스에 문제가 발생했습니다."

def create_system_prompt(user_message: str, context: dict = None) -> str:
    """시스템 프롬프트 생성"""
    base_prompt = """당신은 사내 지식베이스 도우미입니다. 
한국어로 친절하고 정확하게 답변해주세요. 
사내 정책, 업무 프로세스, HR 관련 질문에 대해 도움을 드립니다.

다음 질문에 답변해주세요:"""
    
    if context and context.get("previous_messages"):
        conversation_context = "\n".join([
            f"이전 질문: {msg}" for msg in context["previous_messages"][-2:]
        ])
        base_prompt += f"\n\n대화 맥락:\n{conversation_context}\n"
    
    return f"{base_prompt}\n\n질문: {user_message}\n\n답변:"

@app.post("/conversation/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """새 대화 세션 생성"""
    session_id = str(uuid.uuid4())
    now = datetime.now()
    
    session = {
        "session_id": session_id,
        "title": request.title,
        "max_turns": request.max_turns,
        "created_at": now.isoformat(),
        "expires_at": now.isoformat(),
        "turn_count": 0,
        "turns": [],
        "messages": []
    }
    
    sessions[session_id] = session
    logger.info(f"Created session: {session_id}")
    
    return CreateSessionResponse(
        session_id=session_id,
        title=request.title,
        max_turns=request.max_turns,
        expires_at=now.isoformat(),
        created_at=now.isoformat()
    )

@app.post("/conversation/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """메시지 전송 및 Ollama 응답 생성"""
    start_time = time.time()
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    turn_number = session["turn_count"] + 1
    
    # 대화 컨텍스트 구성
    context = {
        "previous_messages": [msg["content"] for msg in session["messages"][-4:] if msg["role"] == "user"]
    }
    
    # 시스템 프롬프트 생성
    prompt = create_system_prompt(request.message, context)
    logger.info(f"Calling Ollama with prompt length: {len(prompt)}")
    
    # Ollama 호출
    assistant_message = await call_ollama(prompt)
    
    # 세션 업데이트
    session["turn_count"] = turn_number
    session["messages"].extend([
        {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()},
        {"role": "assistant", "content": assistant_message, "timestamp": datetime.now().isoformat()}
    ])
    
    turn_data = {
        "turn_number": turn_number,
        "user_message": request.message,
        "assistant_message": assistant_message,
        "timestamp": datetime.now().isoformat()
    }
    session["turns"].append(turn_data)
    
    response_time_ms = int((time.time() - start_time) * 1000)
    
    logger.info(f"Session {session_id}, Turn {turn_number}: Response generated in {response_time_ms}ms")
    
    return SendMessageResponse(
        session_id=session_id,
        turn_number=turn_number,
        user_message=request.message,
        assistant_message=assistant_message,
        search_context={"requires_search": True, "confidence": 0.9, "source": "ollama"},
        context_explanation="Ollama AI 모델을 통해 응답을 생성했습니다.",
        response_time_ms=response_time_ms,
        confidence_score=0.9,
        dialog_state="active",
        current_topics=["일반 대화"]
    )

@app.get("/health")
async def health_check():
    """Health check 및 Ollama 연결 상태 확인"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            ollama_status = "connected" if response.status_code == 200 else "error"
    except Exception:
        ollama_status = "disconnected"
    
    return {
        "status": "ok", 
        "message": "Ollama server is running",
        "ollama_status": ollama_status,
        "active_sessions": len(sessions)
    }

@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """세션 정보 조회"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return sessions[session_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)