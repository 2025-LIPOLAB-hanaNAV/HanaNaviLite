from typing import List


def _import_pdf_reader():
    """Return a PdfReader class from available backends (pypdf or PyPDF2)."""
    # Try pypdf first
    try:  # pragma: no cover - runtime environment dependent
        from pypdf import PdfReader  # type: ignore
        return PdfReader
    except Exception:
        pass
    # Fallback to PyPDF2 (declared in requirements.txt)
    try:  # pragma: no cover
        from PyPDF2 import PdfReader  # type: ignore
        return PdfReader
    except Exception:
        return None


def parse_pdf(path: str) -> List[str]:
    """Parse a PDF file into page texts using available backend.

    Returns a list of per-page text strings. Returns empty list if parsing fails.
    """
    PdfReader = _import_pdf_reader()
    if not PdfReader:  # pragma: no cover
        return []
    try:
        reader = PdfReader(path)
        texts: List[str] = []
        for page in getattr(reader, 'pages', []):
            try:
                raw = page.extract_text()  # type: ignore[attr-defined]
                if raw is None:
                    texts.append("")
                else:
                    # Normalize whitespace and NBSP
                    cleaned = raw.replace('\u00A0', ' ').strip()
                    texts.append(cleaned)
            except Exception:
                texts.append("")
        return texts
    except Exception:
        return []
