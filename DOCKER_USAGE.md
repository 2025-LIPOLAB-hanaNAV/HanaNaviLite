# HanaNaviLite Docker 사용법 가이드

이 문서는 Docker를 사용하여 HanaNaviLite를 실행하는 방법을 안내합니다. `Makefile`을 사용하는 것을 권장합니다.

---

## 🚀 빠른 시작 (Makefile 사용)

### **사전 준비**
1.  Docker 및 Docker Compose 설치
2.  (선택) NVIDIA GPU 사용 시 [nvidia-docker](https://github.com/NVIDIA/nvidia-docker) 설치
3.  (권장) 로컬에 [Ollama](https://ollama.ai/) 설치 및 실행

### **1. 로컬 Ollama 사용 (권장)**

이 방식은 호스트 머신에 설치된 Ollama를 사용합니다. `docker-compose.yml`의 기본 설정입니다.

```bash
# 1. 로컬 Ollama 서버 실행
ollama serve

# 2. 필요한 LLM 모델 다운로드
make pull-model

# 3. Docker 컨테이너 실행
make docker-up
```

### **2. Ollama 컨테이너 사용**

호스트 머신에 Ollama를 설치하고 싶지 않은 경우, Docker 컨테이너로 Ollama를 함께 실행할 수 있습니다.

```bash
# 1. docker-compose.yml 파일 수정
# OLLAMA_BASE_URL 환경 변수를 아래와 같이 변경합니다.
# - OLLAMA_BASE_URL=http://host-gateway:11435  # 주석 처리
- OLLAMA_BASE_URL=http://ollama:11434      # 주석 해제

# 2. Ollama 프로파일로 Docker 컨테이너 실행 (GPU 권장)
docker-compose --profile ollama-container up -d

# 3. 컨테이너 내에서 LLM 모델 다운로드
make pull-model-container
```

**🎯 접속 정보:**
*   **API 서버**: http://localhost:8011
*   **API 문서**: http://localhost:8011/docs
*   **UI**: `docker-compose.yml`에 UI 서비스가 포함되어 있지 않으므로, 로컬에서 `npm run dev`로 실행하거나 별도 컨테이너로 실행해야 합니다.

---

## 🔧 **주요 Makefile 명령어**

*   `make docker-up`: Docker Compose로 전체 시스템을 시작합니다.
*   `make docker-down`: 시스템을 종료합니다.
*   `make docker-build`: Docker 이미지를 빌드합니다.
*   `make logs`: 모든 컨테이너의 실시간 로그를 확인합니다.
*   `make logs-app`: 애플리케이션 컨테이너의 로그만 확인합니다.
*   `make clean`: 임시 파일과 캐시를 정리합니다.

---

## 🛠️ **트러블슈팅**

### **1. Ollama 연결 실패**
*   **로컬 Ollama 사용 시**: `ollama serve`가 호스트 머신에서 실행 중인지, 방화벽에서 `11435` 포트가 열려 있는지 확인하세요.
*   **Ollama 컨테이너 사용 시**: `make logs-ollama` 명령으로 로그를 확인하고, 모델이 정상적으로 다운로드되었는지 확인하세요.

### **2. 포트 충돌**
`docker-compose.yml` 파일에서 `ports` 설정을 변경하여 다른 포트를 사용하세요.

```yaml
# 예시: 8011 포트가 이미 사용 중인 경우
ports:
  - "8012:8011"
```

### **3. GPU 메모리 부족**
`docker-compose.yml`의 `ollama` 서비스에서 `deploy` 섹션의 리소스 제한을 조정하세요.
