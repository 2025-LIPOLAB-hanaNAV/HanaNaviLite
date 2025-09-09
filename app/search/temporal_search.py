#!/usr/bin/env python3
"""
Temporal Search System - Natural Language Time Range Processing
Phase 2 고급 검색 기능 - 시간 기반 검색 및 자연어 시간 표현 처리
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, date
from enum import Enum
from dataclasses import dataclass
import calendar
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class TimeUnit(Enum):
    """시간 단위"""
    DAY = "일"
    WEEK = "주"
    MONTH = "월"
    QUARTER = "분기"
    YEAR = "년"


class TimeDirection(Enum):
    """시간 방향"""
    PAST = "과거"
    FUTURE = "미래"
    CURRENT = "현재"


@dataclass
class TimeRange:
    """시간 범위"""
    start_date: datetime
    end_date: datetime
    description: str
    confidence: float = 1.0
    
    def to_sql_conditions(self) -> Tuple[str, List]:
        """SQL 조건문 생성"""
        return (
            "(created_at >= ? AND created_at <= ?)",
            [self.start_date.isoformat(), self.end_date.isoformat()]
        )


@dataclass
class TemporalQuery:
    """시간적 쿼리"""
    original_query: str
    cleaned_query: str
    time_ranges: List[TimeRange]
    temporal_expressions: List[str]
    has_temporal: bool


class KoreanTemporalParser:
    """한국어 시간 표현 파서"""
    
    def __init__(self):
        self.today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.temporal_patterns = self._initialize_temporal_patterns()
        self.korean_numbers = self._initialize_korean_numbers()
        
    def _initialize_temporal_patterns(self) -> List[Dict]:
        """한국어 시간 표현 패턴 초기화"""
        return [
            # 절대적 시간 표현
            {
                'pattern': r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
                'type': 'absolute_date',
                'handler': self._parse_absolute_date
            },
            {
                'pattern': r'(\d{4})년\s*(\d{1,2})월',
                'type': 'absolute_month',
                'handler': self._parse_absolute_month
            },
            {
                'pattern': r'(\d{4})년',
                'type': 'absolute_year',
                'handler': self._parse_absolute_year
            },
            
            # 상대적 시간 표현 - 최근
            {
                'pattern': r'최근\s*([일이삼사오육칠팔구십1-9]+|한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*(일|주|개?\s*월|년)',
                'type': 'recent_period',
                'handler': self._parse_recent_period
            },
            {
                'pattern': r'최근\s*(하루|이틀|사흘|나흘|닷새|엿새|이레|여드레|아흐레|열흘)',
                'type': 'recent_days',
                'handler': self._parse_recent_days_korean
            },
            {
                'pattern': r'최근\s*(\d+)\s*(일|주|개?\s*월|년)',
                'type': 'recent_number',
                'handler': self._parse_recent_number
            },
            
            # 지난/작년 표현
            {
                'pattern': r'지난\s*(주|달|월|년)',
                'type': 'last_period',
                'handler': self._parse_last_period
            },
            {
                'pattern': r'작년|지난해|지난\s*년',
                'type': 'last_year',
                'handler': self._parse_last_year
            },
            {
                'pattern': r'작년\s*동기|지난해\s*동기',
                'type': 'same_period_last_year',
                'handler': self._parse_same_period_last_year
            },
            
            # 이번/올해 표현
            {
                'pattern': r'이번\s*(주|달|월|년)',
                'type': 'this_period',
                'handler': self._parse_this_period
            },
            {
                'pattern': r'올해|금년|이번\s*년',
                'type': 'this_year',
                'handler': self._parse_this_year
            },
            
            # 분기 표현
            {
                'pattern': r'(\d+)\s*분기',
                'type': 'quarter',
                'handler': self._parse_quarter
            },
            {
                'pattern': r'(1|2|3|4|첫|두|세|네)?\s*번째\s*분기',
                'type': 'quarter_ordinal',
                'handler': self._parse_quarter_ordinal
            },
            
            # 월 이름
            {
                'pattern': r'(\d{1,2})월',
                'type': 'month_name',
                'handler': self._parse_month_name
            },
            
            # 특정 기간 범위
            {
                'pattern': r'(\d+)일?\s*(부터|에서)\s*(\d+)일?\s*(까지|사이)',
                'type': 'day_range',
                'handler': self._parse_day_range
            },
            {
                'pattern': r'(\d+)월\s*(부터|에서)\s*(\d+)월\s*(까지|사이)',
                'type': 'month_range',
                'handler': self._parse_month_range
            }
        ]
    
    def _initialize_korean_numbers(self) -> Dict[str, int]:
        """한국어 숫자 매핑"""
        return {
            '한': 1, '일': 1, '하나': 1,
            '두': 2, '이': 2, '둘': 2,
            '세': 3, '삼': 3, '셋': 3,
            '네': 4, '사': 4, '넷': 4,
            '다섯': 5, '오': 5,
            '여섯': 6, '육': 6,
            '일곱': 7, '칠': 7,
            '여덟': 8, '팔': 8,
            '아홉': 9, '구': 9,
            '열': 10, '십': 10
        }
    
    def parse_temporal_query(self, query: str) -> TemporalQuery:
        """시간적 쿼리 파싱"""
        try:
            time_ranges = []
            temporal_expressions = []
            current_query = query # Use a mutable variable for the query
            
            # Sort patterns by length in descending order to prioritize longer matches
            # This helps in matching "2024년 3월 15일" before "2024년" or "3월"
            sorted_patterns = sorted(self.temporal_patterns, key=lambda x: len(x['pattern']), reverse=True)

            for pattern_info in sorted_patterns:
                pattern = pattern_info['pattern']
                # Apply pattern to the current_query
                matches = list(re.finditer(pattern, current_query, re.IGNORECASE))
                
                # Process matches in reverse order to avoid issues with string replacement
                for match in reversed(matches):
                    try:
                        time_range = pattern_info['handler'](match)
                        if time_range:
                            time_ranges.append(time_range)
                            temporal_expressions.append(match.group(0))
                            
                            # Remove the matched temporal expression from current_query
                            start, end = match.span()
                            current_query = current_query[:start] + current_query[end:]
                            
                    except Exception as e:
                        logger.warning(f"Failed to parse temporal expression '{match.group(0)}': {e}")
            
            # Clean up extra spaces after replacements
            cleaned_query = re.sub(r'\s+', ' ', current_query).strip()
            
            return TemporalQuery(
                original_query=query,
                cleaned_query=cleaned_query,
                time_ranges=time_ranges,
                temporal_expressions=list(set(temporal_expressions)), # Use set to remove duplicates
                has_temporal=len(time_ranges) > 0
            )
            
        except Exception as e:
            logger.error(f"Temporal query parsing failed: {e}")
            return TemporalQuery(
                original_query=query,
                cleaned_query=query,
                time_ranges=[],
                temporal_expressions=[],
                has_temporal=False
            )
    
    def _parse_absolute_date(self, match) -> Optional[TimeRange]:
        """절대 날짜 파싱: 2024년 3월 15일"""
        try:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            
            start_date = datetime(year, month, day)
            end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description=f"{year}년 {month}월 {day}일",
                confidence=1.0
            )
            
        except (ValueError, IndexError):
            return None
    
    def _parse_absolute_month(self, match) -> Optional[TimeRange]:
        """절대 월 파싱: 2024년 3월"""
        try:
            year = int(match.group(1))
            month = int(match.group(2))
            
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description=f"{year}년 {month}월",
                confidence=1.0
            )
            
        except (ValueError, IndexError):
            return None
    
    def _parse_absolute_year(self, match) -> Optional[TimeRange]:
        """절대 연도 파싱: 2024년"""
        try:
            year = int(match.group(1))
            
            start_date = datetime(year, 1, 1)
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description=f"{year}년",
                confidence=1.0
            )
            
        except (ValueError, IndexError):
            return None
    
    def _parse_recent_period(self, match) -> Optional[TimeRange]:
        """최근 기간 파싱: 최근 3개월, 최근 두 주"""
        try:
            number_str = match.group(1)
            unit = match.group(2).replace('개', '').strip()
            
            # 한국어 숫자 변환
            if number_str in self.korean_numbers:
                number = self.korean_numbers[number_str]
            else:
                try:
                    number = int(number_str)
                except ValueError:
                    return None
            
            end_date = self.today + timedelta(days=1) - timedelta(seconds=1)
            
            if unit == '일':
                start_date = self.today - timedelta(days=number)
                desc = f"최근 {number}일"
            elif unit == '주':
                start_date = self.today - timedelta(weeks=number)
                desc = f"최근 {number}주"
            elif unit in ['월', '개월']:
                start_date = self.today - relativedelta(months=number)
                desc = f"최근 {number}개월"
            elif unit == '년':
                start_date = self.today - relativedelta(years=number)
                desc = f"최근 {number}년"
            else:
                return None
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description=desc,
                confidence=0.9
            )
            
        except Exception:
            return None
    
    def _parse_recent_number(self, match) -> Optional[TimeRange]:
        """최근 숫자 기간 파싱: 최근 30일"""
        try:
            number = int(match.group(1))
            unit = match.group(2).replace('개', '').strip()
            
            return self._create_recent_range(number, unit)
            
        except (ValueError, IndexError):
            return None
    
    def _parse_recent_days_korean(self, match) -> Optional[TimeRange]:
        """최근 한국어 일 수 파싱: 최근 이틀, 최근 사흘"""
        korean_day_names = {
            '하루': 1, '이틀': 2, '사흘': 3, '나흘': 4, '닷새': 5,
            '엿새': 6, '이레': 7, '여드레': 8, '아흐레': 9, '열흘': 10
        }
        
        day_name = match.group(1)
        if day_name in korean_day_names:
            number = korean_day_names[day_name]
            return self._create_recent_range(number, '일')
        
        return None
    
    def _create_recent_range(self, number: int, unit: str) -> Optional[TimeRange]:
        """최근 범위 생성 헬퍼"""
        end_date = self.today + timedelta(days=1) - timedelta(seconds=1)
        
        if unit == '일':
            start_date = self.today - timedelta(days=number)
            desc = f"최근 {number}일"
        elif unit == '주':
            start_date = self.today - timedelta(weeks=number)
            desc = f"최근 {number}주"
        elif unit in ['월', '개월']:
            start_date = self.today - relativedelta(months=number)
            desc = f"최근 {number}개월"
        elif unit == '년':
            start_date = self.today - relativedelta(years=number)
            desc = f"최근 {number}년"
        else:
            return None
        
        return TimeRange(
            start_date=start_date,
            end_date=end_date,
            description=desc,
            confidence=0.9
        )
    
    def _parse_last_period(self, match) -> Optional[TimeRange]:
        """지난 기간 파싱: 지난 주, 지난 달"""
        unit = match.group(1)
        today = self.today
        
        if unit == '주':
            # 지난 주 (월요일 ~ 일요일)
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            return TimeRange(
                start_date=last_monday,
                end_date=last_sunday,
                description="지난 주",
                confidence=0.95
            )
            
        elif unit in ['달', '월']:
            # 지난 달
            if today.month == 1:
                last_month_date = today.replace(year=today.year - 1, month=12, day=1)
            else:
                last_month_date = today.replace(month=today.month - 1, day=1)
            
            start_date = last_month_date
            
            # 다음 달의 첫날 - 1초
            if last_month_date.month == 12:
                end_date = datetime(last_month_date.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(last_month_date.year, last_month_date.month + 1, 1) - timedelta(seconds=1)
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description="지난 달",
                confidence=0.95
            )
            
        elif unit == '년':
            return self._parse_last_year(match)
        
        return None
    
    def _parse_last_year(self, match) -> Optional[TimeRange]:
        """작년 파싱"""
        last_year = self.today.year - 1
        
        start_date = datetime(last_year, 1, 1)
        end_date = datetime(last_year + 1, 1, 1) - timedelta(seconds=1)
        
        return TimeRange(
            start_date=start_date,
            end_date=end_date,
            description="작년",
            confidence=1.0
        )
    
    def _parse_same_period_last_year(self, match) -> Optional[TimeRange]:
        """작년 동기 파싱"""
        # 현재 날짜에서 1년 전의 같은 기간
        current_date = self.today
        last_year_date = current_date - relativedelta(years=1)
        
        # 현재 월의 작년 동월
        start_date = last_year_date.replace(day=1)
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1) - timedelta(seconds=1)
        
        return TimeRange(
            start_date=start_date,
            end_date=end_date,
            description="작년 동기",
            confidence=0.85
        )
    
    def _parse_this_period(self, match) -> Optional[TimeRange]:
        """이번 기간 파싱: 이번 주, 이번 달"""
        unit = match.group(1)
        today = self.today
        
        if unit == '주':
            # 이번 주 (월요일 ~ 일요일)
            days_since_monday = today.weekday()
            this_monday = today - timedelta(days=days_since_monday)
            this_sunday = this_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            return TimeRange(
                start_date=this_monday,
                end_date=this_sunday,
                description="이번 주",
                confidence=1.0
            )
            
        elif unit in ['달', '월']:
            # 이번 달
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = datetime(today.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(today.year, today.month + 1, 1) - timedelta(seconds=1)
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description="이번 달",
                confidence=1.0
            )
            
        elif unit == '년':
            return self._parse_this_year(match)
        
        return None
    
    def _parse_this_year(self, match) -> Optional[TimeRange]:
        """올해 파싱"""
        this_year = self.today.year
        
        start_date = datetime(this_year, 1, 1)
        end_date = datetime(this_year + 1, 1, 1) - timedelta(seconds=1)
        
        return TimeRange(
            start_date=start_date,
            end_date=end_date,
            description="올해",
            confidence=1.0
        )
    
    def _parse_quarter(self, match) -> Optional[TimeRange]:
        """분기 파싱: 1분기, 2분기"""
        try:
            quarter_num = int(match.group(1))
            if quarter_num < 1 or quarter_num > 4:
                return None
            
            year = self.today.year
            start_month = (quarter_num - 1) * 3 + 1
            end_month = quarter_num * 3
            
            start_date = datetime(year, start_month, 1)
            if end_month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, end_month + 1, 1) - timedelta(seconds=1)
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description=f"{quarter_num}분기",
                confidence=0.9
            )
            
        except (ValueError, IndexError):
            return None
    
    def _parse_quarter_ordinal(self, match) -> Optional[TimeRange]:
        """순서 분기 파싱: 첫 번째 분기"""
        quarter_map = {'첫': 1, '두': 2, '세': 3, '네': 4, '1': 1, '2': 2, '3': 3, '4': 4}
        
        quarter_str = match.group(1)
        if quarter_str in quarter_map:
            quarter_num = quarter_map[quarter_str]
            
            # 기존 _parse_quarter 로직 재사용
            class MockMatch:
                def group(self, n):
                    return str(quarter_num)
            
            return self._parse_quarter(MockMatch())
        
        return None
    
    def _parse_month_name(self, match) -> Optional[TimeRange]:
        """월 이름 파싱: 3월"""
        try:
            month = int(match.group(1))
            if month < 1 or month > 12:
                return None
            
            year = self.today.year
            
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description=f"{month}월",
                confidence=0.8
            )
            
        except (ValueError, IndexError):
            return None
    
    def _parse_day_range(self, match) -> Optional[TimeRange]:
        """일 범위 파싱: 15일부터 20일까지"""
        try:
            start_day = int(match.group(1))
            end_day = int(match.group(3))
            
            current_month = self.today.month
            current_year = self.today.year
            
            start_date = datetime(current_year, current_month, start_day)
            end_date = datetime(current_year, current_month, end_day, 23, 59, 59)
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description=f"{start_day}일부터 {end_day}일까지",
                confidence=0.8
            )
            
        except (ValueError, IndexError):
            return None
    
    def _parse_month_range(self, match) -> Optional[TimeRange]:
        """월 범위 파싱: 3월부터 6월까지"""
        try:
            start_month = int(match.group(1))
            end_month = int(match.group(3))
            
            if start_month < 1 or start_month > 12 or end_month < 1 or end_month > 12:
                return None
            
            current_year = self.today.year
            
            start_date = datetime(current_year, start_month, 1)
            if end_month == 12:
                end_date = datetime(current_year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(current_year, end_month + 1, 1) - timedelta(seconds=1)
            
            return TimeRange(
                start_date=start_date,
                end_date=end_date,
                description=f"{start_month}월부터 {end_month}월까지",
                confidence=0.8
            )
            
        except (ValueError, IndexError):
            return None


class TemporalSearchEngine:
    """시간 기반 검색 엔진"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.parser = KoreanTemporalParser()
        
    def search_with_temporal(self, query: str, base_results: List[Dict] = None, 
                           top_k: int = 20) -> Dict[str, Any]:
        """시간적 검색 수행"""
        try:
            # 시간적 쿼리 파싱
            temporal_query = self.parser.parse_temporal_query(query)
            
            if not temporal_query.has_temporal:
                # 시간적 요소가 없으면 기본 결과 반환
                return {
                    'results': base_results or [],
                    'temporal_info': {
                        'has_temporal': False,
                        'original_query': query,
                        'cleaned_query': query
                    }
                }
            
            # 시간 조건을 적용한 문서 검색
            filtered_results = self._apply_temporal_filters(
                temporal_query, base_results, top_k
            )
            
            return {
                'results': filtered_results,
                'temporal_info': {
                    'has_temporal': True,
                    'original_query': temporal_query.original_query,
                    'cleaned_query': temporal_query.cleaned_query,
                    'time_ranges': [
                        {
                            'description': tr.description,
                            'start_date': tr.start_date.isoformat(),
                            'end_date': tr.end_date.isoformat(),
                            'confidence': tr.confidence
                        }
                        for tr in temporal_query.time_ranges
                    ],
                    'temporal_expressions': temporal_query.temporal_expressions
                }
            }
            
        except Exception as e:
            logger.error(f"Temporal search failed: {e}")
            return {
                'results': base_results or [],
                'temporal_info': {
                    'has_temporal': False,
                    'error': str(e)
                }
            }
    
    def _apply_temporal_filters(self, temporal_query: TemporalQuery, 
                              base_results: List[Dict], top_k: int) -> List[Dict]:
        """시간적 필터 적용"""
        try:
            if not temporal_query.time_ranges:
                return base_results or []
            
            # SQL 조건 생성
            time_conditions = []
            time_params = []
            
            for time_range in temporal_query.time_ranges:
                condition, params = time_range.to_sql_conditions()
                time_conditions.append(condition)
                time_params.extend(params)
            
            # OR 조건으로 결합 (여러 시간 범위 중 하나라도 만족하면)
            where_clause = " OR ".join(time_conditions)
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                if base_results:
                    # 기존 결과에 시간 필터 적용
                    doc_ids = [str(result.get('document_id', result.get('id', 0))) 
                              for result in base_results]
                    id_placeholders = ','.join(['?' for _ in doc_ids])
                    
                    cursor.execute(f"""
                        SELECT d.id, d.title, d.file_name, d.content, d.created_at,
                               d.file_type, d.summary
                        FROM documents d
                        WHERE d.id IN ({id_placeholders}) 
                        AND ({where_clause})
                        ORDER BY d.created_at DESC
                        LIMIT ?
                    """, doc_ids + time_params + [top_k])
                    
                else:
                    # 시간 조건만으로 검색
                    cursor.execute(f"""
                        SELECT d.id, d.title, d.file_name, d.content, d.created_at,
                               d.file_type, d.summary
                        FROM documents d
                        WHERE ({where_clause}) AND d.status = 'completed'
                        ORDER BY d.created_at DESC
                        LIMIT ?
                    """, time_params + [top_k])
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'document_id': row[0],
                        'title': row[1] or '',
                        'file_name': row[2] or '',
                        'content_preview': (row[3] or '')[:300],
                        'created_at': row[4],
                        'file_type': row[5] or '',
                        'summary': row[6] or '',
                        'score': 1.0,  # 시간 기반 검색은 관련성 점수 고정
                        'temporal_match': True
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Failed to apply temporal filters: {e}")
            return base_results or []
    
    def get_temporal_statistics(self) -> Dict[str, Any]:
        """시간적 통계 정보"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 월별 문서 수
                cursor.execute("""
                    SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
                    FROM documents 
                    WHERE status = 'completed' 
                    AND created_at >= date('now', '-12 months')
                    GROUP BY strftime('%Y-%m', created_at)
                    ORDER BY month DESC
                """)
                
                monthly_stats = {row[0]: row[1] for row in cursor.fetchall()}
                
                # 최근 활동
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN created_at >= date('now', '-1 day') THEN 1 END) as today,
                        COUNT(CASE WHEN created_at >= date('now', '-7 days') THEN 1 END) as this_week,
                        COUNT(CASE WHEN created_at >= date('now', '-30 days') THEN 1 END) as this_month,
                        COUNT(*) as total
                    FROM documents 
                    WHERE status = 'completed'
                """)
                
                row = cursor.fetchone()
                recent_activity = {
                    'today': row[0] if row else 0,
                    'this_week': row[1] if row else 0,
                    'this_month': row[2] if row else 0,
                    'total': row[3] if row else 0
                }
                
                return {
                    'monthly_distribution': monthly_stats,
                    'recent_activity': recent_activity
                }
                
        except Exception as e:
            logger.error(f"Failed to get temporal statistics: {e}")
            return {'monthly_distribution': {}, 'recent_activity': {}}


# 전역 인스턴스
_temporal_search_engine: Optional[TemporalSearchEngine] = None


def get_temporal_search_engine(db_manager=None) -> TemporalSearchEngine:
    """시간 기반 검색 엔진 싱글톤 반환"""
    global _temporal_search_engine
    if _temporal_search_engine is None:
        if db_manager is None:
            from app.core.database import get_database_manager
            db_manager = get_database_manager()
        _temporal_search_engine = TemporalSearchEngine(db_manager)
    return _temporal_search_engine