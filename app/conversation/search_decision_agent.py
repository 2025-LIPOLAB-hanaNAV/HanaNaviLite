#!/usr/bin/env python3
"""
검색 필요성 판단 에이전트
LLM을 사용해서 사용자 질문이 실제로 문서 검색이 필요한지 지능적으로 판단
"""

import re
import logging
from typing import Optional, Dict, Any
from app.llm.ollama_client import get_ollama_client

logger = logging.getLogger(__name__)


class SearchDecisionAgent:
    """검색 필요성을 지능적으로 판단하는 에이전트"""
    
    def __init__(self):
        self.system_prompt = """당신은 사용자의 질문을 분석해서 회사 문서나 정책을 검색해야 하는지 판단하는 전문가입니다.

핵심 원칙: 사용자가 구체적인 정보나 업무 관련 내용을 원하는지, 아니면 단순히 대화를 시작하려는지 구분하는 것입니다.

**문서 검색이 필요한 경우 (info_request):**
- 회사 정책, 규정, 절차에 대한 구체적 질문
- 업무 프로세스, 신청 방법, 처리 절차 문의  
- 특정 정보나 데이터가 필요한 질문
- 공식 문서나 양식에 대한 문의
- 예시: "휴가 정책이 뭔가요?", "연차 신청은 어떻게 하나요?", "급여 지급일이 언제예요?"

**일반 대화로 충분한 경우 (small_talk):**
- 인사말, 감사 표현, 일상적 대화
- 질문 허락을 구하는 표현 (실제 질문이 아닌 대화 시작용)
- 감정이나 의견 표현, 단순 응답
- **매우 중요**: "질문해도 될까요?", "물어봐도 되나요?", "질문하겠습니다", "질문이 있습니다" 등은 모두 대화 시작용 표현이므로 small_talk입니다.
- 단순히 "질문"이라는 단어가 들어있다고 해서 info_request가 아닙니다!
- 예시: "안녕하세요", "질문해도 될까요?", "물어봐도 되나요?", "질문하겠습니다", "질문이 있습니다", "고마워요", "좋아요"

**판단 시 주의사항:**
1. "질문" 키워드가 있어도 실제 정보를 요청하는 것이 아니면 small_talk입니다.
2. 허락을 구하는 표현은 모두 small_talk로 분류하세요.
3. 불확실할 때는 small_talk로 분류하는 것이 더 좋습니다.

응답은 반드시 다음 JSON 형식으로 해주세요:
{
  "requires_search": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "판단 근거 (한 줄로 간단히)",
  "intent_type": "info_request" 또는 "small_talk"
}"""

    async def should_search(self, user_query: str, conversation_context: Optional[str] = None) -> Dict[str, Any]:
        """
        사용자 쿼리가 문서 검색이 필요한지 판단
        
        Args:
            user_query: 사용자 질문
            conversation_context: 대화 맥락 (선택)
            
        Returns:
            Dict containing: requires_search, confidence, reasoning, intent_type
        """
        try:
            # LLM에 질의할 프롬프트 구성
            context_part = ""
            if conversation_context:
                context_part = f"\n이전 대화 맥락:\n{conversation_context}\n"
            
            prompt = f"""{self.system_prompt}

{context_part}
사용자 질문: "{user_query}"

위 질문을 분석해서 문서 검색이 필요한지 판단하고 JSON으로 답변해주세요:"""

            llm = get_ollama_client()
            response = await llm.generate(prompt)
            
            response_text = response.get("response", "").strip()
            
            # JSON 파싱 시도
            try:
                import json
                # JSON 부분만 추출
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                    
                    # 결과 검증 및 기본값 설정
                    return {
                        "requires_search": result.get("requires_search", False),
                        "confidence": float(result.get("confidence", 0.5)),
                        "reasoning": result.get("reasoning", "LLM 분석 결과"),
                        "intent_type": result.get("intent_type", "small_talk")
                    }
                else:
                    # JSON 파싱 실패 시 다시 시도
                    retry_result = await self._retry_with_simpler_prompt(user_query)
                    return retry_result
                    
            except Exception as json_error:
                logger.warning(f"JSON 파싱 실패: {json_error}, 응답: {response_text}")
                # 다시 시도
                retry_result = await self._retry_with_simpler_prompt(user_query)
                return retry_result
                
        except Exception as e:
            logger.error(f"SearchDecisionAgent 오류: {e}")
            # 완전 실패 시 안전한 기본값
            return {
                "requires_search": False,
                "confidence": 0.3,
                "reasoning": "시스템 오류로 인한 기본 분류",
                "intent_type": "small_talk"
            }
    
    async def _retry_with_simpler_prompt(self, user_query: str) -> Dict[str, Any]:
        """더 간단한 프롬프트로 재시도"""
        try:
            simple_prompt = f"""다음 질문이 업무 정보를 요청하는지 판단하세요:
"{user_query}"

질문만 하는 허락 요청 (예: "질문해도 될까요?") → small_talk
구체적 정보 요청 (예: "휴가 정책이 뭔가요?") → info_request

JSON으로만 답변:
{{"requires_search": true/false, "intent_type": "small_talk" 또는 "info_request", "confidence": 0.8}}"""

            llm = get_ollama_client()
            response = await llm.generate(simple_prompt, max_tokens=100, temperature=0.0)
            response_text = response.get("response", "").strip()
            
            import json
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                return {
                    "requires_search": result.get("requires_search", False),
                    "confidence": float(result.get("confidence", 0.5)),
                    "reasoning": "간단한 프롬프트로 재분류",
                    "intent_type": result.get("intent_type", "small_talk")
                }
                
        except Exception as e:
            logger.warning(f"Retry도 실패: {e}")
        
        # 완전 실패시 안전한 기본값
        return {
            "requires_search": False,
            "confidence": 0.4,
            "reasoning": "분류 실패로 안전한 기본값 적용",
            "intent_type": "small_talk"
        }