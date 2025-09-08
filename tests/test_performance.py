import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import psutil
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_memory_usage():
    """메모리 사용량 25GB 이하 확인"""
    process = psutil.Process()
    memory_gb = process.memory_info().rss / (1024**3)
    assert memory_gb < 25.0

@pytest.mark.asyncio
async def test_response_time():
    """API 응답 시간 3초 이하 확인"""
    start = time.time()
    response = client.post("/api/v1/rag/query", params={"query": "테스트 질의"})
    elapsed = time.time() - start
    assert elapsed < 3.0
    assert response.status_code == 200