#!/usr/bin/env python3
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """기본 모듈 import 테스트"""
    try:
        from app.core.config import settings, get_settings
        print("✓ Config import success")
        
        from app.core.database import DatabaseManager, get_db_manager
        print("✓ Database import success")
        
        from app.main import app
        print("✓ Main app import success")
        
        from app.api.health import router
        print("✓ Health API import success")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_database():
    """데이터베이스 기본 기능 테스트"""
    try:
        from app.core.database import get_db_manager
        
        db_manager = get_db_manager()
        health = db_manager.health_check()
        
        if health.get('status') == 'healthy':
            print("✓ Database health check passed")
            print(f"  - Documents: {health.get('documents_count', 0)}")
            print(f"  - Database size: {health.get('database_size_mb', 0)} MB")
            return True
        else:
            print(f"✗ Database health check failed: {health}")
            return False
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_config():
    """설정 파일 테스트"""
    try:
        from app.core.config import get_settings
        
        settings = get_settings()
        print("✓ Settings loaded successfully")
        print(f"  - API Host: {settings.api_host}")
        print(f"  - API Port: {settings.api_port}")
        print(f"  - Database URL: {settings.database_url}")
        print(f"  - Max Memory: {settings.max_memory_gb}GB")
        
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False

def main():
    print("🚀 HanaNaviLite Phase 1 Basic Tests")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Config Tests", test_config), 
        ("Database Tests", test_database)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 1 infrastructure is ready.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)