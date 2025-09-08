import logging
import os
import hashlib
from typing import Dict, Any, Optional

from app.core.database import get_db_manager
from app.parser.pdf_parser import parse_pdf
from app.parser.docx_parser import parse_docx
from app.parser.xlsx_parser import parse_xlsx
from app.utils.text_processor import get_text_processor
from app.llm.embedding import get_embedding_manager
from app.search.faiss_engine import get_faiss_engine

logger = logging.getLogger(__name__)


class ETLPipeline:
    """
    데이터 수집, 변환, 적재(ETL) 파이프라인
    """

    def __init__(self):
        self.db_manager = get_db_manager()
        self.text_processor = get_text_processor()
        self.embedding_manager = get_embedding_manager()
        self.faiss_engine = get_faiss_engine()
        self.parsers = {
            ".pdf": parse_pdf,
            ".docx": parse_docx,
            ".xlsx": parse_xlsx,
            ".txt": lambda p: [open(p, "r", encoding="utf-8").read()],
            ".md": lambda p: [open(p, "r", encoding="utf-8").read()],
        }
        logger.info("ETL Pipeline initialized")

    def _get_file_hash(self, file_path: str) -> str:
        """파일 내용의 해시를 계산"""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def process_file(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """
        단일 파일을 처리하여 데이터베이스와 벡터 스토어에 저장
        """
        try:
            file_ext = os.path.splitext(file_name)[1].lower()
            if file_ext not in self.parsers:
                raise ValueError(f"Unsupported file type: {file_ext}")

            # 1) 문서 메타데이터 저장 (INSERT or 재처리)
            file_size = os.path.getsize(file_path)
            content_hash = self._get_file_hash(file_path)

            with self.db_manager.get_connection() as conn:
                cur = conn.cursor()

                # 중복(해시) 문서 확인
                cur.execute(
                    "SELECT id, status FROM documents WHERE content_hash = ?",
                    (content_hash,),
                )
                row = cur.fetchone()

                if row:
                    document_id, status = row
                    if status == "processed":
                        logger.info(
                            f"Document '{file_name}' already processed. Skipping."
                        )
                        return {
                            "status": "skipped",
                            "document_id": document_id,
                            "message": "Already processed",
                        }
                    # 이전 실패분 정리
                    cur.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                    # 외부콘텐츠 FTS는 documents 조작에 의해 트리거가 반영하므로
                    # documents_fts를 직접 지우는 코드를 넣을 필요 없음.
                    cur.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                    document_id = None  # 새로 삽입

                # 새 문서 삽입 (초기 상태: processing)
                cur.execute(
                    """
                    INSERT INTO documents
                        (file_name, file_path, file_size, file_type, content_hash, title, status, created_at, updated_at)
                    VALUES
                        (?,        ?,         ?,         ?,         ?,            ?,     'processing', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (file_name, file_path, file_size, file_ext, content_hash, None),
                )
                document_id = cur.lastrowid
                logger.info(f"Inserted document '{file_name}' with ID: {document_id}")

            # 2) 파일 파싱
            logger.info(f"Parsing file: {file_name}")
            parser = self.parsers[file_ext]
            full_text = "\n".join(parser(file_path))

            # 3) 텍스트 청킹
            logger.info(f"Chunking text for document ID: {document_id}")
            chunks = self.text_processor.chunk_text(full_text, chunk_size=1000, overlap=100)

            if not chunks:
                logger.warning(f"No chunks created for document {document_id}. Skipping.")
                with self.db_manager.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        UPDATE documents
                           SET status     = 'failed',
                               content    = ?,
                               updated_at = CURRENT_TIMESTAMP
                         WHERE id = ?
                        """,
                        (full_text, document_id),
                    )
                return {
                    "status": "failed",
                    "document_id": document_id,
                    "message": "No content to chunk",
                }

            # 4) 임베딩 계산 및 청크 저장
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            chunk_contents = [c["content"] for c in chunks]
            embeddings = self.embedding_manager.get_embeddings(chunk_contents)

            chunk_ids = []
            with self.db_manager.get_connection() as conn:
                cur = conn.cursor()
                for i, chunk_info in enumerate(chunks):
                    cur.execute(
                        """
                        INSERT INTO chunks (document_id, chunk_index, content, token_count, created_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (
                            document_id,
                            i,
                            chunk_info["content"],
                            chunk_info.get("length"),
                        ),
                    )
                    chunk_ids.append(f"{document_id}_{i}")

                # 문서 전체 내용 및 상태 업데이트 (애플리케이션에서 타임스탬프 직접 세팅)
                cur.execute(
                    """
                    UPDATE documents
                       SET content      = ?,
                           status       = 'processed',
                           processed_at = CURRENT_TIMESTAMP,
                           updated_at   = CURRENT_TIMESTAMP
                     WHERE id = ?
                    """,
                    (full_text, document_id),
                )
                # NOTE: documents_fts는 트리거가 자동 동기화하므로 수동 INSERT/UPDATE 불필요

            # 5) FAISS 인덱스에 벡터 추가
            logger.info(f"Adding {len(embeddings)} vectors to FAISS index...")
            metadata = [{"document_id": document_id, "chunk_index": i} for i in range(len(chunks))]
            self.faiss_engine.add_vectors(chunk_ids, embeddings, metadata)
            self.faiss_engine.save_index()

            logger.info(f"Successfully processed and indexed file: {file_name}")
            return {
                "status": "success",
                "document_id": document_id,
                "chunks_created": len(chunks),
                "message": "File processed successfully",
            }

        except Exception as e:
            logger.error(f"Failed to process file '{file_name}': {e}", exc_info=True)
            # 실패 시 상태 업데이트 (updated_at 포함)
            try:
                if "document_id" in locals() and document_id:
                    with self.db_manager.get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            """
                            UPDATE documents
                               SET status     = 'failed',
                                   updated_at = CURRENT_TIMESTAMP
                             WHERE id = ?
                            """,
                            (document_id,),
                        )
            except Exception:
                # 상태 업데이트마저 실패해도 여기서 추가 예외는 무시
                pass

            return {"status": "error", "message": str(e)}


# 전역 인스턴스
_etl_pipeline: Optional[ETLPipeline] = None

def get_etl_pipeline() -> ETLPipeline:
    global _etl_pipeline
    if _etl_pipeline is None:
        _etl_pipeline = ETLPipeline()
    return _etl_pipeline
