import asyncio
import logging
from typing import List, Optional

from app.llm.ollama_client import get_ollama_client, OllamaClient

logger = logging.getLogger(__name__)


class QueryRewriter:
    """LLM 기반 검색 쿼리 재작성기"""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.llm_client = llm_client or get_ollama_client()
        logger.info("QueryRewriter initialized")

    async def _rewrite_async(self, query: str, history: List[str]) -> str:
        """비동기적으로 쿼리를 재작성"""
        history_text = "\n".join(history) if history else "(대화 기록 없음)"
        prompt = (
            "다음은 사용자와의 이전 대화 내용입니다.\n"
            f"{history_text}\n\n"
            "사용자의 최신 질문을 검색에 적합하도록 명확하고 구체적으로 다시 작성해주세요.\n"
            f"질문: {query}\n\n재작성된 검색용 질문:"
        )
        try:
            response = await self.llm_client.generate(prompt)
            rewritten = response.get("response", "").strip()
            return rewritten or query
        except Exception as e:
            logger.error(f"Failed to rewrite query via LLM: {e}")
            return query

    def rewrite(self, query: str, history: Optional[List[str]] = None) -> str:
        """LLM을 사용하여 쿼리를 재작성 (동기식 래퍼)"""
        history = history or []
        try:
            return asyncio.run(self._rewrite_async(query, history))
        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            return query


_query_rewriter: Optional[QueryRewriter] = None


def get_query_rewriter() -> QueryRewriter:
    """QueryRewriter 싱글톤 인스턴스 반환"""
    global _query_rewriter
    if _query_rewriter is None:
        _query_rewriter = QueryRewriter()
    return _query_rewriter
