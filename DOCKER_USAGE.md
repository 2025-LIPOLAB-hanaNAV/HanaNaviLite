# HanaNaviLite Docker 사용법 가이드

## 개요

HanaNaviLite는 두 가지 방식으로 Ollama를 사용할 수 있습니다:
1. **로컬 서버의 기존 Ollama API 사용** (추천)
2. **Docker 컨테이너로 Ollama 실행**

## 🚀 빠른 시작

### 사전 준비

1. Docker와 Docker Compose 설치
2. NVIDIA GPU 사용시 nvidia-docker 설치 (선택적)

### 방법 1: 로컬 Ollama API 사용 (추천)

#### 1.1 로컬 Ollama 설정

```bash
# 로컬에 Ollama가 설치되어 있다면
ollama serve  # Ollama 서버 시작

# 필요한 모델 다운로드
ollama pull gemma3:12b-it-qat
```

#### 1.2 Docker Compose로 HanaNaviLite 실행

```bash
# 메인 애플리케이션만 실행 (로컬 Ollama 사용)
docker-compose up -d hananavilite redis

# 또는 모든 서비스 실행 (Ollama 컨테이너 제외)
docker-compose up -d
```

### 방법 2: Ollama 컨테이너 사용

#### 2.1 환경변수 설정

```bash
# docker-compose.yml에서 Ollama URL 변경
# 16번째 줄을 주석 처리하고 17번째 줄 주석 해제:
# - OLLAMA_BASE_URL=http://host.docker.internal:11434  # 로컬 Ollama 사용시
- OLLAMA_BASE_URL=http://ollama:11434  # Ollama 컨테이너 사용시
```

#### 2.2 Ollama 컨테이너 포함 실행

```bash
# GPU가 있는 경우
docker-compose --profile ollama-container up -d

# CPU만 사용하는 경우 (docker-compose.yml에서 GPU 설정 제거 후)
docker-compose --profile ollama-container up -d
```

#### 2.3 Ollama 컨테이너에 모델 설치

```bash
# Ollama 컨테이너에 접속
docker exec -it hananavilite-ollama ollama pull gemma3:12b-it-qat
```

## 🔧 설정 옵션

### 환경변수

다음 환경변수를 통해 설정을 변경할 수 있습니다:

```yaml
environment:
  - OLLAMA_BASE_URL=http://localhost:11434       # Ollama 서버 URL
  - LLM_MODEL=gemma3:12b-it-qat                  # 사용할 LLM 모델
  - EMBEDDING_MODEL=dragonkue/snowflake-arctic-embed-l-v2.0-ko  # 임베딩 모델
  - LLM_TEMPERATURE=0.1                          # LLM 온도 (창의성)
  - LLM_MAX_TOKENS=2048                          # 최대 토큰 수
  - DATABASE_URL=sqlite:///data/hananavilite.db  # 데이터베이스 경로
  - LOG_LEVEL=INFO                               # 로그 레벨
```

### 볼륨 마운트

```yaml
volumes:
  - ./data:/app/data        # 데이터베이스 및 인덱스
  - ./models:/app/models    # AI 모델 캐시
  - ./uploads:/app/uploads  # 업로드된 파일
  - ./logs:/app/logs        # 애플리케이션 로그
```

## 📚 상세 사용법

### 1. 개발 환경 설정

```bash
# 개발용 실행 (코드 변경 자동 반영)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 2. 프로덕션 환경 배포

```bash
# 프로덕션 빌드 및 실행
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 3. 로그 확인

```bash
# 전체 로그 확인
docker-compose logs -f

# 특정 서비스 로그 확인
docker-compose logs -f hananavilite
docker-compose logs -f ollama
```

### 4. 상태 확인

```bash
# 서비스 상태 확인
docker-compose ps

# 헬스 체크
curl http://localhost:8001/api/v1/health
```

## 🛠 트러블슈팅

### 자주 발생하는 문제들

#### 1. Ollama 연결 실패

**문제**: `Connection refused to http://localhost:11434`

**해결방법**:
- 로컬 Ollama 사용시: `ollama serve` 실행 확인
- 컨테이너 사용시: `docker-compose logs ollama` 확인

#### 2. 임베딩 모델 다운로드 오류

**문제**: `dragonkue/snowflake-arctic-embed-l-v2.0-ko` 모델 로딩 실패

**해결방법**:
```bash
# 컨테이너 내부에서 수동 다운로드
docker exec -it hananavilite-app python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('dragonkue/snowflake-arctic-embed-l-v2.0-ko')
"
```

#### 3. GPU 메모리 부족

**문제**: CUDA out of memory

**해결방법**:
```yaml
# docker-compose.yml에서 메모리 제한 추가
deploy:
  resources:
    limits:
      memory: 8G
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

#### 4. 포트 충돌

**문제**: Port already in use

**해결방법**:
```yaml
# docker-compose.yml에서 포트 변경
ports:
  - "8002:8001"  # 호스트 포트 변경
```

## 🔍 모니터링

### 1. 시스템 리소스 모니터링

```bash
# 리소스 사용량 확인
docker stats

# 디스크 사용량 확인
docker system df
```

### 2. 애플리케이션 모니터링

```bash
# API 상태 확인
curl -s http://localhost:8001/api/v1/health | jq

# 임베딩 모델 상태 확인
curl -s http://localhost:8001/api/v1/health | jq '.embedding_model'
```

## 🔄 업데이트 및 백업

### 업데이트

```bash
# 최신 코드로 업데이트
git pull
docker-compose build --no-cache
docker-compose up -d
```

### 백업

```bash
# 데이터 백업
tar -czf backup_$(date +%Y%m%d).tar.gz data/

# 복원
tar -xzf backup_YYYYMMDD.tar.gz
```

## 📞 지원

문제가 발생하면:
1. 로그 확인: `docker-compose logs -f`
2. 상태 확인: `docker-compose ps`
3. 헬스체크: `curl http://localhost:8001/api/v1/health`

추가 지원이 필요하면 GitHub Issues를 통해 문의해 주세요.