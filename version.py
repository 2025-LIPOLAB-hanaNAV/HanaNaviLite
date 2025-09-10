#!/usr/bin/env python3
"""
HanaNaviLite 버전 정보
"""

__version__ = "1.0.0"
__title__ = "HanaNaviLite"
__description__ = "경량화 RAG 챗봇 시스템"
__author__ = "팀 위자드 2팀 - 하나 내비"
__license__ = "MIT"

# 릴리즈 정보
RELEASE_DATE = "2025-09-11"
RELEASE_NOTES = """
## HanaNaviLite v1.0.0 - 최종 안정 버전

### 🎉 주요 변경사항
- ✅ **모든 개발 단계 완료**: Phase 1부터 5까지 모든 기능 구현 및 안정화
- ✅ **고품질 UI 통합**: Radix UI 기반의 새로운 챗봇 인터페이스 적용
- ✅ **테스트 커버리지 및 안정성 확보**: 모든 테스트(105개) 통과
- ✅ **문서 업데이트**: README, DEVELOPMENT, FEATURES 등 모든 주요 문서 최신화
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