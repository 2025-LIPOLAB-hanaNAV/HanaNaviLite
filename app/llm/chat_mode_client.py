#!/usr/bin/env python3
"""
채팅 모드별 LLM 클라이언트
빠른답/정밀검증/요약전용 모드에 따라 다른 모델과 프롬프트 사용
"""

import logging
from typing import Dict, Any, Optional
from app.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class ChatModeClient:
    """채팅 모드별 LLM 클라이언트"""
    
    def __init__(self):
        self.clients = {}
        self.mode_configs = {
            "quick": {
                "model": "gemma3:12b-it-qat",  # 빠른 응답용 경량 모델
                "backup_models": [
                    "gemma3:27b",
                    "gpt-oss:20b"
                ],
                "temperature": 0.7,
                "max_tokens": 512,
                "system_prompt": """당신은 빠른 응답을 제공하는 친근한 사내 도우미입니다.
간결하고 핵심적인 답변을 한국어로 제공하세요.

특징:
- 빠르고 정확한 응답
- 핵심만 간단히 설명
- 친근하고 도움이 되는 톤
- 불확실한 내용은 관련 부서 문의 안내

답변 스타일: 간결하고 직접적"""
            },
            "precise": {
                "model": "gpt-oss:20b",  # 정밀한 추론용 대형 모델  
                "backup_models": [
                    "gemma3:27b",
                    "gemma3:12b-it-qat"
                ],
                "temperature": 0.3,
                "max_tokens": 1024,
                "system_prompt": """당신은 정밀한 검증과 상세한 분석을 제공하는 전문 지식베이스 도우미입니다.
정확하고 상세한 정보를 한국어로 제공하며, 모든 답변에 근거와 출처를 명시하세요.

특징:
- 정확성과 신뢰성 최우선
- 상세한 설명과 맥락 제공
- 여러 관점에서의 분석
- 잠재적 예외사항이나 주의사항 포함
- 관련 정책이나 규정의 정확한 인용

답변 스타일: 상세하고 분석적이며 전문적

답변 구조:
1. **핵심 답변**: 질문에 대한 직접적 답변
2. **상세 설명**: 배경과 맥락 설명
3. **관련 규정**: 해당하는 정책이나 규정 명시
4. **주의사항**: 예외사항이나 추가 고려사항
5. **문의처**: 추가 문의를 위한 담당부서 정보"""
            },
            "summary": {
                "model": "gemma3:12b-it-qat",  # 요약에 적합한 모델
                "backup_models": [
                    "gemma3:27b",
                    "gpt-oss:20b"
                ],
                "temperature": 0.2,
                "max_tokens": 256,
                "system_prompt": """당신은 긴 텍스트를 핵심만 간추려서 요약하는 전문가입니다.
복잡한 내용을 이해하기 쉽게 정리하여 한국어로 제공하세요.

요약 원칙:
- 가장 중요한 핵심 내용 2-3개 포인트로 정리
- 불필요한 세부사항 제거
- 명확하고 간결한 문장 구조
- 핵심 키워드와 수치 정보 보존
- 액션 아이템이나 중요한 기한 강조

요약 형식:
**핵심 내용**
• [핵심 포인트 1]
• [핵심 포인트 2]  
• [핵심 포인트 3]

**중요사항**
• [주의할 점이나 기한 등]"""
            }
        }
    
    def get_client(self, mode: str) -> OllamaClient:
        """모드별 클라이언트 반환"""
        if mode not in self.clients:
            # OllamaClient는 설정에서 모델을 가져오므로 매개변수 없이 생성
            self.clients[mode] = OllamaClient()
        return self.clients[mode]
    
    def get_config(self, mode: str) -> Dict[str, Any]:
        """모드별 설정 반환"""
        return self.mode_configs.get(mode, self.mode_configs["quick"])

    async def preload_mode(self, mode: str, keep_alive: str = "15m") -> bool:
        """지정 모드의 모델을 사전 로드하여 지연을 줄임"""
        try:
            config = self.get_config(mode)
            client = self.get_client(mode)
            ok = await client.warm_up(model_name=config["model"], keep_alive=keep_alive)
            if ok:
                logger.info(f"ChatModeClient preload ok - mode={mode}, model={config['model']}")
            else:
                logger.warning(f"ChatModeClient preload failed - mode={mode}, model={config['model']}")
            return ok
        except Exception as e:
            logger.error(f"Failed to preload mode {mode}: {e}")
            return False
    
    async def generate_response(
        self, 
        mode: str, 
        user_message: str,
        conversation_context: Optional[str] = None,
        search_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """모드별 응답 생성"""
        try:
            config = self.get_config(mode)
            client = self.get_client(mode)
            
            # 시스템 프롬프트 구성
            system_prompt = config["system_prompt"]

            # 게시판/첨부 기반 지식베이스 정책 및 결과 부재 처리 규칙 주입
            results_count = 0
            requires_search = False
            intent = None
            if search_context:
                results_count = int(search_context.get("results_count", 0) or 0)
                requires_search = bool(search_context.get("requires_search", False))
                intent = search_context.get("intent")

            kb_policy = (
                "\n[지식베이스 정책]\n"
                "- 내부 지식은 '게시판 게시물 + 첨부파일'에 기반합니다.\n"
                "- 검색결과개수: {rc}. 결과가 0이면 추측하지 말고, 다음을 반드시 포함하세요:\n"
                "  1) '관련 게시물이나 첨부파일에서 정보를 찾지 못했습니다.'라는 안내\n"
                "  2) 재질문 가이드(키워드, 기간/부서 범위, 문서 유형 제안)\n"
                "  3) 필요 시 담당 부서/채널 안내(정중하고 간결하게)\n"
                "- 결과가 존재하면, 게시물/첨부에서 확인된 사실만 근거 기반으로 답하고, 허위 정보는 포함하지 마세요.\n"
            ).format(rc=results_count)
            
            # 컨텍스트 정보 추가 (내부 정보만 - 사용자에게 노출되지 않음)
            internal_context = ""
            if conversation_context:
                internal_context += f"\n[이전 대화 맥락]\n{conversation_context}\n"
            
            # 최종 프롬프트 구성
            if mode == "summary":
                # 요약 모드는 다른 구조 사용
                prompt = f"""{system_prompt}{kb_policy}

다음 내용을 요약해주세요:
{user_message}

요약:"""
            else:
                prompt = f"""{system_prompt}{kb_policy}{internal_context}

사용자 질문: {user_message}

답변:"""
            
            # 1) 권장: Chat API 우선 사용
            try:
                chat_messages = [
                    {"role": "system", "content": system_prompt + kb_policy},
                ]
                if mode == "summary":
                    chat_messages.append({
                        "role": "user",
                        "content": f"다음 내용을 요약해주세요:\n{user_message}\n\n요약:",
                    })
                else:
                    # 내부 컨텍스트는 system에 이미 포함, 사용자 메시지는 별도
                    chat_messages.append({
                        "role": "user",
                        "content": f"사용자 질문: {user_message}\n\n답변:",
                    })

                payload_chat = {
                    "model": config["model"],
                    "messages": chat_messages,
                    "stream": False,
                    "options": {
                        "temperature": config["temperature"],
                        # 출력 최대 토큰 수
                        "num_predict": config["max_tokens"],
                    },
                }
                response = await client._request("POST", "/api/chat", json=payload_chat)
                data = response.json()
                # Normalize chat response payloads
                text = None
                if isinstance(data, dict):
                    msg = data.get("message")
                    if isinstance(msg, dict):
                        text = msg.get("content")
                    elif isinstance(msg, str):
                        text = msg
                    if not text:
                        # Some backends might use 'content' or 'response'
                        cand = data.get("content") or data.get("response")
                        if isinstance(cand, str):
                            text = cand
                if isinstance(text, str) and text.strip():
                    return text.strip()
            except Exception as e_chat:
                logger.warning(f"Chat API failed for model {config['model']}: {e_chat}")

            # 2) 폴백: Generate API (옵션 최소화, num_predict만 지정)
            try:
                payload_gen = {
                    "model": config["model"],
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": config["temperature"],
                        "num_predict": config["max_tokens"],
                    },
                }
                response = await client._request("POST", "/api/generate", json=payload_gen)
                data = response.json()
                text = None
                if isinstance(data, dict):
                    cand = data.get("response") or data.get("message") or data.get("content")
                    if isinstance(cand, str):
                        text = cand
                if isinstance(text, str) and text.strip():
                    return text.strip()
            except Exception as e_gen:
                logger.warning(f"Generate API failed for model {config['model']}: {e_gen}")

            # 3) 백업 모델 폴백 시도 (설치된 모델만)
            backups = config.get("backup_models", [])
            for bmodel in backups:
                try:
                    if hasattr(client, "show_model"):
                        exists = await client.show_model(bmodel)
                        if not exists:
                            continue
                    payload_b = {
                        "model": bmodel,
                        "messages": [
                            {"role": "system", "content": system_prompt + kb_policy},
                            {"role": "user", "content": f"사용자 질문: {user_message}\n\n답변:"},
                        ],
                        "stream": False,
                        "options": {
                            "temperature": config["temperature"],
                            "num_predict": config["max_tokens"],
                        },
                    }
                    response = await client._request("POST", "/api/chat", json=payload_b)
                    data = response.json()
                    text = None
                    if isinstance(data, dict):
                        msg = data.get("message")
                        if isinstance(msg, dict):
                            text = msg.get("content")
                        elif isinstance(msg, str):
                            text = msg
                        if not text:
                            cand = data.get("content") or data.get("response")
                            if isinstance(cand, str):
                                text = cand
                    if isinstance(text, str) and text.strip():
                        logger.info(f"Fell back to backup model: {bmodel}")
                        return text.strip()
                except Exception as e_b:
                    logger.warning(f"Backup model failed ({bmodel}): {e_b}")

            # 4) 최종 폴백: 사과 메시지
            return (
                f"죄송합니다. {mode} 모드에서 일시적인 모델 오류가 발생했습니다. "
                "잠시 후 다시 시도하시거나 다른 모드를 선택해 주세요."
            )
            
        except Exception as e:
            logger.error(f"ChatModeClient 오류 (mode: {mode}): {e}")
            return f"죄송합니다. {mode} 모드에서 일시적인 오류가 발생했습니다."


# 싱글톤 인스턴스
_chat_mode_client = None

def get_chat_mode_client() -> ChatModeClient:
    """ChatModeClient 싱글톤 인스턴스 반환"""
    global _chat_mode_client
    if _chat_mode_client is None:
        _chat_mode_client = ChatModeClient()
    return _chat_mode_client
