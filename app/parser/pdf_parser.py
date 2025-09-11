from typing import List, Optional, Tuple
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)


def _import_candidates() -> List[Tuple[str, Optional[object]]]:
    """Return a PdfReader class from available backends (pypdf or PyPDF2)."""
    candidates: List[Tuple[str, Optional[object]]] = []
    try:  # pragma: no cover
        from pypdf import PdfReader as PypdfReader  # type: ignore
        candidates.append(("pypdf", PypdfReader))
    except Exception:
        candidates.append(("pypdf", None))
    try:  # pragma: no cover
        from PyPDF2 import PdfReader as PyPDF2Reader  # type: ignore
        candidates.append(("PyPDF2", PyPDF2Reader))
    except Exception:
        candidates.append(("PyPDF2", None))
    return candidates


def parse_pdf(path: str) -> List[str]:
    """Parse a PDF file into page texts using available backend.

    Returns a list of per-page text strings. Returns empty list if parsing fails.
    """
    cand = _import_candidates()
    best_texts: List[str] = []
    best_len = -1

    def extract_with(reader_cls) -> List[str]:
        if reader_cls is None:
            return []
        try:
            reader = reader_cls(path)
            pages = getattr(reader, 'pages', [])
            out: List[str] = []
            for page in pages:
                try:
                    raw = page.extract_text()  # type: ignore[attr-defined]
                except Exception:
                    raw = None
                if not raw:
                    out.append("")
                else:
                    cleaned = (
                        raw.replace('\u00A0', ' ')
                           .replace('\x00', ' ')
                           .replace('\r', '\n')
                    )
                    out.append(cleaned)
            return out
        except Exception:
            return []

    # Try all candidates and choose the one with the most characters
    for name, cls in cand:
        texts = extract_with(cls)
        total = sum(len(t) for t in texts)
        if total > best_len:
            best_len = total
            best_texts = texts

    # Final cleanup: ensure at least one element if any content
    if best_len > 0:
        return best_texts

    # Fallback 2: use 'pdftotext' CLI if available (poppler-utils)
    try:
        if shutil.which('pdftotext'):
            # -layout preserves layout, -enc UTF-8 outputs UTF-8, output to stdout with '-' target
            result = subprocess.run(
                ['pdftotext', '-layout', '-enc', 'UTF-8', path, '-'],
                capture_output=True,
                check=False,
                timeout=20
            )
            if result.returncode == 0:
                text = result.stdout.decode('utf-8', errors='ignore')
                if text and text.strip():
                    # pdftotext separates pages with form-feed '\f'
                    pages = [p.strip() for p in text.split('\f') if p and p.strip()]
                    logger.info(f"pdftotext extracted chars={len(text)} pages={len(pages)}")
                    return pages if pages else [text]
            else:
                logger.warning(f"pdftotext failed rc={result.returncode}: {result.stderr[:200]!r}")
    except Exception as e:
        logger.warning(f"pdftotext fallback error: {e}")

    # Give up: return empty
    return []
