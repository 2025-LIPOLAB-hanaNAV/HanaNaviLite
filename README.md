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

### **환경 요구사항**
- **최소**: 8GB RAM, 4core CPU
- **권장**: 16GB+ RAM, 8core+ CPU  
- **소프트웨어**: Python 3.11+, Node.js 16+, Docker (컨테이너 사용시)
- **LLM 서버**: Ollama 서버 (포트 11435에서 실행 중)

## 📦 **설치 및 실행 방법**

### **⚡ 추천: 서버 기반 Ollama 환경 (현재 설정)**

현재 프로젝트는 **서버의 포트 11435에서 실행 중인 Ollama**를 사용하도록 설정되어 있습니다.

```bash
# 1. 프로젝트 클론
git clone https://github.com/your-org/HanaNaviLite.git
cd HanaNaviLite

# 2. Python 가상환경 설정
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Python 의존성 설치
pip install -r requirements.txt

# 4. React UI 의존성 설치
cd ui/chatbot-react
npm install
cd ../..

# 5. 백엔드 API 서버 시작 (터미널 1)
python -m app.main

# 6. 프론트엔드 UI 시작 (터미널 2)
cd ui/chatbot-react
npm run dev
```

**🎯 접속 주소:**
- **🤖 챗봇 UI**: http://localhost:5174 ← **여기서 챗봇 사용!**
- **📡 API 서버**: http://localhost:8001
- **📚 API 문서**: http://localhost:8001/docs

### **🔧 서버 Ollama 상태 확인**

```bash
# Ollama 서버 상태 확인
curl http://localhost:11435/

# 사용 가능한 모델 확인
curl http://localhost:11435/api/tags

# 모델 다운로드 (필요시)
curl -X POST http://localhost:11435/api/pull -d '{"name": "gemma3:12b-it-qat"}'
```

## 🐳 **Docker 실행 (컨테이너 환경)**

### **✅ 방법 1: 로컬 Ollama API 사용 (현재 설정 / 추천)**

**현재 서버의 Ollama가 포트 11435에서 실행되는 환경을 위한 설정입니다.**

```bash
# 1. Docker 컨테이너 실행 (로컬 Ollama 11435 포트 사용)
make docker-up
# 또는: docker-compose up -d

# 2. 모델이 없다면 로컬에서 다운로드
make pull-model
# 또는: ollama pull gemma3:12b-it-qat

# 3. 실시간 로그 모니터링
make logs
```

**🎯 접속 주소 (Docker):**
- **🤖 챗봇 UI**: http://localhost:8001/ui
- **📡 API 서버**: http://localhost:8001  
- **📚 API 문서**: http://localhost:8001/docs

### **🔧 방법 2: Ollama 컨테이너 포함 실행 (선택사항)**

**별도 Ollama 서버 없이 모든 것을 컨테이너로 실행:**

```bash
# 1. Ollama 컨테이너와 함께 실행 (GPU 필요)
docker-compose --profile ollama-container up -d

# 2. docker-compose.yml에서 Ollama URL 변경 필요:
# OLLAMA_BASE_URL=http://ollama:11434  # 주석 해제
# # OLLAMA_BASE_URL=http://host-gateway:11435  # 주석 처리

# 3. 컨테이너에서 모델 다운로드
make pull-model-container
# 또는: docker-compose exec ollama ollama pull gemma3:12b-it-qat
```

### **🛠️ 유용한 Docker 명령어**

```bash
# 📊 상태 확인
make logs              # 모든 컨테이너 실시간 로그
make logs-app          # 앱 컨테이너만 로그
docker-compose ps      # 컨테이너 상태 확인

# 🔄 관리
make docker-down       # 시스템 종료
make clean            # 캐시 정리
docker-compose restart hananavilite  # 앱만 재시작

# 🧪 API 테스트
curl -X POST "http://localhost:8001/api/v1/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "안녕하세요"}'

# 📊 헬스체크
curl http://localhost:8001/api/v1/health

# 🌐 UI 접속 테스트
curl http://localhost:8001/ui/
```

---

**📱 챗봇 사용법**

1. **챗봇 UI 접속**: http://localhost:5174 (로컬) / http://localhost:8001/ui (Docker)
2. **문서 업로드**: 우측 사이드바에서 PDF, DOCX, XLSX 파일 업로드
3. **질문하기**: 하단 입력창에서 문서 관련 질문 입력
4. **실시간 답변**: RAG 기반으로 문서에서 정확한 답변 생성

### **🔄 백업: 로컬 Ollama 설정**

서버 Ollama를 사용할 수 없는 경우 로컬에서 실행:

```bash
# 1. Ollama 설치 (Linux/macOS)
curl -fsSL https://ollama.ai/install.sh | sh

# 2. 모델 다운로드 및 서버 시작
ollama pull gemma3:12b-it-qat
ollama serve --host 0.0.0.0 --port 11435

# 3. 설정 파일 확인 (필요시 포트 변경)
# app/core/config.py에서 ollama_base_url 확인
```

### **🐳 Docker 환경 (선택사항)**

```bash
# 1. 프로젝트 클론
git clone https://github.com/your-org/HanaNaviLite.git
cd HanaNaviLite

# 2. 환경 설정
cp .env.example .env

# 3. 전체 시스템 시작 (API + LLM + UI)
make docker-up

# 4. 모델 다운로드 (최초 1회)
make pull-model
```

**접속 주소:**
- 🖥️ **메인 UI**: http://localhost (Nginx)
- 🚀 **개발 UI**: http://localhost:3000 
- 📡 **API 서버**: http://localhost:8001
- 📚 **API 문서**: http://localhost:8001/docs

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

## ✅ **현재 테스트 현황**

### **백엔드 기능 테스트**
- ✅ `test_basic.py`: 기본 기능 테스트 통과
- ✅ `test_phase1_complete.py`: Phase 1 핵심 인프라 테스트 통과
- ✅ `tests/test_phase2_advanced_features.py`: Phase 2 고급 기능 테스트 통과
- ✅ `tests/test_image_ocr_parser.py`: 이미지 OCR 파서 테스트 통과

### **통합 및 UI 관련 테스트**
- ⚠️ `test_phase4_complete.py`: 환경 설정 문제로 인해 테스트 실행 불가 (API 서버 및 특정 Pytest Fixture 필요)

**종합**: 핵심 백엔드 기능은 모두 테스트를 통과했습니다. UI 및 통합 테스트는 별도 환경 설정이 필요합니다.

---

## 🔧 **문제 해결**

### **일반적인 문제 및 해결방법**

#### 1. **Ollama 서버 연결 실패**
```bash
# 서버 상태 확인
curl http://localhost:11435/
# 실패시: Ollama 서버가 실행 중인지 확인

# 로컬 Ollama 대안
ollama serve --host 0.0.0.0 --port 11435
```

#### 2. **OCR/OpenCV 오류 (GUI 환경 없음)**
```bash
# 이미 headless 버전으로 수정됨
pip install opencv-python-headless
```

#### 3. **메모리 부족 오류**
```bash
# 메모리 사용량 확인
curl http://localhost:8001/api/v1/health/memory

# 캐시 정리
curl -X POST http://localhost:8001/api/v1/health/cache/cleanup
```

#### 4. **포트 충돌**
```bash
# 포트 사용 확인
netstat -tulpn | grep :8001
netstat -tulpn | grep :5174
netstat -tulpn | grep :11435

# 다른 포트로 변경 (vite.config.ts 또는 app/core/config.py 수정)
```

#### 5. **React UI 빌드 오류**
```bash
cd ui/chatbot-react
rm -rf node_modules package-lock.json
npm install
npm run dev
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

### **Phase 2: 검색 엔진** ✅ **완료**
- [x] FAISS 벡터 검색 엔진
- [x] SQLite FTS5 IR 검색 
- [x] 하이브리드 검색 융합 (RRF)
- [x] 한국어 텍스트 처리
- [x] 검색 성능 최적화

### **추가된 Phase 2 기능**
- ✅ **이미지 처리 (OCR)**: PDF 및 이미지 첨부 파일 내 텍스트 추출 및 레이아웃 인식
- ✅ **답변 품질 향상**: 답변 신뢰도 시스템 및 다양한 스타일 조정 기능

### **Phase 3: ETL & LLM** ✅ **완료**
- [x] 파일 파서 통합 (PDF/XLSX/DOCX)
- [x] ETL 파이프라인 구축
- [x] Ollama LLM 서비스 연동
- [x] RAG 파이프라인 완성
- [x] 답변 품질 향상

### **Phase 4: UI & 최적화** ✅ **완료**
- [x] React UI 포팅 및 통합
- [x] 성능 최적화 및 튜닝
- [x] CORS 및 통신 최적화
- [x] 실시간 상태 모니터링
- [x] 통합 테스트 케이스 완성

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