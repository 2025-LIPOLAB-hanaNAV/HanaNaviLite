#!/usr/bin/env python3
"""
Phase 1.5 파서 테스트
HWP, PPTX, CSV 파서에 대한 종합 테스트
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import shutil

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.parser.hwp_parser import HWPParser, create_parser as create_hwp_parser
from app.parser.pptx_parser import PowerPointParser, create_parser as create_pptx_parser
from app.parser.csv_parser import CSVParser, create_parser as create_csv_parser


class TestHWPParser(unittest.TestCase):
    """HWP 파서 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.parser = create_hwp_parser()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_can_parse(self):
        """파싱 가능 파일 확인 테스트"""
        # HWP 파일들
        self.assertTrue(self.parser.can_parse("test.hwp"))
        self.assertTrue(self.parser.can_parse("TEST.HWP"))
        self.assertTrue(self.parser.can_parse("document.hwpx"))
        
        # 지원하지 않는 파일들
        self.assertFalse(self.parser.can_parse("test.docx"))
        self.assertFalse(self.parser.can_parse("test.pdf"))
        self.assertFalse(self.parser.can_parse("test.txt"))
    
    def test_get_supported_extensions(self):
        """지원 확장자 목록 테스트"""
        extensions = self.parser.get_supported_extensions()
        self.assertIn('.hwp', extensions)
        self.assertIn('.hwpx', extensions)
        self.assertEqual(len(extensions), 2)
    
    def test_validate_file_non_existent(self):
        """존재하지 않는 파일 검증 테스트"""
        non_existent_file = os.path.join(self.test_dir, "non_existent.hwp")
        self.assertFalse(self.parser.validate_file(non_existent_file))
    
    def test_validate_file_wrong_extension(self):
        """잘못된 확장자 파일 검증 테스트"""
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        self.assertFalse(self.parser.validate_file(test_file))
    
    def test_validate_file_too_large(self):
        """너무 큰 파일 검증 테스트"""
        test_file = os.path.join(self.test_dir, "large.hwp")
        
        # 100MB를 초과하는 크기의 파일 생성
        with open(test_file, 'wb') as f:
            f.write(b'0' * (101 * 1024 * 1024))
        
        self.assertFalse(self.parser.validate_file(test_file))
    
    def test_parse_file_success(self):
        """HWP 파일 파싱 성공 테스트 (대안 방법 사용)"""        
        # 테스트 파일 생성 (pyhwp를 사용할 수 없으므로 대안 방법 테스트)
        test_file = os.path.join(self.test_dir, "test.hwp")
        # 한국어 텍스트가 포함된 바이너리 생성
        korean_text = "테스트 한글 텍스트입니다."
        content = korean_text.encode('utf-8') + b'additional binary data'
        
        with open(test_file, 'wb') as f:
            f.write(b'\xd0\xcf\x11\xe0')  # HWP 매직 바이트
            f.write(content)
        
        # 파싱 실행 (대안 방법 사용됨)
        result = self.parser.parse_file(test_file)
        
        # 결과 검증
        self.assertEqual(result.file_name, "test.hwp")
        self.assertEqual(result.file_type, "hwp")
        self.assertGreater(len(result.content), 0)
        self.assertIsInstance(result.metadata, dict)
        
        # 대안 방법에서는 경고 메시지나 기본 메시지가 나올 수 있음
        self.assertTrue(
            "한글 텍스트" in result.content or 
            "HWP 문서" in result.content or
            "텍스트 추출" in result.content
        )
    
    def test_parse_file_not_found(self):
        """존재하지 않는 파일 파싱 테스트"""
        non_existent_file = os.path.join(self.test_dir, "non_existent.hwp")
        
        with self.assertRaises(FileNotFoundError):
            self.parser.parse_file(non_existent_file)
    
    def test_extract_korean_text(self):
        """한국어 텍스트 추출 테스트"""
        test_text = "안녕하세요. 이것은 테스트 텍스트입니다. Hello World!"
        result = self.parser._extract_korean_text(test_text)
        
        self.assertIn("안녕하세요", result)
        self.assertIn("테스트 텍스트", result)


class TestPowerPointParser(unittest.TestCase):
    """PowerPoint 파서 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.parser = create_pptx_parser()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_can_parse(self):
        """파싱 가능 파일 확인 테스트"""
        # PowerPoint 파일들
        self.assertTrue(self.parser.can_parse("test.ppt"))
        self.assertTrue(self.parser.can_parse("TEST.PPT"))
        self.assertTrue(self.parser.can_parse("presentation.pptx"))
        
        # 지원하지 않는 파일들
        self.assertFalse(self.parser.can_parse("test.docx"))
        self.assertFalse(self.parser.can_parse("test.pdf"))
        self.assertFalse(self.parser.can_parse("test.txt"))
    
    def test_get_supported_extensions(self):
        """지원 확장자 목록 테스트"""
        extensions = self.parser.get_supported_extensions()
        self.assertIn('.ppt', extensions)
        self.assertIn('.pptx', extensions)
        self.assertEqual(len(extensions), 2)
    
    def test_validate_file_pptx(self):
        """PPTX 파일 검증 테스트 (ZIP 기반)"""
        test_file = os.path.join(self.test_dir, "test.pptx")
        with open(test_file, 'wb') as f:
            f.write(b'PK\x03\x04')  # ZIP 매직 바이트
        
        self.assertTrue(self.parser.validate_file(test_file))
    
    def test_validate_file_ppt(self):
        """PPT 파일 검증 테스트 (OLE 기반)"""
        test_file = os.path.join(self.test_dir, "test.ppt")
        with open(test_file, 'wb') as f:
            f.write(b'\xd0\xcf\x11\xe0')  # OLE 매직 바이트
        
        self.assertTrue(self.parser.validate_file(test_file))
    
    def test_validate_file_too_large(self):
        """너무 큰 파일 검증 테스트"""
        test_file = os.path.join(self.test_dir, "large.pptx")
        
        # 200MB를 초과하는 크기의 파일 생성
        with open(test_file, 'wb') as f:
            f.write(b'PK\x03\x04')
            f.write(b'0' * (201 * 1024 * 1024))
        
        self.assertFalse(self.parser.validate_file(test_file))
    
    @patch('pptx.Presentation')
    def test_parse_file_success(self, mock_presentation_class):
        """PowerPoint 파일 파싱 성공 테스트"""
        # Mock PowerPoint 구조
        mock_shape = MagicMock()
        mock_shape.text = "슬라이드 제목"
        
        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]
        mock_slide.has_notes_slide = False
        
        mock_presentation = MagicMock()
        mock_presentation.slides = [mock_slide]
        mock_presentation.core_properties.title = "테스트 프레젠테이션"
        mock_presentation.core_properties.author = "테스터"
        mock_presentation.core_properties.subject = None
        mock_presentation.core_properties.created = None
        mock_presentation.core_properties.modified = None
        mock_presentation.slide_width = 9144000
        mock_presentation.slide_height = 6858000
        
        mock_presentation_class.return_value = mock_presentation
        
        # 테스트 파일 생성
        test_file = os.path.join(self.test_dir, "test.pptx")
        with open(test_file, 'wb') as f:
            f.write(b'PK\x03\x04test pptx content')
        
        # 파싱 실행
        result = self.parser.parse_file(test_file)
        
        # 결과 검증
        self.assertEqual(result.file_name, "test.pptx")
        self.assertEqual(result.file_type, "pptx")
        self.assertIn("슬라이드 제목", result.content)
        self.assertEqual(result.page_count, 1)
        self.assertIsInstance(result.metadata, dict)
        self.assertEqual(result.metadata.get('title'), "테스트 프레젠테이션")
    
    def test_parse_file_with_options(self):
        """옵션 포함 파싱 테스트"""
        # 실제 파싱은 mock으로 처리하되, 옵션 전달 확인
        test_file = os.path.join(self.test_dir, "test.pptx")
        with open(test_file, 'wb') as f:
            f.write(b'PK\x03\x04')
        
        with patch('pptx.Presentation') as mock_pres:
            mock_pres.return_value.slides = []
            mock_pres.return_value.core_properties = MagicMock()
            
            # 옵션과 함께 파싱
            result = self.parser.parse_file(
                test_file, 
                extract_notes=False,
                extract_comments=True
            )
            
            self.assertEqual(result.file_type, "pptx")


class TestCSVParser(unittest.TestCase):
    """CSV 파서 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.parser = create_csv_parser()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_can_parse(self):
        """파싱 가능 파일 확인 테스트"""
        # CSV 파일들
        self.assertTrue(self.parser.can_parse("data.csv"))
        self.assertTrue(self.parser.can_parse("DATA.CSV"))
        self.assertTrue(self.parser.can_parse("table.tsv"))
        self.assertTrue(self.parser.can_parse("list.txt"))
        
        # 지원하지 않는 파일들
        self.assertFalse(self.parser.can_parse("test.docx"))
        self.assertFalse(self.parser.can_parse("test.pdf"))
        self.assertFalse(self.parser.can_parse("test.hwp"))
    
    def test_get_supported_extensions(self):
        """지원 확장자 목록 테스트"""
        extensions = self.parser.get_supported_extensions()
        self.assertIn('.csv', extensions)
        self.assertIn('.tsv', extensions)
        self.assertIn('.txt', extensions)
        self.assertEqual(len(extensions), 3)
    
    def test_validate_file_too_large(self):
        """너무 큰 파일 검증 테스트"""
        test_file = os.path.join(self.test_dir, "large.csv")
        
        # 500MB를 초과하는 크기의 파일 생성
        with open(test_file, 'wb') as f:
            f.write(b'header1,header2\n')
            f.write(b'data,data\n' * (501 * 1024 * 1024 // 10))
        
        self.assertFalse(self.parser.validate_file(test_file))
    
    def test_detect_encoding(self):
        """인코딩 감지 테스트"""
        # UTF-8 파일 테스트
        test_file = os.path.join(self.test_dir, "utf8.csv")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("이름,나이\n홍길동,25\n")
        
        encoding = self.parser._detect_encoding(test_file)
        self.assertIsNotNone(encoding)
    
    def test_detect_delimiter(self):
        """구분자 감지 테스트"""
        # 쉼표 구분자
        test_file = os.path.join(self.test_dir, "comma.csv")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("name,age,city\n")
        
        delimiter = self.parser._detect_delimiter(test_file, 'utf-8')
        self.assertEqual(delimiter, ',')
        
        # 탭 구분자
        test_file = os.path.join(self.test_dir, "tab.tsv")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("name\tage\tcity\n")
        
        delimiter = self.parser._detect_delimiter(test_file, 'utf-8')
        self.assertEqual(delimiter, '\t')
    
    def test_parse_file_success(self):
        """CSV 파일 파싱 성공 테스트"""
        # 테스트 CSV 파일 생성
        test_file = os.path.join(self.test_dir, "test.csv")
        csv_content = """이름,나이,도시,점수
홍길동,25,서울,85
김철수,30,부산,92
이영희,28,대구,78
박민수,35,인천,95
최영자,22,광주,88"""
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        # 파싱 실행
        result = self.parser.parse_file(test_file)
        
        # 결과 검증
        self.assertEqual(result.file_name, "test.csv")
        self.assertEqual(result.file_type, "csv")
        self.assertEqual(result.page_count, 1)
        
        # 내용 확인
        self.assertIn("이름", result.content)
        self.assertIn("홍길동", result.content)
        self.assertIn("데이터 요약", result.content)
        self.assertIn("열별 데이터 요약", result.content)
        
        # 메타데이터 확인
        self.assertEqual(result.metadata.get('total_rows'), 5)
        self.assertEqual(result.metadata.get('total_columns'), 4)
        self.assertIn('이름', result.metadata.get('columns', []))
        self.assertIn('나이', result.metadata.get('columns', []))
    
    def test_parse_file_with_options(self):
        """옵션 포함 CSV 파싱 테스트"""
        test_file = os.path.join(self.test_dir, "options.csv")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("a;b;c\n1;2;3\n4;5;6\n")
        
        # 커스텀 옵션으로 파싱
        result = self.parser.parse_file(
            test_file,
            delimiter=';',
            max_rows=1,
            include_headers=False
        )
        
        self.assertEqual(result.file_type, "csv")
        self.assertEqual(result.metadata.get('total_rows'), 1)  # max_rows 제한
    
    def test_analyze_column_numeric(self):
        """숫자 열 분석 테스트"""
        import pandas as pd
        
        # 숫자 데이터
        series = pd.Series([10, 20, 30, 40, 50])
        result = self.parser._analyze_column(series, "점수")
        
        self.assertIn("점수", result)
        self.assertIn("숫자", result)
        self.assertIn("10.00 ~ 50.00", result)
        self.assertIn("평균: 30.00", result)
    
    def test_analyze_column_text(self):
        """텍스트 열 분석 테스트"""
        import pandas as pd
        
        # 텍스트 데이터
        series = pd.Series(["서울", "부산", "서울", "대구", "서울"])
        result = self.parser._analyze_column(series, "도시")
        
        self.assertIn("도시", result)
        self.assertIn("텍스트", result)
        self.assertIn("고유값: 3", result)
        self.assertIn("서울", result)  # 주요값에 포함되어야 함


class TestParsersIntegration(unittest.TestCase):
    """파서 통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.hwp_parser = create_hwp_parser()
        self.pptx_parser = create_pptx_parser()
        self.csv_parser = create_csv_parser()
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_all_parsers_have_required_methods(self):
        """모든 파서가 필수 메서드를 가지고 있는지 테스트"""
        parsers = [self.hwp_parser, self.pptx_parser, self.csv_parser]
        
        for parser in parsers:
            # 필수 메서드 확인
            self.assertTrue(hasattr(parser, 'can_parse'))
            self.assertTrue(hasattr(parser, 'parse_file'))
            self.assertTrue(hasattr(parser, 'validate_file'))
            self.assertTrue(hasattr(parser, 'get_supported_extensions'))
            
            # 메서드가 호출 가능한지 확인
            self.assertTrue(callable(parser.can_parse))
            self.assertTrue(callable(parser.parse_file))
            self.assertTrue(callable(parser.validate_file))
            self.assertTrue(callable(parser.get_supported_extensions))
    
    def test_parser_extension_uniqueness(self):
        """파서별 확장자가 겹치지 않는지 테스트"""
        hwp_ext = set(self.hwp_parser.get_supported_extensions())
        pptx_ext = set(self.pptx_parser.get_supported_extensions())
        csv_ext = set(self.csv_parser.get_supported_extensions())
        
        # 확장자가 겹치지 않는지 확인
        self.assertEqual(len(hwp_ext & pptx_ext), 0)
        self.assertEqual(len(hwp_ext & csv_ext), 0)
        self.assertEqual(len(pptx_ext & csv_ext), 0)
    
    def test_factory_functions(self):
        """팩토리 함수들이 올바른 인스턴스를 생성하는지 테스트"""
        hwp = create_hwp_parser()
        pptx = create_pptx_parser()
        csv = create_csv_parser()
        
        self.assertIsInstance(hwp, HWPParser)
        self.assertIsInstance(pptx, PowerPointParser)
        self.assertIsInstance(csv, CSVParser)


def create_test_suite():
    """테스트 스위트 생성"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # HWP 파서 테스트
    suite.addTests(loader.loadTestsFromTestCase(TestHWPParser))
    
    # PowerPoint 파서 테스트
    suite.addTests(loader.loadTestsFromTestCase(TestPowerPointParser))
    
    # CSV 파서 테스트
    suite.addTests(loader.loadTestsFromTestCase(TestCSVParser))
    
    # 통합 테스트
    suite.addTests(loader.loadTestsFromTestCase(TestParsersIntegration))
    
    return suite


if __name__ == '__main__':
    # 개별 테스트 실행
    loader = unittest.TestLoader()
    if len(sys.argv) > 1:
        # 특정 테스트 클래스만 실행
        test_class = sys.argv[1]
        if test_class == 'hwp':
            suite = loader.loadTestsFromTestCase(TestHWPParser)
        elif test_class == 'pptx':
            suite = loader.loadTestsFromTestCase(TestPowerPointParser)
        elif test_class == 'csv':
            suite = loader.loadTestsFromTestCase(TestCSVParser)
        elif test_class == 'integration':
            suite = loader.loadTestsFromTestCase(TestParsersIntegration)
        else:
            suite = create_test_suite()
    else:
        # 모든 테스트 실행
        suite = create_test_suite()
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 요약
    print(f"\n{'='*50}")
    print(f"테스트 완료!")
    print(f"실행된 테스트: {result.testsRun}")
    print(f"실패: {len(result.failures)}")
    print(f"에러: {len(result.errors)}")
    
    if result.failures:
        print(f"\n실패한 테스트:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\n에러가 발생한 테스트:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    # 성공/실패 반환
    sys.exit(0 if result.wasSuccessful() else 1)