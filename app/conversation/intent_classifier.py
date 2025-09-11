#!/usr/bin/env python3
"""Simple intent classifier for conversation system.

This module provides a lightweight classifier that distinguishes between
small talk and information requests based on heuristic patterns.
"""

from __future__ import annotations

import re
from typing import List


class IntentClassifier:
    """Classify user utterances into high level intents."""

    def __init__(self) -> None:
        # Patterns for small talk phrases
        self.small_talk_patterns: List[re.Pattern] = [
            re.compile(r"^(안녕|안녕하세요|반가워|반갑습니다)"),
            re.compile(r"(날씨|기분|잘 지내|오늘 어때)"),
            re.compile(r"(질문해도|물어봐도|괜찮).*?[될까|도될까|을까]"),
            re.compile(r"^(고마워|감사|수고)"),
            re.compile(r"(잘했어|좋아|멋져|훌륭)"),
            re.compile(r"^(네|예|응|그래)$"),
            re.compile(r"(채팅|대화).*?(시작|해보|하자)"),
        ]

        # Patterns that usually indicate information requests
        self.info_request_patterns: List[re.Pattern] = [
            re.compile(r"(정보|알려|어떻게|무엇|언제|어디|왜|뭐|방법)"),
            re.compile(r"(정책|규정|절차|신청|접수|처리)"),
            re.compile(r"(휴가|연차|출장|교육|회의)"),
            re.compile(r"(급여|연봉|보너스|수당)"),
            re.compile(r".*?(어떻게|방법|절차).*?\?"),
            re.compile(r".*?(언제|몇시|며칠).*?\?"),
            re.compile(r".*?(무엇|뭐|어떤).*?\?"),
        ]

    def classify(self, text: str) -> str:
        """Return a simple intent label for the given text."""
        lowered = text.lower()
        for pattern in self.small_talk_patterns:
            if pattern.search(lowered):
                return "small_talk"

        for pattern in self.info_request_patterns:
            if pattern.search(lowered):
                return "info_request"

        return "unknown"

    def requires_search(self, text: str) -> bool:
        """Return True if the query likely needs searching."""
        return self.classify(text) != "small_talk"
