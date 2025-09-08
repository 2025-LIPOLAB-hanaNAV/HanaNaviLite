import re
import logging
import unicodedata
from typing import List, Optional, Dict, Any, Tuple
import hashlib

logger = logging.getLogger(__name__)


class KoreanTextProcessor:
    """
    한국어 텍스트 처리 유틸리티
    형태소 분석 없이 효율적인 한국어 처리
    """
    
    def __init__(self):
        # 한국어 조사/어미 패턴
        self.korean_particles = [
            '은', '는', '이', '가', '을', '를', '의', '에', '에서', '로', '으로',
            '와', '과', '도', '만', '까지', '부터', '마저', '조차', '라도', '든지',
            '이나', '나', '라', '야', '아', '여', '요', '습니다', '했다', '한다'
        ]
        
        # 불용어 (한국어 + 영어)
        self.stopwords = {
            # 한국어 불용어
            '그', '이', '저', '것', '들', '및', '등', '또한', '그리고', '하지만',
            '그러나', '따라서', '그래서', '즉', '예를 들어', '또는', '혹은',
            '만약', '그럼', '그런데', '그렇다면', '물론', '당연히', '확실히',
            '아마', '아마도', '혹시', '만일', '만약에', '설마', '과연',
            '정말', '진짜', '실제로', '사실', '실제', '바로', '단지', '오직',
            # 영어 불용어
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
            'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        # 한국어 문자 패턴
        self.hangul_pattern = re.compile(r'[가-힣]+')
        self.english_pattern = re.compile(r'[a-zA-Z]+')
        self.number_pattern = re.compile(r'[0-9]+')
        
        # 문장 분리 패턴
        self.sentence_patterns = [
            re.compile(r'[.!?]+\s'),  # 마침표, 느낌표, 물음표 + 공백
            re.compile(r'[.!?]+$'),   # 문서 끝의 마침표, 느낌표, 물음표
            re.compile(r'\n\s*\n'),   # 빈 줄
        ]
        
        logger.info("Korean Text Processor initialized")
    
    def normalize_text(self, text: str) -> str:
        """
        텍스트 정규화
        - Unicode 정규화
        - 공백 정리
        - 특수 문자 처리
        """
        if not text:
            return ""
        
        # Unicode 정규화 (NFC)
        text = unicodedata.normalize('NFC', text)
        
        # 연속된 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        
        # 특수 문자 정리 (필요한 것만 남기기)
        text = re.sub(r'[^\w\s가-힣.,!?()-]', ' ', text)
        
        # 앞뒤 공백 제거
        return text.strip()
    
    def remove_particles(self, text: str) -> str:
        """한국어 조사/어미 제거 (간단한 버전)"""
        if not text:
            return ""
        
        words = text.split()
        processed_words = []
        
        for word in words:
            if len(word) <= 1:
                processed_words.append(word)
                continue
            
            # 조사 제거 시도
            processed_word = word
            for particle in self.korean_particles:
                if word.endswith(particle) and len(word) > len(particle):
                    processed_word = word[:-len(particle)]
                    break
            
            processed_words.append(processed_word)
        
        return ' '.join(processed_words)
    
    def remove_stopwords(self, text: str) -> str:
        """불용어 제거"""
        if not text:
            return ""
        
        words = text.split()
        filtered_words = [word for word in words if word.lower() not in self.stopwords]
        
        return ' '.join(filtered_words)
    
    def extract_keywords(self, text: str, min_length: int = 2, max_keywords: int = 20) -> List[str]:
        """
        키워드 추출
        - 한국어/영어 단어 추출
        - 빈도 기반 중요도 계산
        """
        if not text:
            return []
        
        # 텍스트 정규화
        normalized = self.normalize_text(text)
        
        # 한국어 단어 추출
        korean_words = self.hangul_pattern.findall(normalized)
        korean_words = [word for word in korean_words if len(word) >= min_length]
        
        # 영어 단어 추출
        english_words = self.english_pattern.findall(normalized.lower())
        english_words = [word for word in english_words if len(word) >= min_length and word not in self.stopwords]
        
        # 단어 빈도 계산
        word_freq = {}
        for word in korean_words + english_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 빈도순 정렬
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # 상위 키워드 반환
        keywords = [word for word, freq in sorted_words[:max_keywords]]
        
        return keywords
    
    def split_sentences(self, text: str) -> List[str]:
        """문장 단위 분리"""
        if not text:
            return []
        
        # 기본적인 문장 분리
        sentences = []
        current_text = text
        
        for pattern in self.sentence_patterns:
            parts = pattern.split(current_text)
            if len(parts) > 1:
                sentences.extend(parts[:-1])
                current_text = parts[-1]
        
        # 마지막 부분 추가
        if current_text.strip():
            sentences.append(current_text.strip())
        
        # 빈 문장 제거 및 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
        """
        텍스트를 청크 단위로 분할
        한국어 문장 경계 고려
        """
        if not text:
            return []
        
        # 문장 단위로 분리
        sentences = self.split_sentences(text)
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = ""
        current_length = 0
        sentence_start_idx = 0
        
        for i, sentence in enumerate(sentences):
            sentence_length = len(sentence)
            
            # 현재 청크에 추가했을 때 크기 초과하는지 확인
            if current_length + sentence_length > chunk_size and current_chunk:
                # 청크 완성
                chunk_info = {
                    'content': current_chunk.strip(),
                    'start_sentence': sentence_start_idx,
                    'end_sentence': i - 1,
                    'length': current_length,
                    'keywords': self.extract_keywords(current_chunk, max_keywords=10)
                }
                chunks.append(chunk_info)
                
                # 다음 청크 시작 (오버랩 고려)
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
                current_length = len(current_chunk)
                sentence_start_idx = i
            else:
                # 현재 청크에 추가
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                    sentence_start_idx = i
                
                current_length += sentence_length
        
        # 마지막 청크 추가
        if current_chunk.strip():
            chunk_info = {
                'content': current_chunk.strip(),
                'start_sentence': sentence_start_idx,
                'end_sentence': len(sentences) - 1,
                'length': len(current_chunk),
                'keywords': self.extract_keywords(current_chunk, max_keywords=10)
            }
            chunks.append(chunk_info)
        
        return chunks
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        간단한 텍스트 유사도 계산 (Jaccard similarity)
        """
        if not text1 or not text2:
            return 0.0
        
        # 키워드 추출
        keywords1 = set(self.extract_keywords(text1))
        keywords2 = set(self.extract_keywords(text2))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # Jaccard 유사도
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        
        return intersection / union if union > 0 else 0.0
    
    def clean_query(self, query: str) -> str:
        """검색 쿼리 정리"""
        if not query:
            return ""
        
        # 정규화
        cleaned = self.normalize_text(query)
        
        # 조사 제거
        cleaned = self.remove_particles(cleaned)
        
        # 불용어 제거
        cleaned = self.remove_stopwords(cleaned)
        
        return cleaned.strip()
    
    def generate_search_variants(self, query: str) -> List[str]:
        """검색 쿼리 변형 생성"""
        if not query:
            return []
        
        variants = [query]
        
        # 정리된 쿼리
        cleaned = self.clean_query(query)
        if cleaned and cleaned != query:
            variants.append(cleaned)
        
        # 키워드만 추출
        keywords = self.extract_keywords(query, max_keywords=5)
        if keywords:
            keyword_query = ' '.join(keywords)
            if keyword_query not in variants:
                variants.append(keyword_query)
        
        # 중복 제거 및 빈 문자열 제거
        variants = [v for v in variants if v.strip()]
        return list(dict.fromkeys(variants))  # 순서 유지하며 중복 제거
    
    def get_text_hash(self, text: str) -> str:
        """텍스트 해시 생성 (캐싱용)"""
        if not text:
            return ""
        
        # 정규화된 텍스트의 MD5 해시
        normalized = self.normalize_text(text.lower())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def get_stats(self, text: str) -> Dict[str, Any]:
        """텍스트 통계 정보"""
        if not text:
            return {
                'char_count': 0,
                'word_count': 0,
                'sentence_count': 0,
                'korean_ratio': 0.0,
                'english_ratio': 0.0
            }
        
        char_count = len(text)
        words = text.split()
        word_count = len(words)
        sentences = self.split_sentences(text)
        sentence_count = len(sentences)
        
        # 한국어/영어 비율 계산
        korean_chars = len(self.hangul_pattern.findall(text))
        english_chars = len(self.english_pattern.findall(text))
        total_chars = korean_chars + english_chars
        
        korean_ratio = korean_chars / total_chars if total_chars > 0 else 0.0
        english_ratio = english_chars / total_chars if total_chars > 0 else 0.0
        
        return {
            'char_count': char_count,
            'word_count': word_count,
            'sentence_count': sentence_count,
            'korean_ratio': korean_ratio,
            'english_ratio': english_ratio,
            'avg_sentence_length': char_count / sentence_count if sentence_count > 0 else 0
        }


# 전역 인스턴스 (싱글톤 패턴)
_text_processor: Optional[KoreanTextProcessor] = None


def get_text_processor() -> KoreanTextProcessor:
    """텍스트 프로세서 싱글톤 인스턴스 반환"""
    global _text_processor
    if _text_processor is None:
        _text_processor = KoreanTextProcessor()
    return _text_processor


# 편의 함수들
def normalize_korean_text(text: str) -> str:
    """한국어 텍스트 정규화 편의 함수"""
    processor = get_text_processor()
    return processor.normalize_text(text)


def extract_korean_keywords(text: str, max_keywords: int = 20) -> List[str]:
    """키워드 추출 편의 함수"""
    processor = get_text_processor()
    return processor.extract_keywords(text, max_keywords=max_keywords)


def clean_search_query(query: str) -> str:
    """검색 쿼리 정리 편의 함수"""
    processor = get_text_processor()
    return processor.clean_query(query)