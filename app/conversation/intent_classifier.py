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
        ]

        # Patterns that usually indicate information requests
        self.info_request_patterns: List[re.Pattern] = [
            re.compile(r"(정보|알려|어떻게|무엇|언제|어디|왜)"),
            re.compile(r"\?"),
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
