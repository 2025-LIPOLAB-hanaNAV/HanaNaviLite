import httpx
import logging
import json
from typing import List, Dict, Any, Optional, AsyncGenerator

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaClient:
    """
    Ollama LLM 서버와 통신하는 비동기 클라이언트
    """

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.llm_model
        self.timeout = 60  # 초
        self._client = httpx.AsyncClient()
        logger.info(f"OllamaClient initialized - Base URL: {self.base_url}, Model: {self.model}")

    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """HTTP 요청을 보내는 내부 함수"""
        try:
            response = await self._client.request(
                method,
                f"{self.base_url}{endpoint}",
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request to Ollama failed: {e}")
            raise

    async def generate(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """LLM으로부터 답변 생성 (스트리밍 미사용)"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "context": context or [],
            "stream": False,
            "options": {
                "temperature": settings.llm_temperature,
                "num_ctx": settings.llm_max_tokens
            }
        }
        try:
            response = await self._request("POST", "/api/generate", json=payload)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to generate non-streaming response: {e}")
            raise

    async def stream_generate(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """LLM으로부터 답변 스트리밍 생성"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "context": context or [],
            "stream": True,
            "options": {
                "temperature": settings.llm_temperature,
                "num_ctx": settings.llm_max_tokens
            }
        }
        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            yield chunk
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode stream chunk: {line}")
        except Exception as e:
            logger.error(f"Failed to generate streaming response: {e}")
            raise

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def health_check(self) -> bool:
        """Ollama 서버 상태 확인"""
        try:
            response = await self._request("GET", "/")
            return response.status_code == 200
        except Exception:
            return False

    async def show_model(self, model_name: str) -> bool:
        """모델 메타 정보를 조회하여 존재 여부 확인"""
        try:
            resp = await self._request("POST", "/api/show", json={"model": model_name})
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Model show failed for {model_name}: {e}")
            return False

    async def warm_up(self, model_name: Optional[str] = None, keep_alive: str = "5m") -> bool:
        """지정한 모델을 미리 로드하여 첫 토큰 지연을 줄임

        구현 메모:
        - keep_alive는 Ollama 스펙상 최상위 필드로 전달해야 함
        - 일부 조합에서 /api/generate가 500을 반환하는 경우가 있어 단계적 폴백 수행
        """
        target_model = model_name or self.model

        # 0) 모델 존재 확인 (없으면 곧바로 실패 반환)
        exists = await self.show_model(target_model)
        if not exists:
            logger.error(f"Model not found locally: {target_model}. Please pull it with 'ollama pull {target_model}'.")
            return False

        logger.info(f"Warming up model: {target_model} (keep_alive={keep_alive})")

        # 1) 기본 generate 시도 (정석: keep_alive는 top-level)
        payload_generate = {
            "model": target_model,
            "prompt": "warmup",
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": 0.0,
            },
        }
        try:
            await self._request("POST", "/api/generate", json=payload_generate)
            return True
        except Exception as e1:
            logger.error(f"Warm-up generate failed for {target_model}: {e1}")

        # 2) chat API로 재시도
        payload_chat = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": "warmup"}
            ],
            "stream": False,
            "keep_alive": keep_alive,
            "options": {
                "temperature": 0.0,
            },
        }
        try:
            await self._request("POST", "/api/chat", json=payload_chat)
            return True
        except Exception as e2:
            logger.error(f"Warm-up chat failed for {target_model}: {e2}")

        # 3) keep_alive 없이 최소 generate 재시도 (일부 구버전 호환)
        payload_min = {
            "model": target_model,
            "prompt": "warmup",
            "stream": False,
            "options": {"temperature": 0.0},
        }
        try:
            await self._request("POST", "/api/generate", json=payload_min)
            return True
        except Exception as e3:
            logger.error(f"Warm-up minimal generate failed for {target_model}: {e3}")
            return False


# 전역 인스턴스
_ollama_client: Optional[OllamaClient] = None

def get_ollama_client() -> OllamaClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
