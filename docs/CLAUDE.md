# Claude Code 작업 지침

HanaNaviLite 프로젝트를 위한 Claude Code 개발 가이드입니다.

---

## 🎯 **프로젝트 목표**

32GB RAM 환경에서 안정적으로 동작하는 경량화된 RAG 챗봇 시스템 구축

**핵심 제약사항:**
- 메모리 사용량 25GB 이하
- 응답 시간 3초 이하  
- 정확도 95% 이상
- 동시 사용자 3명 지원

---

## 🏗️ **구현 우선순위**

### **Phase 1: 핵심 인프라 (1차 작업)**
1. **프로젝트 구조 생성**
   ```
   app/
   ├── core/          # FastAPI 메인 서비스
   ├── search/        # 하이브리드 검색 엔진
   ├── etl/           # ETL 파이프라인  
   ├── llm/           # LLM 서비스
   └── utils/         # 공용 유틸리티
   ```

2. **통합 FastAPI 서비스**
   - 모든 API 엔드포인트 통합
   - SQLite 데이터베이스 연결
   - 기본 헬스체크 구현

3. **SQLite 통합 스키마**
   - 메타데이터 + FTS5 + 캐시 통합
   - 초기 테이블 생성 스크립트
   - 마이그레이션 도구

### **Phase 2: 검색 엔진 (2차 작업)**
1. **FAISS 벡터 검색**
   - 인덱스 생성/관리
   - 벡터 추가/검색 API
   - 메모리 최적화

2. **SQLite FTS5 IR 검색**
   - 한국어 텍스트 처리
   - 고급 쿼리 기능
   - 성능 최적화

3. **하이브리드 검색 융합**
   - RRF 알고리즘 구현
   - 결과 재랭킹
   - 필터링 기능

### **Phase 3: ETL & LLM (3차 작업)**
1. **파일 파서 이전**
   - 기존 코드에서 재활용
   - PDF/XLSX/DOCX 지원
   - 에러 처리 강화

2. **LLM 서비스 통합**
   - Ollama 클라이언트
   - 프롬프트 엔지니어링
   - 스트리밍 응답

---

## 📋 **개발 규칙**

### **1. 코드 품질**
```python
# 타입 힌트 필수
def search_documents(query: str, top_k: int = 10) -> List[SearchResult]:
    """문서 검색 함수
    
    Args:
        query: 검색 쿼리
        top_k: 반환할 결과 수
        
    Returns:
        검색 결과 리스트
    """
    pass

# 에러 처리 필수
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

### **2. 메모리 최적화**
```python
# 제너레이터 사용
def process_large_dataset(data_source):
    for item in data_source:
        yield process_item(item)

# 컨텍스트 매니저 활용
with sqlite3.connect(db_path) as conn:
    cursor = conn.execute(query)
    # 자동으로 연결 해제

# 불필요한 객체 즉시 해제
large_object = create_large_object()
result = process(large_object)
del large_object  # 명시적 해제
```

### **3. 설정 관리**
```python
# app/core/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 데이터베이스
    database_url: str = "sqlite:///data/haanavilite.db"
    
    # FAISS 설정
    faiss_dimension: int = 1024
    faiss_index_path: str = "models/faiss_index"
    
    # LLM 설정
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "gemma3:12b"
    
    # 메모리 제한
    max_memory_gb: int = 25
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 🔄 **기존 코드 재활용 가이드**

### **재활용 가능한 파일들**
원본 레포에서 다음 파일들을 참조하여 재구현:

1. **검색 관련**: `app/search_adapter/hybrid.py`
2. **파서 관련**: `app/parser/` 전체
3. **유틸리티**: `app/utils/` 전체
4. **ETL 로직**: `app/etl-api/` 및 `app/worker/`
5. **LLM 서비스**: `app/rag-api/main.py`

### **수정이 필요한 부분**
1. **Qdrant → FAISS**
   ```python
   # 기존 (Qdrant)
   from qdrant_client import QdrantClient
   client = QdrantClient(host="localhost", port=6333)
   
   # 신규 (FAISS)
   import faiss
   index = faiss.IndexFlatIP(dimension)
   ```

2. **PostgreSQL/Redis → SQLite**
   ```python
   # 기존 (PostgreSQL)
   from sqlalchemy import create_engine
   engine = create_engine("postgresql://...")
   
   # 신규 (SQLite)  
   import sqlite3
   conn = sqlite3.connect("data/haanavilite.db")
   ```

3. **의존성 제거**
   - Dify 관련 코드 모두 제거
   - OpenSearch 관련 코드 제거
   - Redis 캐시 → SQLite 캐시로 변경

---

## 🛠️ **개발 도구 설정**

### **requirements.txt 구성**
```txt
# 웹 프레임워크
fastapi==0.104.1
uvicorn[standard]==0.24.0

# 데이터베이스
sqlite-utils==3.35
sqlalchemy==2.0.23

# 벡터 검색
faiss-cpu==1.7.4  # GPU 버전: faiss-gpu
numpy==1.24.3

# 텍스트 처리
sentence-transformers==2.2.2

# 파일 파싱
PyPDF2==3.0.1
openpyxl==3.1.2
python-docx==1.1.0

# HTTP 클라이언트 (Ollama 통신)
httpx==0.25.2
requests==2.31.0

# 유틸리티
python-multipart==0.0.6
aiofiles==23.2.1
structlog==23.2.0
```

### **개발 환경 requirements-dev.txt**
```txt
# 테스트
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1

# 코드 품질
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1

# 프로파일링
memory-profiler==0.61.0
line-profiler==4.1.1
```

### **.env.example**
```env
# 데이터베이스
DATABASE_URL=sqlite:///data/haanavilite.db

# FAISS 설정
FAISS_DIMENSION=1024
FAISS_INDEX_PATH=models/faiss_index

# LLM 설정
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=gemma3:12b
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.1

# 임베딩 설정
EMBEDDING_MODEL=dragonkue/snowflake-arctic-embed-l-v2.0-ko
EMBEDDING_BATCH_SIZE=32

# 검색 설정
HYBRID_SEARCH_TOP_K=20
RRF_K=60
VECTOR_WEIGHT=0.6
IR_WEIGHT=0.4

# 시스템 설정
LOG_LEVEL=INFO
MAX_MEMORY_GB=25
```

---

## 📝 **구현 체크리스트**

### **Phase 1: 기본 인프라**
- [ ] 프로젝트 구조 생성
- [ ] FastAPI 앱 초기화
- [ ] SQLite 스키마 생성
- [ ] 기본 설정 관리
- [ ] 로깅 시스템 구축
- [ ] 헬스체크 엔드포인트
- [ ] Docker 설정

### **Phase 2: 검색 엔진**
- [ ] FAISS 인덱스 매니저
- [ ] SQLite FTS5 검색기
- [ ] 하이브리드 검색 엔진
- [ ] RRF 융합 알고리즘
- [ ] 한국어 텍스트 처리
- [ ] 검색 API 엔드포인트

### **Phase 3: ETL & LLM**
- [ ] 파일 파서 통합
- [ ] ETL 파이프라인 구축
- [ ] 임베딩 서비스
- [ ] Ollama 클라이언트
- [ ] RAG 파이프라인
- [ ] 답변 생성 API

### **Phase 4: UI & 최적화**
- [ ] React UI 포팅
- [ ] API 통합 테스트
- [ ] 성능 최적화
- [ ] 메모리 사용량 모니터링
- [ ] 문서화 완성

---

## 🚨 **주의사항**

### **메모리 관리**
1. **FAISS 인덱스 크기 모니터링**
   - 인덱스 크기가 메모리의 50%를 넘지 않도록
   - 필요시 IndexIVF 등 압축 인덱스 사용

2. **SQLite 연결 관리**
   - 연결 풀링 사용
   - 장시간 연결 유지 금지
   - WAL 모드로 동시성 향상

3. **임베딩 캐시**
   - 자주 사용되는 임베딩만 메모리에 유지
   - LRU 캐시 구현

### **성능 최적화**
1. **비동기 처리**
   - FastAPI async/await 적극 활용
   - 병렬 검색 처리
   - 논블로킹 I/O

2. **캐싱 전략**
   - 검색 결과 캐싱
   - 임베딩 결과 캐싱
   - API 응답 캐싱

### **에러 처리**
1. **예외 상황 대비**
   - 메모리 부족 상황 처리
   - 모델 로딩 실패 처리
   - 네트워크 오류 처리

2. **폴백 메커니즘**
   - FAISS 실패 시 FTS5만 사용
   - LLM 실패 시 기본 응답 제공

---

## 🔍 **테스트 전략**

### **단위 테스트**
```python
# tests/test_search_engine.py
import pytest
from app.search.hybrid_engine import HybridSearchEngine

@pytest.fixture
def search_engine():
    return HybridSearchEngine()

def test_korean_text_normalization(search_engine):
    query = "안녕하세요! 검색 테스트입니다."
    normalized = search_engine.normalize_korean_text(query)
    assert "안녕하세요" in normalized
    assert "검색" in normalized
    assert "테스트" in normalized

def test_hybrid_search(search_engine):
    results = search_engine.search("테스트 쿼리", top_k=5)
    assert len(results) <= 5
    assert all(hasattr(r, 'score') for r in results)
```

### **통합 테스트**
```python
# tests/test_api_integration.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_search_endpoint():
    response = client.post("/search/hybrid", json={
        "query": "테스트 쿼리",
        "top_k": 5
    })
    assert response.status_code == 200
    assert "results" in response.json()
```

### **성능 테스트**
```python
# tests/test_performance.py
import psutil
import time

def test_memory_usage():
    """메모리 사용량 25GB 이하 확인"""
    process = psutil.Process()
    memory_gb = process.memory_info().rss / (1024**3)
    assert memory_gb < 25.0

def test_response_time():
    """API 응답 시간 3초 이하 확인"""
    start = time.time()
    response = client.post("/rag/query", json={"query": "테스트"})
    elapsed = time.time() - start
    assert elapsed < 3.0
    assert response.status_code == 200
```

---

## 📦 **배포 설정**

### **Dockerfile**
```dockerfile
FROM python:3.11-slim as base

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY app/ ./app/
COPY data/ ./data/
COPY models/ ./models/

# 사용자 생성
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### **docker-compose.yml**
```yaml
version: '3.8'

services:
  haanavilite:
    build: .
    ports:
      - "8001:8001"
    volumes:
      - ./data:/app/data
      - ./models:/app/models
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=sqlite:///app/data/haanavilite.db
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - ollama
    deploy:
      resources:
        limits:
          memory: 8G

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        limits:
          memory: 12G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama_data:
```

---

## 🎯 **성공 기준**

프로젝트 완료 시 다음 기준을 만족해야 합니다:

1. **기능적 요구사항**
   - ✅ 웹훅 기반 문서 수집
   - ✅ PDF/XLSX/DOCX 파싱
   - ✅ 하이브리드 검색 (IR + Vector)
   - ✅ RAG 기반 질의응답
   - ✅ React UI 제공

2. **비기능적 요구사항**
   - ✅ 메모리 사용량 < 25GB
   - ✅ 응답 시간 < 3초
   - ✅ 정확도 > 95%
   - ✅ 동시 사용자 3명 지원

3. **기술적 요구사항**
   - ✅ Docker 컨테이너화
   - ✅ API 문서화 (Swagger)
   - ✅ 테스트 커버리지 > 80%
   - ✅ 코드 품질 검사 통과

이 지침을 따라 단계별로 구현하면 성공적인 HanaNaviLite 시스템을 완성할 수 있습니다.