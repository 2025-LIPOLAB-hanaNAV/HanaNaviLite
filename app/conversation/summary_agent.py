import asyncio
import logging
from typing import Optional

from app.llm.ollama_client import get_ollama_client, OllamaClient

logger = logging.getLogger(__name__)


class ConversationSummarizer:
    """Summarize recent conversation turns using an LLM."""

    def __init__(
        self,
        session_manager: Optional["ConversationSessionManager"] = None,
        llm_client: Optional[OllamaClient] = None,
        max_turns: int = 5,
    ):
        if session_manager is None:
            from app.conversation.session_manager import get_session_manager as gsm
            session_manager = gsm()
        self.session_manager = session_manager
        self.llm_client = llm_client or get_ollama_client()
        self.max_turns = max_turns

    async def summarize(self, session_id: str) -> str:
        """Return a concise summary of the recent conversation turns."""
        turns = self.session_manager.get_session_turns(session_id, limit=self.max_turns)
        if not turns:
            return ""

        convo_lines = []
        for turn in turns:
            convo_lines.append(f"User: {turn.user_message}")
            if turn.assistant_message:
                convo_lines.append(f"Assistant: {turn.assistant_message}")
        convo_text = "\n".join(convo_lines)

        prompt = (
            "다음은 사용자와 AI 어시스턴트의 최근 대화입니다. "
            "핵심 정보와 주제를 유지하면서 간결하게 요약해주세요.\n\n"
            f"[대화]\n{convo_text}\n\n[요약]"
        )
        try:
            response = await self.llm_client.generate(prompt)
            summary = response.get("response", "").strip()
            if summary:
                return summary
        except Exception as e:
            logger.error(f"Conversation summary failed: {e}")
        # Fallback to concatenated conversation text
        return convo_text

    def summarize_sync(self, session_id: str) -> str:
        """Synchronous wrapper for summarize."""
        try:
            return asyncio.run(self.summarize(session_id))
        except RuntimeError:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.summarize(session_id))
                return ""
            except Exception:
                return ""


_summarizer: Optional[ConversationSummarizer] = None


def get_conversation_summarizer() -> ConversationSummarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = ConversationSummarizer()
    return _summarizer
