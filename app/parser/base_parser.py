#!/usr/bin/env python3
"""
파일 파서 기본 클래스 및 공통 데이터 구조
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class ParsedDocument:
    """파싱된 문서 정보를 담는 데이터 클래스"""
    
    file_path: str
    file_name: str
    file_type: str
    content: str
    metadata: Dict[str, Any]
    page_count: int = 1
    file_size: int = 0
    
    def __post_init__(self):
        """초기화 후 추가 검증"""
        if not self.file_name and self.file_path:
            self.file_name = os.path.basename(self.file_path)
        
        if not self.file_size and self.file_path and os.path.exists(self.file_path):
            self.file_size = os.path.getsize(self.file_path)


class BaseFileParser(ABC):
    """파일 파서 기본 추상 클래스"""
    
    def __init__(self):
        """기본 초기화"""
        pass
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """파일을 파싱할 수 있는지 확인
        
        Args:
            file_path: 확인할 파일 경로
            
        Returns:
            bool: 파싱 가능 여부
        """
        pass
    
    @abstractmethod
    def parse_file(self, file_path: str, **kwargs) -> ParsedDocument:
        """파일을 파싱하여 텍스트와 메타데이터 추출
        
        Args:
            file_path: 파싱할 파일 경로
            **kwargs: 추가 파싱 옵션
            
        Returns:
            ParsedDocument: 파싱된 문서 정보
            
        Raises:
            Exception: 파싱 실패 시
        """
        pass
    
    @abstractmethod
    def validate_file(self, file_path: str) -> bool:
        """파일 유효성 검사
        
        Args:
            file_path: 검사할 파일 경로
            
        Returns:
            bool: 파일이 유효한지 여부
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """지원하는 파일 확장자 목록 반환
        
        Returns:
            List[str]: 지원하는 확장자 목록
        """
        pass
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """파일 기본 정보 추출
        
        Args:
            file_path: 파일 경로
            
        Returns:
            Dict[str, Any]: 파일 정보
        """
        if not os.path.exists(file_path):
            return {}
        
        stat = os.stat(file_path)
        
        return {
            'file_name': os.path.basename(file_path),
            'file_size': stat.st_size,
            'created_time': stat.st_ctime,
            'modified_time': stat.st_mtime,
            'file_extension': os.path.splitext(file_path)[1].lower()
        }
    
    def is_file_too_large(self, file_path: str, max_size_mb: int = 100) -> bool:
        """파일 크기가 너무 큰지 확인
        
        Args:
            file_path: 파일 경로
            max_size_mb: 최대 허용 크기 (MB)
            
        Returns:
            bool: 파일이 너무 큰지 여부
        """
        if not os.path.exists(file_path):
            return False
        
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        return file_size > max_size_bytes