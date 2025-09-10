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


# 전역 인스턴스
_ollama_client: Optional[OllamaClient] = None

def get_ollama_client() -> OllamaClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
