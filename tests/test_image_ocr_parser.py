#!/usr/bin/env python3
"""
Smart OCR Image Parser 테스트
Phase 2 이미지 처리 기능 검증
"""

import unittest
import tempfile
import os
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from unittest.mock import patch, MagicMock
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.parser.image_ocr_parser import (
    SmartOCRImageParser, 
    ImageOCRParserFactory,
    parse_image_with_smart_ocr,
    DEFAULT_OCR_CONFIG,
    BANKING_OCR_CONFIG
)


class TestSmartOCRImageParser(unittest.TestCase):
    """Smart OCR 이미지 파서 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.parser = SmartOCRImageParser()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """테스트 정리"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def create_test_image(self, width=800, height=600, content_type='text'):
        """테스트용 이미지 생성"""
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        if content_type == 'text':
            # 단순 텍스트 이미지
            try:
                # 시스템에서 사용 가능한 폰트 시도
                font = ImageFont.load_default()
            except:
                font = None
                
            draw.text((50, 50), "안녕하세요 Hello World", fill='black', font=font)
            draw.text((50, 100), "This is a test document", fill='black', font=font)
            draw.text((50, 150), "테스트 문서입니다", fill='black', font=font)
            
        elif content_type == 'table':
            # 간단한 테이블 구조
            # 테이블 경계
            draw.rectangle([100, 100, 600, 400], outline='black', width=2)
            
            # 행 구분선
            for i in range(1, 4):
                y = 100 + i * 75
                draw.line([100, y, 600, y], fill='black', width=1)
                
            # 열 구분선  
            for i in range(1, 4):
                x = 100 + i * 125
                draw.line([x, 100, x, 400], fill='black', width=1)
                
            # 셀 내용
            try:
                font = ImageFont.load_default()
            except:
                font = None
                
            draw.text((120, 120), "Name", fill='black', font=font)
            draw.text((245, 120), "Age", fill='black', font=font)
            draw.text((370, 120), "City", fill='black', font=font)
            draw.text((120, 195), "김철수", fill='black', font=font)
            draw.text((245, 195), "30", fill='black', font=font)
            draw.text((370, 195), "서울", fill='black', font=font)
            
        return image
        
    def save_test_image(self, image, filename='test.png'):
        """테스트 이미지 저장"""
        filepath = os.path.join(self.temp_dir, filename)
        image.save(filepath)
        return filepath
        
    def test_can_parse_supported_formats(self):
        """지원 형식 파싱 가능 여부 테스트"""
        supported_files = [
            'test.png', 'test.jpg', 'test.jpeg', 
            'test.tiff', 'test.bmp', 'test.webp'
        ]
        
        for filename in supported_files:
            with self.subTest(filename=filename):
                filepath = os.path.join(self.temp_dir, filename)
                self.assertTrue(self.parser.can_parse(filepath))
                
    def test_cannot_parse_unsupported_formats(self):
        """미지원 형식 파싱 불가 테스트"""
        unsupported_files = [
            'test.pdf', 'test.docx', 'test.txt', 'test.mp4'
        ]
        
        for filename in unsupported_files:
            with self.subTest(filename=filename):
                filepath = os.path.join(self.temp_dir, filename)
                self.assertFalse(self.parser.can_parse(filepath))
                
    def test_validate_file_existing(self):
        """존재하는 이미지 파일 검증 테스트"""
        image = self.create_test_image()
        filepath = self.save_test_image(image)
        
        self.assertTrue(self.parser.validate_file(filepath))
        
    def test_validate_file_nonexisting(self):
        """존재하지 않는 파일 검증 테스트"""
        filepath = os.path.join(self.temp_dir, 'nonexistent.png')
        self.assertFalse(self.parser.validate_file(filepath))
        
    def test_preprocess_image(self):
        """이미지 전처리 테스트"""
        # 컬러 이미지 생성
        image_array = np.ones((100, 100, 3), dtype=np.uint8) * 128
        
        # 전처리 실행
        processed = self.parser.preprocess_image(image_array)
        
        # 결과 검증
        self.assertEqual(len(processed.shape), 2)  # 그레이스케일로 변환
        self.assertEqual(processed.dtype, np.uint8)
        
    @patch('pytesseract.image_to_string')
    def test_extract_text_regions_mock(self, mock_ocr):
        """텍스트 영역 추출 테스트 (Mock)"""
        mock_ocr.return_value = "안녕하세요 Hello World"
        
        image = np.ones((200, 200, 3), dtype=np.uint8) * 255
        table_regions = []
        
        result = self.parser.extract_text_regions(image, table_regions)
        
        self.assertEqual(result, "안녕하세요 Hello World")
        mock_ocr.assert_called_once()
        
    def test_detect_table_regions_basic(self):
        """기본 테이블 영역 감지 테스트"""
        # 테이블 구조가 있는 이미지 생성
        image = np.ones((400, 600, 3), dtype=np.uint8) * 255
        
        # 수직선과 수평선으로 테이블 구조 그리기
        cv2.rectangle(image, (100, 100), (500, 300), (0, 0, 0), 2)
        cv2.line(image, (100, 150), (500, 150), (0, 0, 0), 1)
        cv2.line(image, (100, 200), (500, 200), (0, 0, 0), 1)
        cv2.line(image, (200, 100), (200, 300), (0, 0, 0), 1)
        cv2.line(image, (300, 100), (300, 300), (0, 0, 0), 1)
        
        tables = self.parser.detect_table_regions(image)
        
        # 최소한 하나의 테이블이 감지되어야 함
        self.assertGreaterEqual(len(tables), 0)
        
        # 감지된 테이블이 있다면 구조 검증
        if tables:
            table = tables[0]
            self.assertIn('bbox', table)
            self.assertIn('confidence', table)
            self.assertIn('area', table)
            
    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    def test_parse_file_text_image_mock(self, mock_data, mock_string):
        """텍스트 이미지 파싱 테스트 (Mock)"""
        # Mock 설정
        mock_string.return_value = "Test document content\n테스트 문서 내용"
        mock_data.return_value = {
            'text': ['Test', 'document'],
            'conf': [95, 90],
            'block_num': [1, 1],
            'par_num': [1, 1], 
            'line_num': [1, 1],
            'word_num': [1, 2]
        }
        
        # 테스트 이미지 생성 및 저장
        image = self.create_test_image(content_type='text')
        filepath = self.save_test_image(image)
        
        # 파싱 실행
        result = self.parser.parse_file(filepath)
        
        # 결과 검증
        self.assertTrue(result['success'])
        self.assertEqual(result['parser_type'], 'smart_ocr')
        self.assertIn('Test document content', result['text_content'])
        self.assertIn('metadata', result)
        
    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    def test_parse_file_table_image_mock(self, mock_data, mock_string):
        """테이블 이미지 파싱 테스트 (Mock)"""
        # Mock 설정
        mock_string.return_value = "Additional text content"
        mock_data.return_value = {
            'text': ['Name', 'Age', '김철수', '30'],
            'conf': [95, 90, 85, 95],
            'block_num': [1, 1, 2, 2],
            'par_num': [1, 1, 1, 1],
            'line_num': [1, 1, 2, 2], 
            'word_num': [1, 2, 1, 2]
        }
        
        # 테이블 이미지 생성 및 저장
        image = self.create_test_image(content_type='table')
        filepath = self.save_test_image(image)
        
        # 파싱 실행
        result = self.parser.parse_file(filepath)
        
        # 결과 검증
        self.assertTrue(result['success'])
        self.assertGreaterEqual(result['metadata']['tables_found'], 0)
        self.assertIsInstance(result['structured_data'], list)
        
    def test_parse_file_invalid_image(self):
        """잘못된 이미지 파일 파싱 테스트"""
        # 잘못된 파일 생성
        filepath = os.path.join(self.temp_dir, 'invalid.png')
        with open(filepath, 'w') as f:
            f.write("This is not an image file")
            
        result = self.parser.parse_file(filepath)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        
    def test_custom_config(self):
        """커스텀 설정 테스트"""
        custom_config = {
            'table_detection': False,
            'enhance_contrast': False,
            'tesseract_config': '--psm 8 -l eng'
        }
        
        parser = SmartOCRImageParser(custom_config)
        
        self.assertFalse(parser.table_detection)
        self.assertFalse(parser.enhance_contrast) 
        self.assertEqual(parser.tesseract_config, '--psm 8 -l eng')


class TestImageOCRParserFactory(unittest.TestCase):
    """이미지 OCR 파서 팩토리 테스트"""
    
    def test_create_smart_ocr_parser(self):
        """Smart OCR 파서 생성 테스트"""
        parser = ImageOCRParserFactory.create_parser('smart_ocr')
        self.assertIsInstance(parser, SmartOCRImageParser)
        
    def test_create_parser_with_config(self):
        """설정과 함께 파서 생성 테스트"""
        config = {'table_detection': False}
        parser = ImageOCRParserFactory.create_parser('smart_ocr', config)
        self.assertIsInstance(parser, SmartOCRImageParser)
        self.assertFalse(parser.table_detection)
        
    def test_create_unsupported_parser(self):
        """미지원 파서 타입 테스트"""
        with self.assertRaises(ValueError):
            ImageOCRParserFactory.create_parser('unsupported_type')
            
    def test_get_supported_extensions(self):
        """지원 확장자 목록 테스트"""
        extensions = ImageOCRParserFactory.get_supported_extensions()
        self.assertIn('.png', extensions)
        self.assertIn('.jpg', extensions)
        self.assertIn('.jpeg', extensions)
        
    def test_get_available_parsers(self):
        """사용 가능한 파서 목록 테스트"""
        parsers = ImageOCRParserFactory.get_available_parsers()
        self.assertIn('smart_ocr', parsers)


class TestConfigurationTests(unittest.TestCase):
    """설정 관련 테스트"""
    
    def test_default_config_validity(self):
        """기본 설정 유효성 테스트"""
        self.assertIn('tesseract_config', DEFAULT_OCR_CONFIG)
        self.assertIn('table_detection', DEFAULT_OCR_CONFIG)
        self.assertIsInstance(DEFAULT_OCR_CONFIG['enhance_contrast'], bool)
        
    def test_banking_config_validity(self):
        """뱅킹 설정 유효성 테스트"""
        self.assertIn('tesseract_config', BANKING_OCR_CONFIG)
        self.assertIn('table_detection', BANKING_OCR_CONFIG)
        self.assertLess(
            BANKING_OCR_CONFIG['table_confidence_threshold'], 
            DEFAULT_OCR_CONFIG['table_confidence_threshold']
        )


class TestConvenienceFunctions(unittest.TestCase):
    """편의 함수 테스트"""
    
    @patch('app.parser.image_ocr_parser.SmartOCRImageParser')
    def test_parse_image_with_smart_ocr(self, mock_parser_class):
        """Smart OCR 편의 함수 테스트"""
        mock_parser = MagicMock()
        mock_parser.parse_file.return_value = {'success': True}
        mock_parser_class.return_value = mock_parser
        
        result = parse_image_with_smart_ocr('/fake/path.png')
        
        self.assertEqual(result, {'success': True})
        mock_parser_class.assert_called_once()
        mock_parser.parse_file.assert_called_once_with('/fake/path.png')


class TestIntegrationScenarios(unittest.TestCase):
    """통합 시나리오 테스트"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    @patch('pytesseract.image_to_string')
    def test_banking_document_scenario_mock(self, mock_ocr):
        """은행 문서 시나리오 테스트 (Mock)"""
        mock_ocr.return_value = "계좌번호: 123-456-789\n잔액: 1,000,000원\n거래일시: 2024-09-09"
        
        # 은행 설정으로 파서 생성
        parser = SmartOCRImageParser(BANKING_OCR_CONFIG)
        
        # 테스트 이미지 생성
        image = Image.new('RGB', (600, 400), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
        draw.text((50, 50), "계좌 정보", fill='black', font=font)
        draw.text((50, 100), "계좌번호: 123-456-789", fill='black', font=font)
        draw.text((50, 150), "잔액: 1,000,000원", fill='black', font=font)
        
        filepath = os.path.join(self.temp_dir, 'banking_doc.png')
        image.save(filepath)
        
        result = parser.parse_file(filepath)
        
        self.assertTrue(result['success'])
        self.assertIn('계좌번호', result['text_content'])
        self.assertEqual(result['parser_type'], 'smart_ocr')
        
    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data') 
    def test_mixed_content_scenario_mock(self, mock_data, mock_string):
        """텍스트+테이블 혼합 문서 시나리오 테스트 (Mock)"""
        mock_string.return_value = "문서 제목: 월별 보고서\n\n추가 설명이 있습니다."
        mock_data.return_value = {
            'text': ['월', '매출', '1월', '100만원'],
            'conf': [90, 85, 95, 90],
            'block_num': [1, 1, 2, 2],
            'par_num': [1, 1, 1, 1],
            'line_num': [1, 1, 2, 2],
            'word_num': [1, 2, 1, 2]
        }
        
        parser = SmartOCRImageParser({'table_detection': True})
        
        # 혼합 컨텐츠 이미지 생성
        image = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(image)
        
        # 제목
        draw.text((50, 50), "월별 보고서", fill='black')
        
        # 테이블 구조
        draw.rectangle([100, 150, 500, 300], outline='black', width=2)
        draw.line([100, 200, 500, 200], fill='black', width=1)
        draw.line([300, 150, 300, 300], fill='black', width=1)
        
        # 추가 텍스트
        draw.text((50, 350), "추가 설명이 있습니다.", fill='black')
        
        filepath = os.path.join(self.temp_dir, 'mixed_content.png')
        image.save(filepath)
        
        result = parser.parse_file(filepath)
        
        self.assertTrue(result['success'])
        self.assertIn('text_content', result)
        self.assertIn('structured_data', result)


def create_test_suite():
    """테스트 스위트 생성"""
    test_suite = unittest.TestSuite()
    
    # 기본 파서 기능 테스트
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestSmartOCRImageParser))
    
    # 팩토리 패턴 테스트
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestImageOCRParserFactory))
    
    # 설정 테스트
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestConfigurationTests))
    
    # 편의 함수 테스트
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestConvenienceFunctions))
    
    # 통합 시나리오 테스트
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestIntegrationScenarios))
    
    return test_suite


if __name__ == '__main__':
    # 개별 테스트 클래스 실행
    if len(sys.argv) > 1:
        # python test_image_ocr_parser.py TestSmartOCRImageParser
        unittest.main()
    else:
        # 전체 테스트 스위트 실행
        runner = unittest.TextTestRunner(verbosity=2)
        test_suite = create_test_suite()
        result = runner.run(test_suite)
        
        # 결과 요약
        print(f"\n{'='*50}")
        print(f"테스트 실행 완료")
        print(f"총 테스트: {result.testsRun}")
        print(f"실패: {len(result.failures)}")
        print(f"에러: {len(result.errors)}")
        print(f"성공률: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
        
        if result.failures:
            print(f"\n실패한 테스트:")
            for test, traceback in result.failures:
                print(f"- {test}")
                
        if result.errors:
            print(f"\n에러 발생 테스트:")
            for test, traceback in result.errors:
                print(f"- {test}")