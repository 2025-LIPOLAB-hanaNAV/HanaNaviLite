import logging
from typing import List, Dict, Any, Optional
from app.llm.ollama_client import get_ollama_client, OllamaClient

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """
    텍스트 기반 질문 자동 생성 엔진
    주어진 문서나 텍스트에서 질문을 생성합니다.
    """
    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.llm_client = llm_client or get_ollama_client()
        logger.info("Question Generator initialized.")

    async def generate_questions(self, text: str, num_questions: int = 3) -> List[str]:
        """
        주어진 텍스트에서 질문을 생성합니다.
        
        Args:
            text: 질문을 생성할 텍스트
            num_questions: 생성할 질문의 개수
            
        Returns:
            List[str]: 생성된 질문 목록
        """
        if not text:
            return []

        prompt = f"""
        다음 텍스트를 읽고, 텍스트의 내용을 바탕으로 {num_questions}개의 질문을 생성해주세요.
        질문은 명확하고 간결해야 하며, 텍스트에서 직접 답을 찾을 수 있는 질문이어야 합니다.
        각 질문은 번호가 매겨진 목록 형태로 제시해주세요.

        [텍스트]
        {text}

        [질문 생성]
        """
        
        try:
            logger.info(f"Generating {num_questions} questions from text (length: {len(text)})...")
            llm_response = await self.llm_client.generate(prompt)
            generated_text = llm_response.get('response', '').strip()
            
            # 생성된 텍스트에서 질문 목록 파싱
            questions = self._parse_questions_from_text(generated_text)
            
            return questions
        except Exception as e:
            logger.error(f"Failed to generate questions: {e}", exc_info=True)
            return []

    def _parse_questions_from_text(self, text: str) -> List[str]:
        """
        LLM 응답 텍스트에서 질문 목록을 파싱합니다.
        """
        questions = []
        # 번호가 매겨진 목록 (예: 1. 질문, 2. 질문) 파싱
        for line in text.split('\n'):
            if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')):
                questions.append(line.strip()[line.strip().find('.') + 1:].strip())
            elif line.strip().startswith('- '): # 불릿 포인트도 고려
                questions.append(line.strip()[2:].strip())
        return questions

# 전역 인스턴스
_question_generator: Optional[QuestionGenerator] = None

def get_question_generator() -> QuestionGenerator:
    global _question_generator
    if _question_generator is None:
        _question_generator = QuestionGenerator()
    return _question_generator
