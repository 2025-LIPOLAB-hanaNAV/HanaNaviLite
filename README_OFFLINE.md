HanaNaviLite 오프라인 번들 사용법

구성
- `docker-compose.offline.yml`: 오프라인 실행용 컴포즈 파일(이미지 참조)
- `images/`: 사전 빌드/프리로드된 이미지 tar.gz
  - `hananavilite-app:offline`
  - `hananavilite-ollama:offline` (사전 pull 모델 포함)
- `load_offline.sh`: 이미지 일괄 로드 스크립트

오프라인 설치 절차
1) 번들 로드
   bash load_offline.sh
2) 서비스 기동
   docker compose -f docker-compose.offline.yml up -d
3) 접속
   - 백엔드/Swagger: http://<host>:8020/docs
   - UI: http://<host>:8020/ui

환경변수
- `docker-compose.offline.yml` 기본값으로 바로 동작합니다.
- 임베딩 모델: 이미지 빌드시 사전 캐시됨 (dragonkue/snowflake-arctic-embed-l-v2.0-ko)
- Ollama 모델: `gemma3:12b-it-qat`, `llama3.1:8b-instruct` 포함 (Dockerfile.ollama 수정 가능)

문제 해결
- 포트 충돌 시 `docker-compose.offline.yml`의 `8020`/`11434` 포트 변경
- PDF 파싱 실패 시: 이미지 내 `poppler-utils` 포함. 여전히 0페이지면 원본 확인 필요
- 최초 임베딩 로딩 지연: 이미지에 캐시 포함됨. 장비 성능에 따라 수초~수십초 발생 가능
