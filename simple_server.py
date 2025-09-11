#!/usr/bin/env python3
"""
Simple FastAPI server for testing chat integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import uuid
from datetime import datetime

app = FastAPI(title="Simple Chat API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for testing
sessions = {}

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

@app.post("/conversation/sessions", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new conversation session"""
    session_id = str(uuid.uuid4())
    now = datetime.now()
    
    session = {
        "session_id": session_id,
        "title": request.title,
        "max_turns": request.max_turns,
        "created_at": now.isoformat(),
        "expires_at": now.isoformat(),
        "turn_count": 0,
        "turns": []
    }
    
    sessions[session_id] = session
    
    return CreateSessionResponse(
        session_id=session_id,
        title=request.title,
        max_turns=request.max_turns,
        expires_at=now.isoformat(),
        created_at=now.isoformat()
    )

@app.post("/conversation/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """Send a message and get AI response"""
    start_time = time.time()
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    turn_number = session["turn_count"] + 1
    
    # Simulate AI response based on the question
    user_msg = request.message.lower()
    
    if "휴가" in user_msg or "휴직" in user_msg:
        assistant_message = """육아휴직에 대해 안내드리겠습니다.

근속 6개월 이상의 직원이 육아휴직을 신청할 수 있으며, 최대 1년까지 가능합니다. 
육아휴직 기간 중에는 기본급의 40%를 육아휴직급여로 지급하며, 매월 25일에 계좌로 입금됩니다.

신청 절차는 휴직 시작일 30일 전까지 인사팀에 신청서를 제출하시면 됩니다.

추가 문의사항이 있으시면 인사팀(내선번호: 1234)으로 연락해 주세요."""
    elif "급여" in user_msg or "연봉" in user_msg:
        assistant_message = """급여 관련 문의에 대해 안내드리겠습니다.

급여는 매월 25일에 지급되며, 연말정산은 매년 1월에 진행됩니다.
급여명세서는 사내 인트라넷에서 확인하실 수 있습니다.

급여 관련 상세한 문의는 인사팀으로 연락해 주세요."""
    elif "안녕" in user_msg or "hello" in user_msg.lower():
        assistant_message = """안녕하세요! 사내 지식베이스 도우미입니다.

궁금한 사내 정책이나 업무 관련 질문이 있으시면 언제든 말씀해 주세요.
- 인사 정책 (휴가, 휴직, 급여 등)
- IT 지원
- 업무 프로세스
- 각종 신청서 및 양식

무엇을 도와드릴까요?"""
    else:
        assistant_message = f"""'{request.message}'에 대한 정보를 확인해보겠습니다.

죄송합니다만, 해당 키워드에 대한 구체적인 정보를 찾지 못했습니다. 
더 구체적인 질문을 해주시거나 다음과 같은 방식으로 질문해 보세요:

- "휴가 정책이 어떻게 되나요?"
- "급여 지급일은 언제인가요?"
- "육아휴직 신청 방법을 알려주세요"

인사팀(내선: 1234) 또는 IT지원팀(내선: 5678)으로 직접 문의하실 수도 있습니다."""
    
    # Update session
    session["turn_count"] = turn_number
    turn_data = {
        "turn_number": turn_number,
        "user_message": request.message,
        "assistant_message": assistant_message,
        "timestamp": datetime.now().isoformat()
    }
    session["turns"].append(turn_data)
    
    response_time_ms = int((time.time() - start_time) * 1000)
    
    return SendMessageResponse(
        session_id=session_id,
        turn_number=turn_number,
        user_message=request.message,
        assistant_message=assistant_message,
        search_context={"requires_search": True, "confidence": 0.85},
        context_explanation="관련 정보를 검색했습니다.",
        response_time_ms=response_time_ms,
        confidence_score=0.85,
        dialog_state="active",
        current_topics=["HR 정책"]
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Simple server is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)