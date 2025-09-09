#!/usr/bin/env python3
"""
HWP 파일 파서
한국어 특화 문서 형식 지원
"""

import os
import logging
from typing import Dict, Any, Optional
import tempfile

from app.parser.base_parser import BaseFileParser, ParsedDocument

logger = logging.getLogger(__name__)


class HWPParser(BaseFileParser):
    """HWP 파일 파서 클래스"""
    
    SUPPORTED_EXTENSIONS = ['.hwp', '.hwpx']
    
    def __init__(self):
        super().__init__()
    
    def can_parse(self, file_path: str) -> bool:
        """HWP 파일 파싱 가능 여부 확인"""
        return any(file_path.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)
    
    def parse_file(self, file_path: str, **kwargs) -> ParsedDocument:
        """HWP 파일을 파싱하여 텍스트 추출
        
        Args:
            file_path: HWP 파일 경로
            **kwargs: 추가 파싱 옵션
            
        Returns:
            ParsedDocument: 파싱된 문서 정보
            
        Raises:
            Exception: 파싱 실패 시
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"HWP file not found: {file_path}")
        
        try:
            # HWP 파일 텍스트 추출
            content = self._extract_text_from_hwp(file_path)
            
            # 메타데이터 추출
            metadata = self._extract_metadata(file_path)
            
            # 문서 정보 생성
            doc = ParsedDocument(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                file_type='hwp',
                content=content,
                metadata=metadata,
                page_count=1,  # HWP는 일반적으로 단일 문서로 처리
                file_size=os.path.getsize(file_path)
            )
            
            logger.info(f"Successfully parsed HWP file: {file_path}")
            logger.info(f"Content length: {len(content)} characters")
            
            return doc
            
        except Exception as e:
            error_msg = f"Failed to parse HWP file {file_path}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def _extract_text_from_hwp(self, file_path: str) -> str:
        """HWP 파일에서 텍스트 추출"""
        try:
            # pyhwp를 사용한 텍스트 추출
            import pyhwp
            from pyhwp.hwp5 import api
            
            # HWP 파일 열기
            with api.open(file_path) as hwp_doc:
                # 모든 텍스트 추출
                text_content = []
                
                # 문서의 모든 섹션 순회
                for section in hwp_doc.bodytext.sections:
                    section_text = self._extract_section_text(section)
                    if section_text:
                        text_content.append(section_text)
                
                content = '\n\n'.join(text_content)
                
                if not content.strip():
                    logger.warning(f"No text content extracted from HWP: {file_path}")
                    return "HWP 문서에서 텍스트를 추출할 수 없습니다."
                
                return content
                
        except ImportError:
            logger.error("pyhwp library not available, trying alternative method")
            return self._extract_text_alternative(file_path)
        except Exception as e:
            logger.error(f"pyhwp parsing failed: {e}, trying alternative method")
            return self._extract_text_alternative(file_path)
    
    def _extract_section_text(self, section) -> str:
        """HWP 섹션에서 텍스트 추출"""
        try:
            text_parts = []
            
            # 단락별로 텍스트 추출
            for paragraph in section.paragraphs:
                para_text = self._extract_paragraph_text(paragraph)
                if para_text:
                    text_parts.append(para_text)
            
            return '\n'.join(text_parts)
            
        except Exception as e:
            logger.warning(f"Failed to extract section text: {e}")
            return ""
    
    def _extract_paragraph_text(self, paragraph) -> str:
        """HWP 단락에서 텍스트 추출"""
        try:
            text_parts = []
            
            # 단락 내 모든 텍스트 요소 추출
            for line in paragraph.linesegments:
                for text_chunk in line.textchunks:
                    if hasattr(text_chunk, 'text'):
                        text_parts.append(text_chunk.text)
            
            return ' '.join(text_parts)
            
        except Exception as e:
            logger.warning(f"Failed to extract paragraph text: {e}")
            return ""
    
    def _extract_text_alternative(self, file_path: str) -> str:
        """대안적인 HWP 텍스트 추출 방법"""
        try:
            # HWP를 임시로 다른 형식으로 변환하여 텍스트 추출
            # 또는 기본적인 바이너리 분석을 통한 텍스트 추출
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 간단한 텍스트 추출 시도 (한국어 인코딩 고려)
            try:
                # UTF-8 시도
                text = content.decode('utf-8', errors='ignore')
                # 의미있는 한국어 텍스트만 추출
                korean_text = self._extract_korean_text(text)
                if korean_text:
                    return korean_text
            except:
                pass
            
            try:
                # EUC-KR 시도
                text = content.decode('euc-kr', errors='ignore')
                korean_text = self._extract_korean_text(text)
                if korean_text:
                    return korean_text
            except:
                pass
            
            # 최후의 수단: 기본 메시지
            logger.warning(f"Could not extract readable text from HWP file: {file_path}")
            return f"HWP 문서 ({os.path.basename(file_path)})가 업로드되었지만 텍스트 추출에 실패했습니다."
            
        except Exception as e:
            logger.error(f"Alternative HWP parsing failed: {e}")
            return f"HWP 문서 파싱 중 오류가 발생했습니다: {str(e)}"
    
    def _extract_korean_text(self, text: str) -> str:
        """텍스트에서 한국어 문장 추출"""
        import re
        
        # 한국어 문자 패턴
        korean_pattern = re.compile(r'[가-힣\s\.,!?;:\-\(\)\[\]{}"\'\n]+')
        korean_matches = korean_pattern.findall(text)
        
        # 의미있는 한국어 문장 필터링
        meaningful_sentences = []
        for match in korean_matches:
            cleaned = match.strip()
            # 최소 길이와 한국어 비율 확인
            if (len(cleaned) >= 10 and 
                len(re.findall(r'[가-힣]', cleaned)) > len(cleaned) * 0.3):
                meaningful_sentences.append(cleaned)
        
        return '\n'.join(meaningful_sentences) if meaningful_sentences else ""
    
    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """HWP 파일 메타데이터 추출"""
        metadata = {
            'file_type': 'hwp',
            'parser': 'hwp_parser',
            'encoding': 'unknown',
        }
        
        try:
            import pyhwp
            from pyhwp.hwp5 import api
            
            with api.open(file_path) as hwp_doc:
                # 문서 정보 추출
                if hasattr(hwp_doc, 'docinfo'):
                    docinfo = hwp_doc.docinfo
                    
                    # 제목 추출
                    if hasattr(docinfo, 'document_properties'):
                        props = docinfo.document_properties
                        if hasattr(props, 'title'):
                            metadata['title'] = props.title
                        if hasattr(props, 'author'):
                            metadata['author'] = props.author
                        if hasattr(props, 'subject'):
                            metadata['subject'] = props.subject
                
                metadata['parsing_method'] = 'pyhwp'
                
        except Exception as e:
            logger.warning(f"Could not extract HWP metadata: {e}")
            metadata['parsing_method'] = 'alternative'
            metadata['error'] = str(e)
        
        return metadata
    
    def validate_file(self, file_path: str) -> bool:
        """HWP 파일 유효성 검사"""
        if not os.path.exists(file_path):
            return False
        
        if not self.can_parse(file_path):
            return False
        
        # 파일 크기 확인 (너무 크면 메모리 문제)
        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:  # 100MB 제한
            logger.warning(f"HWP file too large: {file_size} bytes")
            return False
        
        # 실제 HWP 파일인지 확인 (매직 바이트)
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                # HWP 파일의 매직 바이트 확인
                if header.startswith(b'\xd0\xcf\x11\xe0') or header.startswith(b'HWP'):
                    return True
        except:
            pass
        
        return True  # 확실하지 않으면 시도해보기
    
    def get_supported_extensions(self) -> list:
        """지원하는 파일 확장자 목록 반환"""
        return self.SUPPORTED_EXTENSIONS.copy()


def create_parser() -> HWPParser:
    """HWP 파서 인스턴스 생성"""
    return HWPParser()


# 테스트 함수
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python hwp_parser.py <hwp_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    parser = create_parser()
    
    if not parser.validate_file(file_path):
        print(f"Invalid HWP file: {file_path}")
        sys.exit(1)
    
    try:
        doc = parser.parse_file(file_path)
        print(f"File: {doc.file_name}")
        print(f"Type: {doc.file_type}")
        print(f"Size: {doc.file_size} bytes")
        print(f"Content length: {len(doc.content)} characters")
        print(f"Metadata: {doc.metadata}")
        print("\n--- Content Preview ---")
        print(doc.content[:500] + "..." if len(doc.content) > 500 else doc.content)
        
    except Exception as e:
        print(f"Parsing failed: {e}")
        sys.exit(1)