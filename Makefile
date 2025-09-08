# HanaNaviLite Makefile
# 개발 및 배포 자동화 도구

.PHONY: help install dev build test clean docker-build docker-up docker-down pull-model

# 기본 타겟
help:
	@echo "HanaNaviLite v0.1.0 - 사용 가능한 명령어:"
	@echo ""
	@echo "개발 환경:"
	@echo "  install     - Python 의존성 설치"
	@echo "  dev         - 개발 서버 실행 (API + UI)"
	@echo "  test        - 모든 테스트 실행"
	@echo "  lint        - 코드 품질 검사"
	@echo ""
	@echo "Docker 배포:"
	@echo "  docker-build - Docker 이미지 빌드"
	@echo "  docker-up   - Docker Compose로 전체 시스템 시작"
	@echo "  docker-down - Docker Compose 시스템 종료"
	@echo "  pull-model  - Ollama 모델 다운로드"
	@echo ""
	@echo "유지보수:"
	@echo "  clean       - 임시 파일 및 캐시 정리"
	@echo "  backup      - 데이터 백업"
	@echo "  logs        - 실시간 로그 모니터링"

# 개발 환경 설치
install:
	@echo "🔧 Python 환경 설정 중..."
	python -m venv venv
	source venv/bin/activate && pip install -r requirements.txt
	@echo "🔧 Node.js 의존성 설치 중..."
	cd ui/chatbot-react && npm install
	@echo "✅ 설치 완료!"

# 개발 서버 실행
dev:
	@echo "🚀 개발 서버 시작 중..."
	@echo "API 서버: http://localhost:8001"
	@echo "UI 서버: http://localhost:5175"
	@echo "API 문서: http://localhost:8001/docs"
	@echo ""
	@echo "Ctrl+C로 종료하세요."
	source venv/bin/activate && python -m app.main &
	cd ui/chatbot-react && npm run dev

# 테스트 실행
test:
	@echo "🧪 테스트 실행 중..."
	source venv/bin/activate && python test_basic.py
	source venv/bin/activate && python test_phase1_complete.py
	source venv/bin/activate && python test_phase4_complete.py
	@echo "✅ 모든 테스트 통과!"

# 코드 품질 검사
lint:
	@echo "🔍 코드 품질 검사 중..."
	source venv/bin/activate && python -m flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
	@echo "✅ 코드 품질 검사 완료!"

# Docker 이미지 빌드
docker-build:
	@echo "🐳 Docker 이미지 빌드 중..."
	docker-compose build
	@echo "✅ 빌드 완료!"

# Docker 시스템 시작
docker-up:
	@echo "🚀 HanaNaviLite 시스템 시작 중..."
	docker-compose up -d
	@echo "✅ 시스템 시작됨!"
	@echo ""
	@echo "접속 정보:"
	@echo "  - API: http://localhost:8001"
	@echo "  - UI: http://localhost:3000 (개발) 또는 http://localhost (프로덕션)"
	@echo "  - API 문서: http://localhost:8001/docs"
	@echo ""
	@echo "상태 확인: make logs"
	@echo "종료: make docker-down"

# Docker 시스템 종료
docker-down:
	@echo "🛑 시스템 종료 중..."
	docker-compose down
	@echo "✅ 시스템 종료됨!"

# Ollama 모델 다운로드
pull-model:
	@echo "🤖 Ollama 모델 다운로드 중..."
	docker-compose exec ollama ollama pull gemma2:2b
	@echo "✅ 모델 다운로드 완료!"

# 로그 모니터링
logs:
	@echo "📋 실시간 로그 모니터링 (Ctrl+C로 종료):"
	docker-compose logs -f

# 정리 작업
clean:
	@echo "🧹 정리 중..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	docker system prune -f
	@echo "✅ 정리 완료!"

# 데이터 백업
backup:
	@echo "💾 데이터 백업 중..."
	mkdir -p backups
	cp -r data/ backups/data_$(shell date +%Y%m%d_%H%M%S)
	cp -r uploads/ backups/uploads_$(shell date +%Y%m%d_%H%M%S)
	@echo "✅ 백업 완료!"

# 프로덕션 배포
deploy:
	@echo "🚀 프로덕션 배포 중..."
	docker-compose -f docker-compose.yml --profile prod up -d
	@echo "✅ 배포 완료!"

# 개발 환경 리셋
reset:
	@echo "🔄 개발 환경 리셋 중..."
	make docker-down
	make clean
	docker-compose build --no-cache
	@echo "✅ 리셋 완료!"