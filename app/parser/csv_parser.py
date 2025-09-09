#!/usr/bin/env python3
"""
CSV 파일 파서
구조화된 데이터 파일 지원
"""

import os
import logging
from typing import Dict, Any, List, Optional
import io

import pandas as pd

from app.parser.base_parser import BaseFileParser, ParsedDocument

logger = logging.getLogger(__name__)


class CSVParser(BaseFileParser):
    """CSV 파일 파서 클래스"""
    
    SUPPORTED_EXTENSIONS = ['.csv', '.tsv', '.txt']
    
    def __init__(self):
        super().__init__()
    
    def can_parse(self, file_path: str) -> bool:
        """CSV 파일 파싱 가능 여부 확인"""
        return any(file_path.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS)
    
    def parse_file(self, file_path: str, **kwargs) -> ParsedDocument:
        """CSV 파일을 파싱하여 텍스트 추출
        
        Args:
            file_path: CSV 파일 경로
            **kwargs: 추가 파싱 옵션
                - encoding: 파일 인코딩 (기본값: 'utf-8')
                - delimiter: 구분자 (기본값: auto-detect)
                - max_rows: 최대 처리 행 수 (기본값: 10000)
                - include_headers: 헤더 포함 여부 (기본값: True)
                
        Returns:
            ParsedDocument: 파싱된 문서 정보
            
        Raises:
            Exception: 파싱 실패 시
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        try:
            # 옵션 설정
            encoding = kwargs.get('encoding', 'utf-8')
            delimiter = kwargs.get('delimiter', None)  # auto-detect
            max_rows = kwargs.get('max_rows', 10000)
            include_headers = kwargs.get('include_headers', True)
            
            # CSV 파일 텍스트 추출
            content, metadata_info = self._extract_text_from_csv(
                file_path, encoding, delimiter, max_rows, include_headers
            )
            
            # 메타데이터 추출
            metadata = self._extract_metadata(file_path, metadata_info)
            
            # 문서 정보 생성
            doc = ParsedDocument(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                file_type='csv',
                content=content,
                metadata=metadata,
                page_count=1,  # CSV는 단일 시트로 처리
                file_size=os.path.getsize(file_path)
            )
            
            logger.info(f"Successfully parsed CSV file: {file_path}")
            logger.info(f"Rows: {metadata_info['total_rows']}, Content length: {len(content)} characters")
            
            return doc
            
        except Exception as e:
            error_msg = f"Failed to parse CSV file {file_path}: {e}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def _extract_text_from_csv(self, file_path: str, encoding: str, delimiter: Optional[str],
                              max_rows: int, include_headers: bool) -> tuple[str, Dict[str, Any]]:
        """CSV 파일에서 텍스트 추출"""
        try:
            # 인코딩 자동 감지
            if encoding == 'auto':
                encoding = self._detect_encoding(file_path)
            
            # 구분자 자동 감지
            if delimiter is None:
                delimiter = self._detect_delimiter(file_path, encoding)
            
            # CSV 파일 읽기
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    delimiter=delimiter,
                    nrows=max_rows,
                    na_values=['', 'N/A', 'NULL', 'null', 'None'],
                    keep_default_na=False
                )
            except UnicodeDecodeError:
                # 인코딩 실패 시 다른 인코딩 시도
                for alt_encoding in ['cp949', 'euc-kr', 'latin-1']:
                    try:
                        df = pd.read_csv(
                            file_path,
                            encoding=alt_encoding,
                            delimiter=delimiter,
                            nrows=max_rows,
                            na_values=['', 'N/A', 'NULL', 'null', 'None'],
                            keep_default_na=False
                        )
                        encoding = alt_encoding
                        break
                    except:
                        continue
                else:
                    raise Exception("모든 인코딩 시도 실패")
            
            # 데이터 정보 수집
            total_rows, total_cols = df.shape
            columns = df.columns.tolist()
            
            # 텍스트 변환
            content_parts = []
            
            # 헤더 포함
            if include_headers and columns:
                content_parts.append("=== 열 정보 ===")
                for i, col in enumerate(columns, 1):
                    content_parts.append(f"{i}. {col}")
                content_parts.append("")
            
            # 데이터 요약 정보
            content_parts.append("=== 데이터 요약 ===")
            content_parts.append(f"총 행 수: {total_rows:,}")
            content_parts.append(f"총 열 수: {total_cols}")
            content_parts.append("")
            
            # 각 열별 데이터 요약
            content_parts.append("=== 열별 데이터 요약 ===")
            for col in columns:
                col_summary = self._analyze_column(df[col], col)
                content_parts.append(col_summary)
            
            content_parts.append("")
            
            # 실제 데이터 샘플 (처음 몇 행)
            sample_size = min(10, len(df))
            if sample_size > 0:
                content_parts.append(f"=== 데이터 샘플 (처음 {sample_size}행) ===")
                
                # 테이블 형태로 변환
                sample_df = df.head(sample_size)
                table_text = self._dataframe_to_text(sample_df)
                content_parts.append(table_text)
            
            content = '\n'.join(content_parts)
            
            # 메타데이터 정보
            metadata_info = {
                'total_rows': total_rows,
                'total_cols': total_cols,
                'columns': columns,
                'encoding': encoding,
                'delimiter': delimiter,
                'sample_size': sample_size
            }
            
            return content, metadata_info
            
        except Exception as e:
            logger.error(f"CSV parsing failed: {e}")
            raise Exception(f"CSV 파싱 중 오류 발생: {str(e)}")
    
    def _detect_encoding(self, file_path: str) -> str:
        """파일 인코딩 자동 감지"""
        try:
            import chardet
            
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # 처음 10KB만 읽어서 감지
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except ImportError:
            # chardet 없으면 일반적인 인코딩들 시도
            for encoding in ['utf-8', 'cp949', 'euc-kr']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(1000)  # 일부만 읽어서 테스트
                        return encoding
                except:
                    continue
            return 'utf-8'  # 기본값
        except Exception:
            return 'utf-8'  # 기본값
    
    def _detect_delimiter(self, file_path: str, encoding: str) -> str:
        """구분자 자동 감지"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                first_line = f.readline()
                
            # 일반적인 구분자들 확인
            delimiters = [',', '\t', ';', '|', ':']
            delimiter_counts = {}
            
            for delimiter in delimiters:
                count = first_line.count(delimiter)
                if count > 0:
                    delimiter_counts[delimiter] = count
            
            if delimiter_counts:
                # 가장 많이 나타나는 구분자 선택
                return max(delimiter_counts, key=delimiter_counts.get)
            else:
                return ','  # 기본값
                
        except Exception:
            return ','  # 기본값
    
    def _analyze_column(self, series: pd.Series, col_name: str) -> str:
        """열 데이터 분석"""
        try:
            analysis = [f"[{col_name}]"]
            
            # 기본 정보
            total_count = len(series)
            non_null_count = series.count()
            null_count = total_count - non_null_count
            
            analysis.append(f"  - 총 값: {total_count:,}")
            analysis.append(f"  - 유효값: {non_null_count:,}")
            if null_count > 0:
                analysis.append(f"  - 빈값: {null_count:,}")
            
            # 데이터 타입 추정
            if pd.api.types.is_numeric_dtype(series):
                analysis.append(f"  - 타입: 숫자")
                if non_null_count > 0:
                    analysis.append(f"  - 범위: {series.min():.2f} ~ {series.max():.2f}")
                    analysis.append(f"  - 평균: {series.mean():.2f}")
            elif pd.api.types.is_datetime64_any_dtype(series):
                analysis.append(f"  - 타입: 날짜/시간")
                if non_null_count > 0:
                    analysis.append(f"  - 범위: {series.min()} ~ {series.max()}")
            else:
                analysis.append(f"  - 타입: 텍스트")
                
                # 고유값 개수
                unique_count = series.nunique()
                analysis.append(f"  - 고유값: {unique_count:,}")
                
                # 상위 값들 (5개까지)
                if unique_count > 0:
                    top_values = series.value_counts().head(5)
                    analysis.append("  - 주요값:")
                    for value, count in top_values.items():
                        percentage = (count / non_null_count) * 100
                        analysis.append(f"    '{value}': {count}회 ({percentage:.1f}%)")
            
            return '\n'.join(analysis)
            
        except Exception as e:
            return f"[{col_name}] - 분석 실패: {str(e)}"
    
    def _dataframe_to_text(self, df: pd.DataFrame) -> str:
        """DataFrame을 텍스트 테이블로 변환"""
        try:
            # pandas의 to_string 사용하여 테이블 형태로 변환
            return df.to_string(index=False, max_colwidth=50)
        except Exception as e:
            logger.warning(f"Failed to convert DataFrame to text: {e}")
            return "데이터 샘플 표시 실패"
    
    def _extract_metadata(self, file_path: str, metadata_info: Dict[str, Any]) -> Dict[str, Any]:
        """CSV 파일 메타데이터 추출"""
        metadata = {
            'file_type': 'csv',
            'parser': 'csv_parser',
            'total_rows': metadata_info.get('total_rows', 0),
            'total_columns': metadata_info.get('total_cols', 0),
            'encoding': metadata_info.get('encoding', 'unknown'),
            'delimiter': metadata_info.get('delimiter', ','),
            'columns': metadata_info.get('columns', []),
        }
        
        try:
            # 파일 크기 정보
            file_size = os.path.getsize(file_path)
            metadata['file_size_mb'] = round(file_size / (1024 * 1024), 2)
            
            # 추가 파일 정보
            metadata['sample_rows'] = metadata_info.get('sample_size', 0)
            
        except Exception as e:
            logger.warning(f"Could not extract CSV metadata: {e}")
            metadata['error'] = str(e)
        
        return metadata
    
    def validate_file(self, file_path: str) -> bool:
        """CSV 파일 유효성 검사"""
        if not os.path.exists(file_path):
            return False
        
        if not self.can_parse(file_path):
            return False
        
        # 파일 크기 확인 (너무 크면 메모리 문제)
        file_size = os.path.getsize(file_path)
        if file_size > 500 * 1024 * 1024:  # 500MB 제한
            logger.warning(f"CSV file too large: {file_size} bytes")
            return False
        
        # 실제 CSV 파일인지 확인 (첫 줄 읽기 시도)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                # 첫 줄이 있고, 적절한 길이인지 확인
                if first_line and len(first_line.strip()) > 0:
                    return True
        except:
            pass
        
        return True  # 확실하지 않으면 시도해보기
    
    def get_supported_extensions(self) -> List[str]:
        """지원하는 파일 확장자 목록 반환"""
        return self.SUPPORTED_EXTENSIONS.copy()


def create_parser() -> CSVParser:
    """CSV 파서 인스턴스 생성"""
    return CSVParser()


# 테스트 함수
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python csv_parser.py <csv_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    parser = create_parser()
    
    if not parser.validate_file(file_path):
        print(f"Invalid CSV file: {file_path}")
        sys.exit(1)
    
    try:
        doc = parser.parse_file(file_path)
        print(f"File: {doc.file_name}")
        print(f"Type: {doc.file_type}")
        print(f"Size: {doc.file_size} bytes")
        print(f"Rows: {doc.metadata.get('total_rows', 'Unknown')}")
        print(f"Columns: {doc.metadata.get('total_columns', 'Unknown')}")
        print(f"Content length: {len(doc.content)} characters")
        print(f"Metadata: {doc.metadata}")
        print("\n--- Content Preview ---")
        print(doc.content[:1500] + "..." if len(doc.content) > 1500 else doc.content)
        
    except Exception as e:
        print(f"Parsing failed: {e}")
        sys.exit(1)