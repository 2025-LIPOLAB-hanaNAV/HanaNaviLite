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

## 🏗️ **올인원 아키텍처**

```
[올인원 Docker 컨테이너]
├── [React UI 빌드된 정적 파일]
├── [FastAPI 백엔드 서버] ──> [Hybrid Search Engine]
│   └── /ui 경로에서 프론트엔드 서빙    ├─> SQLite FTS5 (IR)
│                                     └─> FAISS (Vector + GPU)
├── [ETL Pipeline] ──> [Multi-format Parser]
└── [LLM Service] ──> [Ollama + Gemma3]
```

**🎯 핵심 특징:**
- **단일 컨테이너**: 백엔드 + 프론트엔드 통합
- **GPU 최적화**: RTX 5080 자동 감지 및 활용
- **올인원 접속**: 하나의 URL로 모든 기능 이용

### **핵심 스택**
*   **FastAPI**: 통합 백엔드 API + 정적 파일 서빙
*   **SQLite**: 통합 데이터베이스 (메타데이터 + FTS5 + 캐시)
*   **FAISS**: GPU 가속 벡터 검색 엔진
*   **Ollama**: LLM 서빙 (Gemma3 12B)
*   **React**: 빌드된 SPA (올인원 통합)

---

## 🚀 **빠른 시작**

### **환경 요구사항**
*   **권장**: 16GB+ RAM, 8core+ CPU
*   **GPU**: NVIDIA GPU 지원 (RTX 5080 최적화)
*   **소프트웨어**: Docker, Docker Compose
*   **LLM 서버**: Ollama 서버 (로컬 권장)

### **설치 및 실행 (Makefile 사용)**

**올인원 Docker 컨테이너로 간편 실행**

```bash
# 컨테이너 빌드 및 실행
docker-compose up -d

# 또는 재빌드가 필요한 경우
docker-compose down
docker-compose build
docker-compose up -d
```

**✨ GPU 가속 지원**
- RTX 5080 GPU 자동 감지 및 사용
- 임베딩 모델 로딩 시간 대폭 단축
- CUDA 최적화된 배치 처리

**🎯 접속 주소:**
*   **🤖 챗봇 UI**: http://localhost:8011/ui
*   **📡 API 서버**: http://localhost:8011
*   **📚 API 문서**: http://localhost:8011/docs

---

## ✅ **테스트 현황**

**시스템 안정성 확인**

*   **GPU 가속**: RTX 5080을 활용한 임베딩 처리 최적화
*   **올인원 통합**: 단일 컨테이너에서 안정적 동작 확인
*   **포트 통일**: 모든 설정이 8011 포트로 통일
*   **헬스체크**: 모델 로딩 시간을 고려한 안정적 헬스체크

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
