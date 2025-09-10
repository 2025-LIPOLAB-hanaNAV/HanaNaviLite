import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.answer_enhancement import (
    validate_and_fix_citations,
    improve_korean_formatting,
    enhance_answer_quality,
)


def test_validate_and_fix_citations_filters_unused():
    answer = "문장[1]\n\nCitations: [1,2]"
    citations = [{"id": "a"}, {"id": "b"}]
    new_answer, used = validate_and_fix_citations(answer, citations)
    assert "Citations: [1]" in new_answer
    assert len(used) == 1 and used[0]["id"] == "a"


def test_improve_korean_formatting_basic():
    text = "문서 는 5 개 있습니다."
    formatted = improve_korean_formatting(text)
    assert formatted == "문서는 5개 있습니다."


def test_enhance_answer_quality_verification_flag():
    answer = "내용"
    citations = [{"id": "a"}]
    enhanced, final_citations, verified = enhance_answer_quality(answer, citations, "질문")
    assert not verified
    assert final_citations == []
    assert "내용" in enhanced
