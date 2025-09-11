import logging
import os
import tempfile
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.parser.pdf_parser import parse_pdf
from app.parser.docx_parser import parse_docx
from app.parser.xlsx_parser import parse_xlsx
from app.parser.image_ocr_parser import create_parser as create_image_parser
from app.utils.text_processor import get_text_processor
from app.llm.embedding import get_embedding_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# 임시 파일 캐시 (메모리에 저장, 실제 운영에서는 Redis 등 사용)
_temp_file_cache: Dict[str, Dict[str, Any]] = {}

@router.post("/chat/upload")
async def upload_chat_file(file: UploadFile = File(...)):
    """
    채팅용 임시 파일 업로드 및 즉시 처리
    영구 저장하지 않고 메모리에 캐시하여 대화에서만 사용
    """
    try:
        # 파일 확장자 확인
        file_ext = os.path.splitext(file.filename or '')[1].lower()
        supported_exts = {".pdf", ".docx", ".xlsx", ".txt", ".md", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}
        
        if file_ext not in supported_exts:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: {file_ext}")
        
        # 파일 크기 제한 (10MB)
        max_size = 10 * 1024 * 1024
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="파일 크기가 10MB를 초과합니다")
        
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # 파일 파싱
            text_content = ""
            page_count = 0
            
            if file_ext == ".pdf":
                pages = parse_pdf(temp_file_path)
                text_content = "\n".join(pages)
                page_count = len(pages)
            elif file_ext == ".docx":
                pages = parse_docx(temp_file_path)
                text_content = "\n".join(pages)
                page_count = len(pages)
            elif file_ext == ".xlsx":
                pages = parse_xlsx(temp_file_path)
                text_content = "\n".join(pages)
                page_count = len(pages)
            elif file_ext in [".txt", ".md"]:
                with open(temp_file_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
                page_count = 1
            elif file_ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]:
                parser = create_image_parser()
                result = parser.parse_file(temp_file_path)
                text_content = result.content
                page_count = 1
            
            if not text_content or not text_content.strip():
                raise HTTPException(status_code=400, detail="파일에서 텍스트를 추출할 수 없습니다")
            
            # 텍스트 청킹
            text_processor = get_text_processor()
            chunks = text_processor.chunk_text(text_content, chunk_size=1000, overlap=100)
            
            if not chunks:
                # 폴백 청킹
                chunk_size = 1000
                chunks = []
                for i in range(0, len(text_content), chunk_size):
                    chunk_text = text_content[i:i+chunk_size]
                    if chunk_text.strip():
                        chunks.append({
                            'content': chunk_text.strip(),
                            'start_sentence': 0,
                            'end_sentence': 0,
                            'length': len(chunk_text),
                            'keywords': text_processor.extract_keywords(chunk_text, max_keywords=5)
                        })
            
            # 임베딩 생성
            embedding_manager = get_embedding_manager()
            chunk_contents = [chunk["content"] for chunk in chunks]
            embeddings = embedding_manager.get_embeddings(chunk_contents)
            
            # 임시 ID 생성
            temp_id = str(uuid.uuid4())
            
            # 캐시에 저장
            _temp_file_cache[temp_id] = {
                "file_name": file.filename,
                "file_type": file_ext,
                "file_size": len(file_content),
                "text_content": text_content,
                "chunks": chunks,
                "embeddings": embeddings.tolist() if embeddings is not None else [],
                "page_count": page_count,
                "char_count": len(text_content),
                "chunk_count": len(chunks)
            }
            
            logger.info(f"Processed chat file: {file.filename} -> {temp_id} ({len(chunks)} chunks)")
            
            return {
                "temp_id": temp_id,
                "file_name": file.filename,
                "file_type": file_ext,
                "file_size": len(file_content),
                "page_count": page_count,
                "char_count": len(text_content),
                "chunk_count": len(chunks),
                "message": "파일이 성공적으로 처리되었습니다. 이제 이 파일 내용에 대해 질문할 수 있습니다."
            }
            
        finally:
            # 임시 파일 정리
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process chat file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류가 발생했습니다: {str(e)}")


@router.get("/chat/files/{temp_id}")
async def get_chat_file_info(temp_id: str):
    """임시 파일 정보 조회"""
    if temp_id not in _temp_file_cache:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    
    file_info = _temp_file_cache[temp_id]
    return {
        "temp_id": temp_id,
        "file_name": file_info["file_name"],
        "file_type": file_info["file_type"],
        "file_size": file_info["file_size"],
        "page_count": file_info["page_count"],
        "char_count": file_info["char_count"],
        "chunk_count": file_info["chunk_count"]
    }


@router.post("/chat/search_in_file")
async def search_in_chat_file(temp_id: str = Form(...), query: str = Form(...), top_k: int = Form(5)):
    """업로드된 파일 내에서 검색"""
    if temp_id not in _temp_file_cache:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    
    try:
        file_info = _temp_file_cache[temp_id]
        chunks = file_info["chunks"]
        stored_embeddings = file_info["embeddings"]
        
        if not stored_embeddings:
            raise HTTPException(status_code=400, detail="파일 임베딩이 없습니다")
        
        # 쿼리 임베딩 생성
        embedding_manager = get_embedding_manager()
        query_embedding = embedding_manager.get_embeddings([query])
        
        if query_embedding is None:
            raise HTTPException(status_code=500, detail="쿼리 임베딩 생성 실패")
        
        # 유사도 계산
        import numpy as np
        query_vec = query_embedding[0]
        similarities = []
        
        for i, chunk_embedding in enumerate(stored_embeddings):
            chunk_vec = np.array(chunk_embedding)
            # 코사인 유사도 계산
            similarity = np.dot(query_vec, chunk_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec))
            similarities.append((i, similarity, chunks[i]))
        
        # 유사도 순으로 정렬
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 결과 반환
        results = []
        for i, (chunk_idx, similarity, chunk) in enumerate(similarities[:top_k]):
            results.append({
                "chunk_index": chunk_idx,
                "similarity": float(similarity),
                "content": chunk["content"],
                "keywords": chunk.get("keywords", [])
            })
        
        return {
            "query": query,
            "file_name": file_info["file_name"],
            "results": results,
            "total_chunks": len(chunks)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search in chat file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 검색 중 오류가 발생했습니다: {str(e)}")


@router.delete("/chat/files/{temp_id}")
async def delete_chat_file(temp_id: str):
    """임시 파일 삭제"""
    if temp_id not in _temp_file_cache:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    
    file_info = _temp_file_cache.pop(temp_id)
    logger.info(f"Deleted chat file: {file_info['file_name']} ({temp_id})")
    
    return {"message": "파일이 삭제되었습니다"}


def get_temp_file_content(temp_id: str) -> str:
    """임시 파일의 전체 텍스트 내용 반환 (다른 모듈에서 사용)"""
    if temp_id in _temp_file_cache:
        return _temp_file_cache[temp_id]["text_content"]
    return ""


def cleanup_old_files():
    """오래된 임시 파일들 정리 (주기적으로 호출)"""
    # 실제로는 타임스탬프를 추가해서 1시간 이상 된 파일들을 정리
    pass