# HanaNaviLite - 경량화 RAG 챗봇 시스템
# Multi-stage build for optimized production image

# Stage 1: Python dependencies and app
FROM python:3.11-slim as python-base

# 환경변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉터리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ ./app/
COPY version.py .
COPY .env.example .env

# 데이터 디렉터리 생성
RUN mkdir -p data models uploads

# Stage 2: Node.js for React build
FROM node:18-alpine as react-build

WORKDIR /ui
COPY ui/chatbot-react/package*.json ./
RUN npm ci

COPY ui/chatbot-react/ ./
RUN npm run build

# Stage 3: Final production image
FROM python:3.11-slim as production

# 환경변수
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 시스템 패키지 (런타임만)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 환경 복사
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin

# 애플리케이션 복사
COPY --from=python-base /app .

# React 빌드 결과 복사 (Nginx 또는 정적 파일 서빙용)
COPY --from=react-build /ui/dist ./ui/dist

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

# 포트 노출
EXPOSE 8001

# 실행 사용자 생성
RUN useradd -m -u 1000 hananavilite
RUN chown -R hananavilite:hananavilite /app
USER hananavilite

# 실행 명령어
CMD ["python", "-m", "app.main"]