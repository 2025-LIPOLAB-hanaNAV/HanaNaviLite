# syntax=docker/dockerfile:1.6

# ---------- UI build stage ----------
FROM node:20-bullseye AS ui-builder
WORKDIR /build/ui
COPY ui/chatbot-react/package*.json ./
RUN npm ci --no-audit --no-fund
COPY ui/chatbot-react ./
RUN npm run build

# ---------- Python app stage ----------
FROM python:3.10-slim-bullseye AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

# System dependencies: poppler-utils(pdftotext), tesseract-ocr (for image OCR), and libs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git curl ca-certificates \
        poppler-utils \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt ./
RUN python -m venv "$VIRTUAL_ENV" && . "$VIRTUAL_ENV/bin/activate" && \
    pip install --upgrade pip && \
    pip install -r requirements.txt
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy source
COPY . .

# Copy built UI
COPY --from=ui-builder /build/ui/dist /app/ui/chatbot-react/dist

# Prefetch sentence-transformers embedding model into image (optional)
# Set ARG to allow skipping in low-network environments
ARG PREFETCH_EMBEDDING=1
ENV HF_HOME=/root/.cache/huggingface
RUN if [ "$PREFETCH_EMBEDDING" = "1" ]; then \
      python -c "from sentence_transformers import SentenceTransformer; import os; m=os.environ.get('EMBEDDING_MODEL','dragonkue/snowflake-arctic-embed-l-v2.0-ko'); print('Prefetching embedding model:', m); SentenceTransformer(m)"; \
    fi

# Ensure runtime directories
RUN mkdir -p /app/data /app/uploads /app/models /app/logs && \
    chmod -R 775 /app/data /app/uploads /app/models /app/logs

# Expose API port (default 8020)
ENV API_PORT=8020
EXPOSE 8020

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
