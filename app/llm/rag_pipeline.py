import logging
from typing import List, Dict, Any, Optional, AsyncGenerator

from app.search.hybrid_engine import get_hybrid_search_engine, HybridSearchResult
from app.llm.ollama_client import get_ollama_client
from app.utils.answer_enhancement import enhance_answer_quality

logger = logging.getLogger(__name__)


from app.llm.ollama_client import get_ollama_client

class RAGPipeline:
    """
    검색-증강-생성(RAG) 파이프라인
    """

    def __init__(self):
        self.search_engine = get_hybrid_search_engine()
        self.llm_client = get_ollama_client()
        logger.info("RAG Pipeline initialized")

    def _build_prompt(self, query: str, context_chunks: List[HybridSearchResult]) -> str:
        """
        LLM에 전달할 프롬프트를 생성
        """
        context_str = ""
        for i, chunk in enumerate(context_chunks):
            context_str += f"[문서 {i+1}: {chunk.title}]\n{chunk.snippet}\n\n"

        prompt = f"아래의 정보를 바탕으로 다음 질문에 대해 한국어로 명확하고 간결하게 답변해 주세요.\n\n[정보]\n{context_str}[질문]\n{query}\n\n답변:"
        return prompt

    async def query(self, user_query: str) -> Dict[str, Any]:
        """
        RAG 파이프라인 실행 (스트리밍 미사용)
        """
        try:
            # 1. 하이브리드 검색으로 컨텍스트 검색
            logger.info(f"Performing hybrid search for query: '{user_query}'")
            context_chunks = await self.search_engine.search(user_query, top_k=5)

            if not context_chunks:
                return {"answer": "관련 정보를 찾을 수 없습니다.", "sources": []}

            # 2. 프롬프트 생성
            prompt = self._build_prompt(user_query, context_chunks)

            # 3. LLM 호출
            logger.info("Generating answer from LLM...")
            llm_response = await self.llm_client.generate(prompt)
            answer = llm_response.get('response', '').strip()

            # 4. 답변 후처리 및 인용 정보 추가
            citations = [
                {
                    "id": chunk.chunk_id,
                    "title": chunk.title,
                    "document_id": chunk.document_id,
                    "source_type": "hybrid",
                    "score": chunk.fusion_score
                }
                for chunk in context_chunks
            ]
            # enhanced_answer, final_citations = enhance_answer_quality(answer, citations, user_query)

            return {"answer": answer, "sources": citations}

        except Exception as e:
            logger.error(f"RAG pipeline failed for query '{user_query}': {e}", exc_info=True)
            raise

    async def stream_query(self, user_query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        RAG 파이프라인 실행 (스트리밍)
        """
        try:
            # 1. 컨텍스트 검색
            logger.info(f"Performing hybrid search for query: '{user_query}'")
            context_chunks = await self.search_engine.search(user_query, top_k=5)

            if not context_chunks:
                yield {"type": "result", "data": {"answer": "관련 정보를 찾을 수 없습니다.", "sources": []}}
                return

            # 2. 프롬프트 생성
            prompt = self._build_prompt(user_query, context_chunks)

            # 3. LLM 스트리밍 호출
            logger.info("Streaming answer from LLM...")
            full_answer = ""
            async for chunk in self.llm_client.stream_generate(prompt):
                token = chunk.get('response', '')
                full_answer += token
                yield {"type": "token", "data": token}

                if chunk.get('done', False):
                    # 스트리밍 완료 후 최종 결과 전송
                    citations = [
                        {
                            "id": c.chunk_id,
                            "title": c.title,
                            "document_id": c.document_id,
                            "source_type": "hybrid",
                            "score": c.fusion_score
                        }
                        for c in context_chunks
                    ]
                    # enhanced_answer, final_citations = enhance_answer_quality(full_answer, citations, user_query)
                    yield {"type": "result", "data": {"answer": full_answer, "sources": citations}}

        except Exception as e:
            logger.error(f"Streaming RAG pipeline failed for query '{user_query}': {e}", exc_info=True)
            yield {"type": "error", "data": {"detail": "스트리밍 중 오류가 발생했습니다."}}


# 전역 인스턴스
_rag_pipeline: Optional[RAGPipeline] = None

def get_rag_pipeline() -> RAGPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
