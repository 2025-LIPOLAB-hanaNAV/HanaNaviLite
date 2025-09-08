#!/usr/bin/env python3
"""
Phase 1 완성도 검증 테스트
HanaNaviLite 핵심 인프라 구현 상태를 종합적으로 검증
"""
import sys
import os
import json
import time
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class Phase1Validator:
    def __init__(self):
        self.results = {
            'passed': 0,
            'total': 0,
            'details': {}
        }
    
    def test(self, test_name: str, test_func):
        """테스트 실행 및 결과 기록"""
        self.results['total'] += 1
        print(f"\n🔍 {test_name}")
        print("-" * 50)
        
        try:
            result = test_func()
            if result:
                self.results['passed'] += 1
                self.results['details'][test_name] = 'PASSED'
                print(f"✅ {test_name} - PASSED")
                return True
            else:
                self.results['details'][test_name] = 'FAILED'
                print(f"❌ {test_name} - FAILED")
                return False
        except Exception as e:
            self.results['details'][test_name] = f'ERROR: {str(e)}'
            print(f"💥 {test_name} - ERROR: {e}")
            return False
    
    def test_file_structure(self):
        """파일 구조 검증"""
        required_files = [
            'app/__init__.py',
            'app/main.py',
            'app/core/__init__.py',
            'app/core/config.py',
            'app/core/database.py',
            'app/api/__init__.py',
            'app/api/health.py',
            'requirements.txt',
            '.env.example'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"Missing files: {missing_files}")
            return False
        
        print("✓ All required files exist")
        return True
    
    def test_imports(self):
        """모든 핵심 모듈 import 테스트"""
        try:
            from app.core.config import settings, get_settings
            from app.core.database import DatabaseManager, get_db_manager
            from app.main import app
            from app.api.health import router
            
            print("✓ All core modules imported successfully")
            return True
        except ImportError as e:
            print(f"Import error: {e}")
            return False
    
    def test_config(self):
        """설정 시스템 검증"""
        from app.core.config import get_settings, get_database_path, get_faiss_index_path
        
        settings = get_settings()
        
        # 필수 설정 확인
        required_attrs = [
            'database_url', 'faiss_dimension', 'llm_model',
            'api_host', 'api_port', 'max_memory_gb'
        ]
        
        for attr in required_attrs:
            if not hasattr(settings, attr):
                print(f"Missing config attribute: {attr}")
                return False
        
        # 경로 함수 테스트
        db_path = get_database_path()
        faiss_path = get_faiss_index_path()
        
        print(f"✓ Database path: {db_path}")
        print(f"✓ FAISS path: {faiss_path}")
        print(f"✓ API: {settings.api_host}:{settings.api_port}")
        print(f"✓ Memory limit: {settings.max_memory_gb}GB")
        
        return True
    
    def test_database(self):
        """데이터베이스 시스템 검증"""
        from app.core.database import get_db_manager
        
        db_manager = get_db_manager()
        
        # 헬스체크
        health = db_manager.health_check()
        if health.get('status') != 'healthy':
            print(f"Database health check failed: {health}")
            return False
        
        # 테이블 존재 확인
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 메인 테이블들 확인
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN 
                ('documents', 'documents_fts', 'chunks', 'search_cache', 
                 'system_settings', 'user_sessions', 'query_logs')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['documents', 'documents_fts', 'chunks', 'search_cache']
            missing_tables = [t for t in expected_tables if t not in tables]
            
            if missing_tables:
                print(f"Missing tables: {missing_tables}")
                return False
            
            print(f"✓ Database tables: {len(tables)} created")
            print(f"✓ Database size: {health.get('database_size_mb', 0)} MB")
        
        return True
    
    def test_api_structure(self):
        """API 구조 검증"""
        from app.main import app
        
        # FastAPI 앱 기본 속성 확인
        if not hasattr(app, 'routes'):
            print("FastAPI app missing routes")
            return False
        
        # 라우터 확인
        route_paths = [route.path for route in app.routes if hasattr(route, 'path')]
        
        expected_routes = ['/', '/info']
        for route in expected_routes:
            if route not in route_paths:
                print(f"Missing route: {route}")
                return False
        
        print(f"✓ API routes: {route_paths}")
        return True
    
    def test_health_endpoints(self):
        """헬스체크 엔드포인트 검증"""
        from app.api.health import router
        
        # 라우터의 엔드포인트 확인
        route_paths = [route.path for route in router.routes if hasattr(route, 'path')]
        
        expected_health_routes = [
            '/health', 
            '/health/database', 
            '/health/memory', 
            '/health/system'
        ]
        
        missing_routes = [r for r in expected_health_routes if r not in route_paths]
        if missing_routes:
            print(f"Missing health routes: {missing_routes}")
            return False
        
        print(f"✓ Health endpoints: {len(route_paths)} available")
        return True
    
    def test_dependencies(self):
        """의존성 패키지 확인"""
        import importlib
        
        critical_packages = [
            'fastapi',
            'uvicorn', 
            'pydantic_settings',
            'sqlite3',
            'psutil'
        ]
        
        missing_packages = []
        for package in critical_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"Missing packages: {missing_packages}")
            return False
        
        print(f"✓ All critical packages available")
        return True
    
    def test_environment_config(self):
        """환경설정 파일 검증"""
        env_example_path = Path('.env.example')
        
        if not env_example_path.exists():
            print(".env.example file missing")
            return False
        
        content = env_example_path.read_text()
        
        # 필수 환경변수 확인
        required_vars = [
            'DATABASE_URL',
            'FAISS_DIMENSION', 
            'LLM_MODEL',
            'API_HOST',
            'API_PORT',
            'MAX_MEMORY_GB'
        ]
        
        missing_vars = [var for var in required_vars if var not in content]
        if missing_vars:
            print(f"Missing environment variables: {missing_vars}")
            return False
        
        print(f"✓ Environment template complete")
        return True
    
    def test_memory_safety(self):
        """메모리 안전성 검증"""
        import psutil
        
        # 현재 메모리 사용량
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        
        from app.core.config import get_settings
        settings = get_settings()
        
        if memory_used_gb > settings.max_memory_gb:
            print(f"Current memory usage ({memory_used_gb:.1f}GB) exceeds limit ({settings.max_memory_gb}GB)")
            return False
        
        print(f"✓ Memory usage: {memory_used_gb:.1f}GB / {settings.max_memory_gb}GB limit")
        return True
    
    def generate_report(self):
        """최종 보고서 생성"""
        print("\n" + "="*60)
        print("📊 PHASE 1 VALIDATION REPORT")
        print("="*60)
        
        success_rate = (self.results['passed'] / self.results['total']) * 100
        
        print(f"✅ Tests Passed: {self.results['passed']}/{self.results['total']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("\n🎉 PHASE 1 IMPLEMENTATION COMPLETE!")
            print("🚀 Ready to proceed to Phase 2 (Search Engine)")
        elif success_rate >= 80:
            print("\n⚠️  PHASE 1 MOSTLY COMPLETE")
            print("🔧 Minor issues need to be addressed")
        else:
            print("\n❌ PHASE 1 INCOMPLETE")
            print("🛠️  Major issues need to be resolved")
        
        print("\n📋 Detailed Results:")
        for test_name, result in self.results['details'].items():
            status = "✅" if result == "PASSED" else "❌"
            print(f"  {status} {test_name}: {result}")
        
        return success_rate >= 95  # 95% 이상이면 완료로 간주

def main():
    print("🔬 HanaNaviLite Phase 1 Complete Validation")
    print("=" * 60)
    
    validator = Phase1Validator()
    
    # 모든 검증 테스트 실행
    tests = [
        ("File Structure", validator.test_file_structure),
        ("Module Imports", validator.test_imports),
        ("Configuration System", validator.test_config),
        ("Database System", validator.test_database),
        ("API Structure", validator.test_api_structure),
        ("Health Endpoints", validator.test_health_endpoints),
        ("Dependencies", validator.test_dependencies),
        ("Environment Config", validator.test_environment_config),
        ("Memory Safety", validator.test_memory_safety),
    ]
    
    for test_name, test_func in tests:
        validator.test(test_name, test_func)
    
    # 최종 보고서 생성
    is_complete = validator.generate_report()
    
    return is_complete

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)