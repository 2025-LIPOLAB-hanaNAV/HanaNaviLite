# HanaNaviLite

**AI 기반 문서 검색 및 파일 분석 RAG 챗봇**

최신 RAG (Retrieval-Augmented Generation) 기술과 하이브리드 검색을 활용한 고성능 지능형 챗봇 시스템입니다. ChatGPT와 같은 파일 업로드 기반 대화가 가능하며, 문서 관리와 실시간 검색을 제공합니다.

---

## 🎯 **주요 기능**

### **💬 지능형 챗봇**
- **파일 기반 대화**: PDF, DOC, XLSX, 이미지 업로드 후 즉시 질문 가능
- **실시간 처리 상태**: 파일 업로드 → 처리 중 → 완료까지 실시간 피드백
- **세션 히스토리**: 페이지 새로고침해도 대화 내용 유지
- **근거 기반 답변**: 검색된 문서 근거와 함께 신뢰할 수 있는 답변 제공

### **🔍 하이브리드 검색**
- **벡터 검색**: FAISS 기반 의미적 유사도 검색
- **전문 검색**: SQLite FTS5 기반 키워드 검색
- **RRF 융합**: 두 검색 결과를 최적 비율로 결합
- **컨텍스트 인식**: 이전 대화 맥락을 고려한 지능형 검색

### **📄 문서 관리**
- **멀티 포맷 지원**: PDF, DOC/DOCX, XLS/XLSX, TXT, MD, 이미지(OCR)
- **실시간 ETL**: 업로드 즉시 파싱, 청킹, 벡터화 처리
- **문서 현황판**: 등록된 문서 목록, 상태 확인, 재처리/삭제 관리
- **중복 방지**: 동일 문서 자동 감지 및 스킵

---

## 🚀 **빠른 시작**

### **필수 요구사항**
- **Python**: 3.11+
- **Node.js**: 18+
- **메모리**: 16GB+ RAM 권장
- **GPU**: NVIDIA GPU (선택사항, 임베딩 가속화)
- **LLM 서버**: Ollama (로컬 설치 권장)

### **설치 방법**

#### **1. Ollama 설치 및 모델 다운로드**
```bash
# Ollama 설치 (https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# 모델 다운로드 (12B 모델 권장)
ollama pull gemma3:12b-it-qat

# Ollama 서버 시작
ollama serve
```

#### **2. 프로젝트 설치**
```bash
# 저장소 클론
git clone https://github.com/your-org/HanaNaviLite.git
cd HanaNaviLite

# Python 의존성 설치
pip install -r requirements.txt

# 추가 의존성 (PDF 파싱용)
pip install pypdf PyPDF2

# React 의존성 설치
cd ui/chatbot-react
npm install
cd ../..
```

#### **3. 서버 실행**
```bash
# 백엔드 서버 시작 (포트 8020)
uvicorn app.main:app --host 0.0.0.0 --port 8020

# 새 터미널에서 프론트엔드 서버 시작
cd ui/chatbot-react
npm run dev  # http://localhost:3000 또는 3001
```

### **접속 주소**
- **🤖 챗봇 UI**: http://localhost:3001
- **📡 API 서버**: http://localhost:8020
- **📚 API 문서**: http://localhost:8020/docs
- **🗄️ 문서 관리**: http://localhost:3001에서 "Documents" 탭

---

## 💡 **사용법**

### **1. 파일 기반 채팅**
1. 메인 채팅 페이지에서 파일 아이콘 클릭 또는 드래그 앤 드롭
2. PDF, DOC, 이미지 등 지원 파일 업로드
3. "처리 완료" 메시지 확인 후 파일 내용에 대해 질문
4. AI가 파일 내용을 근거로 정확한 답변 제공

### **2. 문서 관리**
1. "Documents" 탭에서 등록된 문서 목록 확인
2. 🔄 재처리 또는 🗑️ 삭제 가능
3. 상태별 필터링 (처리완료/실패/진행중)
4. 문서 상세 정보 확인 (청크 수, 파일 크기 등)

### **3. 다양한 채팅 모드**
- **빠른답**: 즉시 답변 (기본값)
- **정밀검증**: 상세한 근거와 함께 답변
- **요약전용**: 핵심 내용만 간략히 답변

---

## 🛠️ **기술 스택**

### **백엔드**
- **FastAPI**: 고성능 Python 웹 프레임워크
- **SQLite**: 메타데이터 저장 + FTS5 전문 검색
- **FAISS**: GPU 가속 벡터 유사도 검색
- **Sentence-Transformers**: 한국어 임베딩 모델
- **Ollama**: LLM 추론 엔진

### **프론트엔드**
- **React**: 모던 SPA 프레임워크
- **TypeScript**: 타입 안전성
- **Tailwind CSS**: 유틸리티 우선 스타일링
- **Vite**: 고속 번들러

### **파일 처리**
- **PyPDF2/pypdf**: PDF 파싱
- **python-docx**: DOC/DOCX 처리
- **pandas/openpyxl**: Excel 파일 처리
- **pytesseract**: 이미지 OCR (선택사항)

---

## 📁 **프로젝트 구조**

```
HanaNaviLite/
├── app/                          # FastAPI 백엔드
│   ├── api/                      # API 엔드포인트
│   │   ├── chat_files.py         # 채팅 파일 업로드
│   │   ├── etl.py                # 문서 ETL 관리
│   │   └── search.py             # 검색 API
│   ├── conversation/             # 대화 관리
│   │   ├── api.py                # 대화 API
│   │   ├── session_manager.py    # 세션 관리
│   │   └── context_search.py     # 컨텍스트 검색
│   ├── search/                   # 검색 엔진
│   │   ├── hybrid_engine.py      # 하이브리드 검색
│   │   ├── faiss_engine.py       # FAISS 벡터 검색
│   │   └── ir_engine.py          # IR 전문 검색
│   ├── etl/                      # ETL 파이프라인
│   └── parser/                   # 파일 파서들
├── ui/chatbot-react/             # React 프론트엔드
│   ├── src/components/           # UI 컴포넌트
│   │   ├── ChatPage.tsx          # 메인 채팅 페이지
│   │   ├── DocumentManager.tsx   # 문서 관리 페이지
│   │   └── SearchBar.tsx         # 파일 업로드 검색바
│   └── public/                   # 정적 자산
├── data/                         # SQLite 데이터베이스
├── uploads/                      # 업로드된 파일
└── models/                       # FAISS 인덱스
```

---

## 🔧 **설정**

### **환경 변수 (.env)**
```bash
# LLM 설정
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:12b-it-qat

# 임베딩 모델
EMBEDDING_MODEL=dragonkue/snowflake-arctic-embed-l-v2.0-ko

# 데이터베이스
DB_PATH=data/hananavilite.db

# 업로드 설정
UPLOAD_DIR=data/uploads
MAX_FILE_SIZE_MB=50

# FAISS 설정
FAISS_INDEX_PATH=models/faiss_index.bin
FAISS_DIMENSION=1024
```

---

## ✅ **테스트된 기능**

- ✅ **파일 업로드**: PDF, DOC, 이미지 등 다양한 포맷
- ✅ **실시간 ETL**: 파일 → 파싱 → 청킹 → 벡터화
- ✅ **하이브리드 검색**: 벡터 + 키워드 검색 융합
- ✅ **세션 관리**: 대화 히스토리 유지 및 복원
- ✅ **근거 표시**: 검색 결과 기반 답변 근거 제공
- ✅ **문서 관리**: CRUD + 상태 모니터링

---

## 🚨 **알려진 이슈**

- **대용량 파일**: 100MB 이상 파일은 처리 시간이 오래 걸릴 수 있음
- **OCR 의존성**: 이미지 OCR을 위해서는 tesseract 별도 설치 필요
- **GPU 메모리**: 임베딩 모델 로딩 시 4GB+ GPU 메모리 필요

---

## 🤝 **기여하기**

1. Fork 프로젝트
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add AmazingFeature'`)
4. 브랜치 푸시 (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

---

## 📄 **라이선스**

이 프로젝트는 MIT 라이선스 하에 제공됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 👥 **팀 위자드 2팀 - 하나 내비**

- **기획/PM**: 서정빈
- **AI 파트**: 김진수, 김윤하, 전준휘  
- **데이터 파트**: 고은혜, 전준휘
- **UI/UX**: 전준휘, 서정빈
- **인프라**: 고은혜, 전준휘

---

## 📞 **지원**

문제가 발생하거나 질문이 있으시면 [GitHub Issues](https://github.com/your-org/HanaNaviLite/issues)를 통해 문의해 주세요.