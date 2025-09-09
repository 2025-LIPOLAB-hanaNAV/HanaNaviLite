#!/usr/bin/env python3
"""
Smart OCR + Layout Detection Image Parser
Phase 2 구현 - 테이블 인식 가능한 경량 OCR 시스템
"""

import cv2
import numpy as np
import pytesseract
import pandas as pd
import logging
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageEnhance
import json
import os
from pathlib import Path

from .base_parser import BaseFileParser

logger = logging.getLogger(__name__)


class SmartOCRImageParser(BaseFileParser):
    """Smart OCR with Layout Detection for Images"""
    
    SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__()
        self.config = config or {}
        
        # OCR 설정
        self.tesseract_config = self.config.get('tesseract_config', 
            '--oem 3 --psm 6 -l kor+eng')
        
        # 이미지 전처리 설정
        self.enhance_contrast = self.config.get('enhance_contrast', True)
        self.denoise = self.config.get('denoise', True)
        self.dpi = self.config.get('dpi', 300)
        
        # 테이블 감지 설정
        self.table_detection = self.config.get('table_detection', True)
        self.min_table_area = self.config.get('min_table_area', 1000)
        self.table_confidence_threshold = self.config.get('table_confidence_threshold', 0.7)
        
    def can_parse(self, file_path: str) -> bool:
        """이미지 파일 파싱 가능 여부 확인"""
        try:
            path = Path(file_path)
            return path.suffix.lower() in self.SUPPORTED_EXTENSIONS
        except Exception:
            return False
            
    def validate_file(self, file_path: str) -> bool:
        """이미지 파일 유효성 검사"""
        try:
            if not os.path.exists(file_path):
                return False
                
            # PIL로 이미지 로드 시도
            with Image.open(file_path) as img:
                img.verify()
            return True
            
        except Exception as e:
            logger.warning(f"Image validation failed for {file_path}: {e}")
            return False
            
    def get_supported_extensions(self) -> List[str]:
        """지원하는 파일 확장자 목록 반환"""
        return self.SUPPORTED_EXTENSIONS
            
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """이미지 전처리 - OCR 정확도 향상"""
        try:
            # 그레이스케일 변환
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
                
            # 노이즈 제거
            if self.denoise:
                gray = cv2.fastNlMeansDenoising(gray)
                
            # 대비 향상
            if self.enhance_contrast:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                gray = clahe.apply(gray)
                
            # 이진화
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return binary
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image
            
    def detect_table_regions(self, image: np.ndarray) -> List[Dict]:
        """테이블 영역 감지"""
        try:
            # 전처리된 이미지로 작업
            processed = self.preprocess_image(image)
            
            # 수직선 감지
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
            vertical_lines = cv2.morphologyEx(processed, cv2.MORPH_OPEN, vertical_kernel)
            
            # 수평선 감지
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
            horizontal_lines = cv2.morphologyEx(processed, cv2.MORPH_OPEN, horizontal_kernel)
            
            # 테이블 그리드 생성
            table_mask = cv2.addWeighted(vertical_lines, 0.5, horizontal_lines, 0.5, 0.0)
            table_mask = cv2.dilate(table_mask, np.ones((3,3), np.uint8), iterations=2)
            
            # 컨투어 찾기
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            tables = []
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area > self.min_table_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # 테이블 확신도 계산 (간단한 휴리스틱)
                    aspect_ratio = w / h
                    confidence = min(1.0, area / (w * h))  # 채움도
                    
                    if confidence > self.table_confidence_threshold:
                        tables.append({
                            'id': i,
                            'bbox': (x, y, w, h),
                            'area': area,
                            'confidence': confidence,
                            'aspect_ratio': aspect_ratio
                        })
                        
            logger.info(f"Detected {len(tables)} table regions")
            return tables
            
        except Exception as e:
            logger.error(f"Table detection failed: {e}")
            return []
            
    def extract_table_cells(self, image: np.ndarray, table_bbox: Tuple[int, int, int, int]) -> List[List[str]]:
        """테이블 셀 추출 및 OCR"""
        try:
            x, y, w, h = table_bbox
            table_roi = image[y:y+h, x:x+w]
            
            # 테이블 ROI 전처리
            processed_roi = self.preprocess_image(table_roi)
            
            # 간단한 셀 분할 (그리드 기반)
            # 실제 구현에서는 더 정교한 셀 분할 알고리즘 필요
            
            # pytesseract로 테이블 구조 추출 시도
            try:
                # TSV 형태로 OCR 결과 받기
                tsv_data = pytesseract.image_to_data(
                    processed_roi, 
                    config=self.tesseract_config + ' -c preserve_interword_spaces=1',
                    output_type=pytesseract.Output.DICT
                )
                
                # 테이블 구조화
                cells = self._structure_table_from_ocr(tsv_data)
                return cells
                
            except Exception as ocr_error:
                logger.warning(f"Table OCR failed, using fallback: {ocr_error}")
                # 단순 OCR 폴백
                text = pytesseract.image_to_string(processed_roi, config=self.tesseract_config)
                return [[text]] if text.strip() else [[]]
                
        except Exception as e:
            logger.error(f"Cell extraction failed: {e}")
            return [[]]
            
    def _structure_table_from_ocr(self, ocr_data: Dict) -> List[List[str]]:
        """OCR 데이터를 테이블 구조로 변환"""
        try:
            # OCR 결과에서 블록별로 그룹핑
            blocks = {}
            
            for i in range(len(ocr_data['text'])):
                if int(ocr_data['conf'][i]) < 30:  # 낮은 신뢰도 제외
                    continue
                    
                text = ocr_data['text'][i].strip()
                if not text:
                    continue
                    
                block_num = ocr_data['block_num'][i]
                par_num = ocr_data['par_num'][i]
                line_num = ocr_data['line_num'][i]
                word_num = ocr_data['word_num'][i]
                
                key = (block_num, par_num, line_num)
                if key not in blocks:
                    blocks[key] = []
                blocks[key].append(text)
                
            # 블록을 행으로 변환
            rows = []
            for key in sorted(blocks.keys()):
                row_text = ' '.join(blocks[key])
                # 간단한 열 분할 (탭이나 여러 공백 기준)
                cells = [cell.strip() for cell in row_text.replace('\t', '|').split('|')]
                if any(cell for cell in cells):  # 빈 행 제외
                    rows.append(cells)
                    
            return rows
            
        except Exception as e:
            logger.warning(f"Table structuring failed: {e}")
            return [[]]
            
    def extract_text_regions(self, image: np.ndarray, table_regions: List[Dict]) -> str:
        """테이블이 아닌 텍스트 영역 OCR"""
        try:
            # 테이블 영역을 마스크로 제거
            mask = np.ones(image.shape[:2], dtype=np.uint8) * 255
            
            for table in table_regions:
                x, y, w, h = table['bbox']
                # 테이블 영역을 마스크에서 제거 (패딩 추가)
                padding = 10
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(image.shape[1], x + w + padding)
                y2 = min(image.shape[0], y + h + padding)
                mask[y1:y2, x1:x2] = 0
                
            # 마스크된 이미지에서 텍스트 추출
            masked_image = cv2.bitwise_and(image, image, mask=mask)
            processed_image = self.preprocess_image(masked_image)
            
            # OCR 실행
            text = pytesseract.image_to_string(processed_image, config=self.tesseract_config)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Text region extraction failed: {e}")
            return ""
            
    def parse_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """이미지 파일 파싱 메인 함수"""
        try:
            logger.info(f"Starting Smart OCR parsing for: {file_path}")
            
            # 이미지 로드
            image = cv2.imread(file_path)
            if image is None:
                raise ValueError(f"Cannot load image: {file_path}")
                
            result = {
                'file_path': file_path,
                'file_type': 'image',
                'parser_type': 'smart_ocr',
                'success': False,
                'text_content': '',
                'structured_data': [],
                'metadata': {
                    'image_size': image.shape,
                    'tables_found': 0,
                    'text_regions': 0,
                    'processing_method': 'smart_ocr_layout_detection'
                }
            }
            
            tables_data = []
            
            # 테이블 감지 및 처리
            if self.table_detection:
                table_regions = self.detect_table_regions(image)
                result['metadata']['tables_found'] = len(table_regions)
                
                for table in table_regions:
                    try:
                        cells = self.extract_table_cells(image, table['bbox'])
                        if cells and any(any(cell.strip() for cell in row) for row in cells):
                            table_df = pd.DataFrame(cells)
                            tables_data.append({
                                'table_id': table['id'],
                                'bbox': table['bbox'],
                                'confidence': table['confidence'],
                                'data': table_df.to_dict('records'),
                                'raw_data': cells
                            })
                    except Exception as table_error:
                        logger.warning(f"Table {table['id']} processing failed: {table_error}")
                        
            # 텍스트 영역 처리
            text_content = self.extract_text_regions(image, table_regions if self.table_detection else [])
            
            result.update({
                'success': True,
                'text_content': text_content,
                'structured_data': tables_data,
                'metadata': {
                    **result['metadata'],
                    'text_length': len(text_content),
                    'text_regions': 1 if text_content else 0
                }
            })
            
            logger.info(f"Smart OCR parsing completed: {len(text_content)} chars, {len(tables_data)} tables")
            return result
            
        except Exception as e:
            logger.error(f"Image parsing failed for {file_path}: {e}")
            return {
                'file_path': file_path,
                'file_type': 'image', 
                'parser_type': 'smart_ocr',
                'success': False,
                'error': str(e),
                'text_content': '',
                'structured_data': [],
                'metadata': {'error_details': str(e)}
            }


class ImageOCRParserFactory:
    """이미지 OCR 파서 팩토리"""
    
    @staticmethod
    def create_parser(parser_type: str = 'smart_ocr', config: Optional[Dict] = None) -> BaseFileParser:
        """지정된 타입의 이미지 파서 생성"""
        if parser_type == 'smart_ocr':
            return SmartOCRImageParser(config)
        else:
            raise ValueError(f"Unsupported image parser type: {parser_type}")
    
    @staticmethod
    def get_supported_extensions() -> List[str]:
        """지원하는 이미지 확장자 목록"""
        return SmartOCRImageParser.SUPPORTED_EXTENSIONS
    
    @staticmethod
    def get_available_parsers() -> List[str]:
        """사용 가능한 파서 타입 목록"""
        return ['smart_ocr']


# 편의 함수
def parse_image_with_smart_ocr(file_path: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """Smart OCR로 이미지 파싱"""
    parser = SmartOCRImageParser(config)
    return parser.parse_file(file_path)


# 설정 예시
DEFAULT_OCR_CONFIG = {
    'tesseract_config': '--oem 3 --psm 6 -l kor+eng',
    'enhance_contrast': True,
    'denoise': True,
    'dpi': 300,
    'table_detection': True,
    'min_table_area': 1000,
    'table_confidence_threshold': 0.7
}

BANKING_OCR_CONFIG = {
    **DEFAULT_OCR_CONFIG,
    'tesseract_config': '--oem 3 --psm 6 -l kor+eng -c preserve_interword_spaces=1',
    'table_confidence_threshold': 0.6,  # 은행 문서는 테이블이 많으므로 임계치 낮춤
    'min_table_area': 500,  # 작은 표도 감지
}