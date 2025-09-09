import logging
from typing import Dict, Any, List, Optional
from app.llm.ollama_client import get_ollama_client, OllamaClient

logger = logging.getLogger(__name__)

class StructuredQAEngine:
    """
    구조화된 데이터 기반 질의응답 엔진
    테이블, 차트 등 구조화된 데이터에 대한 질문에 답변합니다.
    """
    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.llm_client = llm_client or get_ollama_client()
        logger.info("Structured QA Engine initialized.")

    async def answer_structured_data_query(self, query: str, structured_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        주어진 구조화된 데이터에 대해 질문에 답변합니다.
        
        Args:
            query: 사용자 질문
            structured_data: 질문과 관련된 구조화된 데이터 (예: 테이블 행의 리스트)
            
        Returns:
            Dict: 답변 및 관련 정보
        """
        if not structured_data:
            return {"answer": "제공된 구조화된 데이터가 없습니다.", "data_used": []}

        # 데이터를 LLM이 이해하기 쉬운 텍스트 형식으로 변환
        data_context = self._format_structured_data_for_llm(structured_data)

        prompt = f"""
        다음은 사용자가 제공한 구조화된 데이터입니다. 이 데이터를 기반으로 질문에 답변해주세요.
        데이터에 없는 내용은 답변하지 마세요.

        [구조화된 데이터]
        {data_context}

        [질문]
        {query}

        답변:
        """
        
        try:
            logger.info(f"Sending structured data query to LLM: {query}")
            llm_response = await self.llm_client.generate(prompt)
            answer = llm_response.get('response', '').strip()
            
            return {"answer": answer, "data_used": structured_data}
        except Exception as e:
            logger.error(f"Failed to answer structured data query: {e}", exc_info=True)
            return {"answer": "구조화된 데이터 기반 답변 생성 중 오류가 발생했습니다.", "data_used": []}

    def _format_structured_data_for_llm(self, data: List[Dict[str, Any]]) -> str:
        """
        구조화된 데이터를 LLM 프롬프트에 적합한 텍스트 형식으로 변환합니다.
        """
        formatted_data = []
        for i, row in enumerate(data):
            row_str = f"행 {i+1}: "
            row_parts = []
            for key, value in row.items():
                row_parts.append(f"{key}: {value}")
            formatted_data.append(row_str + ", ".join(row_parts))
        return "\n".join(formatted_data)

# 전역 인스턴스
_structured_qa_engine: Optional[StructuredQAEngine] = None

def get_structured_qa_engine() -> StructuredQAEngine:
    global _structured_qa_engine
    if _structured_qa_engine is None:
        _structured_qa_engine = StructuredQAEngine()
    return _structured_qa_engine
