# HanaNaviLite

**경량화된 그룹포털 게시판 RAG 챗봇**

32GB RAM 환경에 최적화된 MVP 버전으로, 최소한의 프레임워크로 최대 성능을 달성합니다.

---

## 🎯 **설계 원칙**

1. **최소 의존성**: 5개 핵심 스택으로 완전한 RAG 시스템 구현
2. **메모리 효율**: 32GB 환경에서 안정적 운영 (25GB 이하 사용)
3. **자체 구현 우선**: 핵심 비즈니스 로직은 100% 자체 개발
4. **정확도 우선**: 은행 업무 특성상 응답 정확도를 최우선으로 고려

---

## 🏗️ **아키텍처**

```
[React UI] ──> [FastAPI Core] ──> [Hybrid Search Engine]
                     │                    │
                     │                    ├─> SQLite FTS5 (IR)
                     │                    └─> FAISS (Vector)
                     │
                     ├─> [ETL Pipeline] ──> [File Parser]
                     └─> [LLM Service] ──> [Ollama + Gemma3]
```

### **핵심 스택 (5개)**
- **FastAPI**: 통합 백엔드 API
- **SQLite**: 통합 데이터베이스 (메타데이터 + IR + 캐시)
- **FAISS**: 벡터 검색 엔진
- **Ollama**: LLM 서빙 (Gemma3 12B)
- **React**: 프론트엔드 UI

---

## 🚀 **빠른 시작**

### **1. 환경 요구사항**
- **하드웨어**: 16core CPU, 32GB RAM, A100 80G GPU
- **소프트웨어**: Docker, Docker Compose, Git

### **2. 실행**
```bash
# 레포 클론
git clone <repository-url>
cd HanaNaviLite

# 환경변수 설정
cp .env.example .env

# 서비스 시작
docker-compose up -d

# 모델 다운로드
make pull-model

# 헬스체크
curl http://localhost:8001/health
```

### **3. 접속**
- **챗봇 UI**: http://localhost:3000
- **게시판 UI**: http://localhost:3001
- **API 문서**: http://localhost:8001/docs

---

## 📂 **프로젝트 구조**

```
HanaNaviLite/
├── app/
│   ├── core/              # 통합 FastAPI 서비스
│   ├── search/            # 하이브리드 검색 엔진 (자체 구현)
│   ├── etl/               # ETL 파이프라인
│   ├── parser/            # 파일 파서 (PDF/XLSX/DOCX)
│   ├── llm/               # LLM 서비스
│   └── utils/             # 공용 유틸리티
├── ui/
│   ├── chatbot/           # 챗봇 React UI
│   └── board/             # 게시판 React UI
├── data/                  # SQLite 데이터베이스
├── uploads/               # 업로드 파일 저장소
├── models/                # FAISS 인덱스 저장소
├── docker/                # Docker 설정
└── docs/                  # 개발 문서
```

---

## 🔧 **개발 가이드**

### **개발 환경 설정**
```bash
# Python 가상환경
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 로컬 개발 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### **주요 API 엔드포인트**
- `GET /` - API 루트 정보
- `GET /info` - 시스템 정보
- `GET /api/v1/health` - 종합 헬스체크
- `GET /api/v1/health/database` - 데이터베이스 상태
- `GET /api/v1/health/memory` - 메모리 사용량
- `GET /api/v1/health/system` - 시스템 리소스
- `POST /api/v1/health/cache/cleanup` - 캐시 정리

---

## ✅ **Phase 1 완성 현황**

### **구현된 핵심 인프라**
- ✅ **FastAPI 통합 서비스**: 완전한 웹 API 프레임워크
- ✅ **SQLite 통합 데이터베이스**: FTS5, 메타데이터, 캐시 테이블 완성
- ✅ **설정 관리 시스템**: Pydantic 기반 환경설정
- ✅ **헬스체크 시스템**: 종합 모니터링 API 구현
- ✅ **메모리 최적화**: 25GB 이하 메모리 사용 보장

### **검증 완료 사항**
```bash
# 완성도 검증 테스트 결과
✅ Tests Passed: 9/9
📈 Success Rate: 100.0%
🎉 PHASE 1 IMPLEMENTATION COMPLETE!
```

### **테스트 방법**
```bash
# 기본 기능 테스트
python test_basic.py

# 완성도 검증 테스트
python test_phase1_complete.py

# 헬스체크 테스트
curl http://localhost:8001/api/v1/health
```

---

## 🎨 **자체 구현 하이라이트**

### **1. 하이브리드 검색 엔진**
```python
class HybridSearchEngine:
    """SQLite FTS5 + FAISS 하이브리드 검색"""
    def search(self, query: str) -> List[Dict]:
        # IR 검색 (SQLite FTS5)
        ir_results = self.ir_search(query)
        
        # 벡터 검색 (FAISS)  
        vector_results = self.vector_search(query)
        
        # RRF 융합 (자체 구현)
        return self.rrf_fusion(ir_results, vector_results)
```

### **2. 한국어 텍스트 처리**
- 형태소 분석 기반 키워드 추출
- 쿼리 정규화 및 확장
- 은행 업무 도메인 특화 처리

### **3. 메모리 최적화**
- SQLite 기반 통합 캐싱
- FAISS 인메모리 인덱스 최적화
- 동적 모델 로딩/언로딩

---

## 📊 **성능 목표**

| 지표 | 목표값 | 측정 방법 |
|------|--------|-----------|
| **메모리 사용량** | < 25GB | Docker stats |
| **응답 시간** | < 3초 | API 응답 시간 |
| **정확도** | > 95% | LLM-as-a-Judge |
| **관련성** | > 95% | LLM-as-a-Judge |
| **동시 사용자** | 3명 | 부하 테스트 |

---

## 🔒 **보안 고려사항**

- **PII 정보 마스킹**: 개인정보 자동 검출 및 마스킹
- **내부정보 보호**: 민감 정보 접근 제어
- **API 인증**: JWT 기반 인증 (필요시)
- **감사 로그**: 모든 질의/응답 로깅

---

## 📈 **모니터링**

### **주요 메트릭**
- 메모리/CPU 사용률
- API 응답 시간
- 검색 정확도
- 에러율

### **대시보드**
- Grafana + Prometheus (옵션)
- 내장 헬스체크 엔드포인트

---

## 🚧 **개발 로드맵**

### **Phase 1: 핵심 인프라** ✅ **완료**
- [x] 프로젝트 구조 설계
- [x] FastAPI 통합 서비스
- [x] SQLite 통합 데이터베이스 (FTS5 + 메타데이터 + 캐시)
- [x] 기본 설정 관리 시스템
- [x] 헬스체크 및 모니터링 API
- [x] 메모리 최적화 아키텍처

### **Phase 2: 검색 엔진** (다음 단계)
- [ ] FAISS 벡터 검색 엔진
- [ ] SQLite FTS5 IR 검색 
- [ ] 하이브리드 검색 융합 (RRF)
- [ ] 한국어 텍스트 처리
- [ ] 검색 성능 최적화

### **Phase 3: ETL & LLM** (예정)
- [ ] 파일 파서 통합 (PDF/XLSX/DOCX)
- [ ] ETL 파이프라인 구축
- [ ] Ollama LLM 서비스 연동
- [ ] RAG 파이프라인 완성
- [ ] 답변 품질 향상

### **Phase 4: UI & 최적화** (예정)
- [ ] React UI 포팅 및 통합
- [ ] 성능 최적화 및 튜닝
- [ ] 보안 강화
- [ ] 배포 자동화
- [ ] 사용자 테스트

---

## 📚 **참고 문서**

- [개발 가이드](docs/DEVELOPMENT.md)
- [API 문서](docs/API.md)
- [배포 가이드](docs/DEPLOYMENT.md)
- [트러블슈팅](docs/TROUBLESHOOTING.md)

---

## 👥 **기여자**

- **팀 위자드 2팀 - 하나 내비**
- 기획/PM: 서정빈
- AI 파트: 김진수, 김윤하, 전준휘
- 데이터 파트: 고은혜, 전준휘
- UI/UX: 전준휘, 서정빈
- 인프라: 고은혜, 전준휘

---

## 📄 **라이선스**

이 프로젝트는 내부 사용 목적으로 개발되었습니다.