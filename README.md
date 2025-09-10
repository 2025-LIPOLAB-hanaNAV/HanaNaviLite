# HanaNaviLite

**경량화된 그룹포털 게시판 RAG 챗봇**

32GB RAM 환경에 최적화된, 최소한의 프레임워크로 최대 성능을 내도록 설계된 RAG 챗봇 시스템입니다. 모든 개발 단계가 완료되었으며, 전체 테스트를 통과하여 안정적인 사용성을 제공합니다.

---

## 🎯 **설계 원칙**

1.  **최소 의존성**: 5개 핵심 스택으로 완전한 RAG 시스템 구현
2.  **메모리 효율**: 32GB 환경에서 안정적 운영 (25GB 이하 사용)
3.  **자체 구현 우선**: 핵심 비즈니스 로직은 100% 자체 개발
4.  **정확도 우선**: 은행 업무 특성상 응답 정확도를 최우선으로 고려

---

## 🏗️ **아키텍처**

```
[High-Fidelity React UI] ──> [FastAPI Core] ──> [Hybrid Search Engine]
         │                           │                    │
    [Radix UI]                       │                    ├─> SQLite FTS5 (IR)
    [Tailwind CSS]                   │                    └─> FAISS (Vector)
    [Evidence Panel]                 │
    [Quality Dashboard]              ├─> [ETL Pipeline] ──> [File Parser]
                                     └─> [LLM Service] ──> [Ollama + Gemma3]
```

### **핵심 스택**
*   **FastAPI**: 통합 백엔드 API
*   **SQLite**: 통합 데이터베이스 (메타데이터 + IR + 캐시)
*   **FAISS**: 벡터 검색 엔진
*   **Ollama**: LLM 서빙 (Gemma3 12B)
*   **React**: 고급 프론트엔드 UI (Radix UI, Tailwind CSS 기반)

---

## 🚀 **빠른 시작**

### **환경 요구사항**
*   **권장**: 16GB+ RAM, 8core+ CPU
*   **소프트웨어**: Python 3.11+, Node.js 16+, Docker
*   **LLM 서버**: Ollama 서버 (로컬 또는 Docker)

### **설치 및 실행 (Makefile 사용)**

**1. 전체 시스템 시작 (Docker)**

```bash
# Docker 이미지 빌드 및 컨테이너 실행
make docker-up

# 필요한 LLM 모델 다운로드 (최초 1회)
make pull-model
```

**2. 로컬 개발 환경 실행**

```bash
# Python/Node.js 의존성 설치
make install

# 개발 서버 실행 (API + UI)
make dev
```

**🎯 접속 주소:**
*   **🤖 챗봇 UI (로컬)**: http://localhost:5174
*   **🐳 챗봇 UI (Docker)**: http://localhost:8001/ui/
*   **📡 API 서버**: http://localhost:8001
*   **📚 API 문서**: http://localhost:8001/docs

---

## ✅ **테스트 현황**

**모든 테스트 통과 (105/105)**

*   **단위/통합 테스트**: 모든 백엔드 기능 및 API 엔드포인트 테스트 완료.
*   **성능 테스트**: 메모리 사용량 및 응답 시간 목표치 만족 (Ollama 외부 의존성 Mock 처리).
*   **코드 품질**: `make lint` 실행 시 문제 없음.

---

## 🚧 **개발 현황**

**모든 개발 단계 완료**

*   **Phase 1: 핵심 인프라** ✅
*   **Phase 2: 검색 엔진** ✅
*   **Phase 3: ETL & LLM** ✅
*   **Phase 4: UI & 최적화** ✅
*   **Phase 5: 고급 UI 통합** ✅

프로젝트는 현재 모든 핵심 기능과 고급 UI 기능이 통합되어 완전한 RAG 챗봇으로 작동합니다.

---

## 📂 **프로젝트 구조**

```
HanaNaviLite/
├── app/              # FastAPI 백엔드
├── ui/               # React 프론트엔드
├── data/             # SQLite DB 저장소
├── models/           # FAISS 인덱스 저장소
├── uploads/          # 업로드 파일 저장소
├── docs/             # 프로젝트 문서
├── tests/            # Pytest 테스트
├── Makefile          # 자동화 스크립트
└── docker-compose.yml # Docker 설정
```

---

## 👥 **기여자**

*   **팀 위자드 2팀 - 하나 내비**
    *   기획/PM: 서정빈
    *   AI 파트: 김진수, 김윤하, 전준휘
    *   데이터 파트: 고은혜, 전준휘
    *   UI/UX: 전준휘, 서정빈
    *   인프라: 고은혜, 전준휘
