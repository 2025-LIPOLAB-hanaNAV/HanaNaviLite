#!/usr/bin/env python3
"""
Phase 4 완성도 검증 테스트
React UI & 최적화 기능 통합 테스트
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path

import aiohttp

# 테스트 설정
API_BASE_URL = "http://localhost:8001/api/v1"
UI_BASE_URL = "http://localhost:5175"
TIMEOUT = 30

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_result(self, test_name: str, success: bool, error: str = None):
        if success:
            self.passed += 1
            print(f"✅ {test_name}")
        else:
            self.failed += 1
            self.errors.append(f"{test_name}: {error}")
            print(f"❌ {test_name}: {error}")

    def print_summary(self):
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n{'='*50}")
        print(f"Phase 4 완성도 검증 결과")
        print(f"{'='*50}")
        print(f"✅ 통과: {self.passed}/{total}")
        print(f"❌ 실패: {self.failed}/{total}")
        print(f"📈 성공률: {success_rate:.1f}%")
        
        if self.errors:
            print(f"\n실패한 테스트:")
            for error in self.errors:
                print(f"   - {error}")
        
        print(f"{'='*50}")
        
        if success_rate == 100:
            print("🎉 PHASE 4 IMPLEMENTATION COMPLETE!")
        elif success_rate >= 80:
            print("⚠️  대부분 기능 완성 (일부 개선 필요)")
        else:
            print("❌ 추가 개발 필요")


async def test_api_health_check(session, results):
    """API 서버 헬스체크"""
    try:
        async with session.get(f"{API_BASE_URL}/health", timeout=TIMEOUT) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "healthy":
                    results.add_result("API 서버 헬스체크", True)
                    return data
                else:
                    results.add_result("API 서버 헬스체크", False, f"Status: {data.get('status')}")
            else:
                results.add_result("API 서버 헬스체크", False, f"HTTP {response.status}")
    except Exception as e:
        results.add_result("API 서버 헬스체크", False, str(e))
    return None


async def test_ui_server_access(session, results):
    """UI 서버 접근성 테스트"""
    try:
        async with session.get(UI_BASE_URL, timeout=TIMEOUT) as response:
            if response.status == 200:
                content = await response.text()
                if "HanaNaviLite" in content or "root" in content:
                    results.add_result("UI 서버 접근성", True)
                    return True
                else:
                    results.add_result("UI 서버 접근성", False, "HTML 내용 확인 실패")
            else:
                results.add_result("UI 서버 접근성", False, f"HTTP {response.status}")
    except Exception as e:
        results.add_result("UI 서버 접근성", False, str(e))
    return False


async def test_file_upload_functionality(session, results):
    """파일 업로드 기능 테스트"""
    try:
        # 테스트 파일 생성
        test_content = """# Phase 4 테스트 문서

## 개요
이것은 Phase 4 UI 통합 테스트를 위한 문서입니다.

## 주요 기능
- React UI 통합
- 파일 업로드 기능
- 실시간 상태 모니터링
- RAG 쿼리 처리

## 결론
모든 기능이 정상적으로 동작합니다.
"""
        
        # 임시 파일로 업로드
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(test_content)
            temp_file_path = f.name
        
        try:
            # 파일 업로드
            data = aiohttp.FormData()
            data.add_field('file', open(temp_file_path, 'rb'), filename='phase4_test.md')
            
            async with session.post(f"{API_BASE_URL}/etl/upload", data=data, timeout=TIMEOUT) as response:
                if response.status == 202:
                    result = await response.json()
                    if "successfully" in result.get("message", "").lower():
                        # 처리 대기
                        await asyncio.sleep(3)
                        results.add_result("파일 업로드 기능", True)
                        return True
                    else:
                        results.add_result("파일 업로드 기능", False, f"Upload response: {result}")
                else:
                    results.add_result("파일 업로드 기능", False, f"HTTP {response.status}")
        finally:
            # 임시 파일 정리
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        results.add_result("파일 업로드 기능", False, str(e))
    return False


async def test_rag_query_functionality(session, results):
    """RAG 쿼리 기능 테스트"""
    try:
        # RAG 쿼리 실행
        params = {'query': 'What are the main features of Phase 4?'}
        
        async with session.post(f"{API_BASE_URL}/rag/query", params=params, timeout=TIMEOUT) as response:
            if response.status == 200:
                result = await response.json()
                if result.get("answer") and len(result["answer"]) > 10:
                    results.add_result("RAG 쿼리 기능", True)
                    return result
                else:
                    results.add_result("RAG 쿼리 기능", False, f"빈 답변: {result}")
            else:
                results.add_result("RAG 쿼리 기능", False, f"HTTP {response.status}")
    except Exception as e:
        results.add_result("RAG 쿼리 기능", False, str(e))
    return None


async def test_hybrid_search_functionality(session, results):
    """하이브리드 검색 기능 테스트"""
    try:
        params = {
            'query': 'Phase 4 기능',
            'top_k': 5
        }
        
        async with session.post(f"{API_BASE_URL}/search/hybrid", params=params, timeout=TIMEOUT) as response:
            if response.status == 200:
                result = await response.json()
                if isinstance(result, list) and len(result) > 0:
                    results.add_result("하이브리드 검색 기능", True)
                    return result
                else:
                    results.add_result("하이브리드 검색 기능", False, f"Empty results: {result}")
            else:
                results.add_result("하이브리드 검색 기능", False, f"HTTP {response.status}")
    except Exception as e:
        results.add_result("하이브리드 검색 기능", False, str(e))
    return None


async def test_search_statistics(session, results):
    """검색 엔진 통계 테스트"""
    try:
        async with session.get(f"{API_BASE_URL}/search/stats", timeout=TIMEOUT) as response:
            if response.status == 200:
                stats = await response.json()
                required_keys = ["ir_engine_stats", "vector_engine_stats", "rrf_stats"]
                if all(key in stats for key in required_keys):
                    results.add_result("검색 엔진 통계", True)
                    return stats
                else:
                    results.add_result("검색 엔진 통계", False, f"Missing keys: {required_keys}")
            else:
                results.add_result("검색 엔진 통계", False, f"HTTP {response.status}")
    except Exception as e:
        results.add_result("검색 엔진 통계", False, str(e))
    return None


async def test_system_monitoring(session, results):
    """시스템 모니터링 기능 테스트"""
    try:
        # 시스템 상태 확인
        async with session.get(f"{API_BASE_URL}/health/system", timeout=TIMEOUT) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "healthy":
                    # 메모리 사용량 확인
                    system_info = data.get("system", {})
                    memory_info = system_info.get("memory", {})
                    
                    if memory_info.get("percentage", 0) < 90:  # 90% 미만
                        results.add_result("시스템 모니터링", True)
                        return data
                    else:
                        results.add_result("시스템 모니터링", False, f"메모리 사용량 높음: {memory_info.get('percentage')}%")
                else:
                    results.add_result("시스템 모니터링", False, f"Status: {data.get('status')}")
            else:
                results.add_result("시스템 모니터링", False, f"HTTP {response.status}")
    except Exception as e:
        results.add_result("시스템 모니터링", False, str(e))
    return None


async def test_database_integrity(session, results):
    """데이터베이스 무결성 테스트"""
    try:
        async with session.get(f"{API_BASE_URL}/health", timeout=TIMEOUT) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "healthy":
                    # 문서와 청크 개수 확인
                    details = data.get("details", {})
                    database_info = details.get("database", {})
                    docs_count = database_info.get("documents_count", 0)
                    chunks_count = database_info.get("chunks_count", 0)
                    
                    if docs_count > 0 and chunks_count > 0:
                        results.add_result("데이터베이스 무결성", True)
                        return data
                    else:
                        results.add_result("데이터베이스 무결성", False, f"문서: {docs_count}, 청크: {chunks_count}")
                else:
                    results.add_result("데이터베이스 무결성", False, f"Status: {data.get('status')}")
            else:
                results.add_result("데이터베이스 무결성", False, f"HTTP {response.status}")
    except Exception as e:
        results.add_result("데이터베이스 무결성", False, str(e))
    return None


async def test_cors_configuration(session, results):
    """CORS 설정 테스트"""
    try:
        # Preflight request 테스트
        headers = {
            'Origin': UI_BASE_URL,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        async with session.options(f"{API_BASE_URL}/rag/query", headers=headers, timeout=TIMEOUT) as response:
            if response.status == 200:
                # CORS 헤더 확인
                cors_headers = response.headers.get('Access-Control-Allow-Origin', '')
                if cors_headers == '*' or UI_BASE_URL in cors_headers:
                    results.add_result("CORS 설정", True)
                    return True
                else:
                    results.add_result("CORS 설정", False, f"CORS 헤더: {cors_headers}")
            else:
                results.add_result("CORS 설정", False, f"HTTP {response.status}")
    except Exception as e:
        results.add_result("CORS 설정", False, str(e))
    return False


async def test_performance_baseline(session, results):
    """성능 기준선 테스트"""
    try:
        # 응답 시간 측정
        start_time = time.time()
        
        params = {'query': 'performance test'}
        async with session.post(f"{API_BASE_URL}/rag/query", params=params, timeout=TIMEOUT) as response:
            response_time = time.time() - start_time
            
            if response.status == 200 and response_time < 10:  # 10초 이내
                results.add_result("성능 기준선", True)
                return response_time
            else:
                results.add_result("성능 기준선", False, f"응답시간: {response_time:.2f}초")
                
    except Exception as e:
        results.add_result("성능 기준선", False, str(e))
    return None


async def run_all_tests():
    """모든 테스트 실행"""
    print("🚀 Phase 4 완성도 검증 시작...")
    print("=" * 50)
    
    results = TestResults()
    
    async with aiohttp.ClientSession() as session:
        # 1. 기본 인프라 테스트
        await test_api_health_check(session, results)
        await test_ui_server_access(session, results)
        await test_cors_configuration(session, results)
        
        # 2. 핵심 기능 테스트  
        await test_file_upload_functionality(session, results)
        await test_rag_query_functionality(session, results)
        await test_hybrid_search_functionality(session, results)
        
        # 3. 시스템 품질 테스트
        await test_search_statistics(session, results)
        await test_system_monitoring(session, results)
        await test_database_integrity(session, results)
        await test_performance_baseline(session, results)
    
    # 결과 출력
    results.print_summary()
    
    return results.passed, results.failed


if __name__ == "__main__":
    try:
        passed, failed = asyncio.run(run_all_tests())
        exit(0 if failed == 0 else 1)
    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")
        exit(1)
    except Exception as e:
        print(f"\n테스트 실행 중 오류 발생: {e}")
        exit(1)