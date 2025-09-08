#!/usr/bin/env python3
"""
HanaNaviLite 버전 정보
"""

__version__ = "0.1.0"
__title__ = "HanaNaviLite"
__description__ = "경량화 RAG 챗봇 시스템"
__author__ = "팀 위자드 2팀 - 하나 내비"
__license__ = "MIT"

# 릴리즈 정보
RELEASE_DATE = "2025-09-08"
RELEASE_NOTES = """
## HanaNaviLite v0.1.0 - 첫 번째 안정 릴리즈

### 🎉 주요 기능
- ✅ **완전한 RAG 파이프라인**: 문서 업로드부터 AI 답변까지 End-to-End
- ✅ **하이브리드 검색**: FAISS 벡터 검색 + SQLite FTS5 IR 검색 융합
- ✅ **React UI**: 실시간 채팅 인터페이스 및 시스템 모니터링
- ✅ **경량화 최적화**: 25GB RAM 환경에서 안정적 운영
- ✅ **한국어 특화**: 은행 업무 도메인 최적화

### 📊 성능 지표
- 메모리 사용량: 7.18GB/25GB (28.7%)
- 응답 시간: < 10초
- 테스트 통과율: 100% (20/20 테스트)
- 코드 규모: 5,068 라인, 42개 모듈

### 🚀 기술 스택
- **Backend**: FastAPI + SQLite + FAISS
- **Frontend**: React + TypeScript + Tailwind CSS  
- **AI**: Ollama + Gemma3 12B + HuggingFace Transformers
- **Search**: Hybrid (Vector + IR) with RRF Fusion

### 📦 설치 및 실행
Docker Compose로 원클릭 실행 지원
"""

def get_version():
    """현재 버전 반환"""
    return __version__

def get_version_info():
    """버전 정보 딕셔너리 반환"""
    return {
        "version": __version__,
        "title": __title__,
        "description": __description__,
        "author": __author__,
        "license": __license__,
        "release_date": RELEASE_DATE
    }

if __name__ == "__main__":
    print(f"{__title__} v{__version__}")
    print(f"{__description__}")
    print(f"Released on {RELEASE_DATE}")