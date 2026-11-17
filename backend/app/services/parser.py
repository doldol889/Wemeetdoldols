"""문서 텍스트 추출 (BE-07).

AI 파트 [AI-사전1] 추출 코드를 백엔드용으로 옮긴 것.
- 파일 형식별로 본문 · 표 텍스트를 뽑아 하나의 문자열로 돌려준다.
- 페이지(슬라이드) 수도 같이 돌려준다.
- 실패하면 ParseError(code, message)를 던진다 → 작업이 failed 가 되고 error 에 담긴다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ParseError(Exception):
    """사용자에게 보여줄 에러 코드와 메시지를 담는 예외."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ExtractResult:
    text: str
    page_count: int


def _extract_pptx(path: Path) -> ExtractResult:
    from pptx import Presentation

    prs = Presentation(str(path))
    texts: list[str] = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip():
                texts.append(shape.text_frame.text)
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    texts.append(" | ".join(cell.text for cell in row.cells))
    return ExtractResult(text="\n".join(texts), page_count=len(prs.slides))


def _extract_docx(path: Path) -> ExtractResult:
    from docx import Document

    doc = Document(str(path))
    texts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            texts.append(" | ".join(cell.text for cell in row.cells))
    # DOCX는 페이지 개념이 없어서 1로 둔다 (섹션 수로 대체하지 않음)
    return ExtractResult(text="\n".join(texts), page_count=1)


def _extract_pdf(path: Path) -> ExtractResult:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ParseError("ENCRYPTED_FILE", "암호가 걸린 PDF는 분석할 수 없습니다.")
    texts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            texts.append(text)
    return ExtractResult(text="\n".join(texts), page_count=len(reader.pages))


_EXTRACTORS = {
    ".pptx": _extract_pptx,
    ".docx": _extract_docx,
    ".pdf": _extract_pdf,
}


def extract(path: str | Path) -> ExtractResult:
    """파일에서 텍스트를 추출한다. 실패하면 ParseError."""
    path = Path(path)
    ext = path.suffix.lower()

    if ext == ".hwp":
        raise ParseError("PARSE_ERROR", "HWP 파일은 아직 분석을 지원하지 않습니다.")
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        raise ParseError("UNSUPPORTED_TYPE", f"지원하지 않는 형식입니다: {ext}")
    if not path.exists():
        raise ParseError("PARSE_ERROR", "저장된 파일을 찾을 수 없습니다.")

    try:
        result = extractor(path)
    except ParseError:
        raise
    except Exception:  # 손상된 파일 등 — 원문 내용은 메시지에 넣지 않는다
        raise ParseError("PARSE_ERROR", "문서를 읽는 중 오류가 발생했습니다. 파일이 손상되었을 수 있습니다.")

    if not result.text.strip():
        raise ParseError("PARSE_ERROR", "문서에서 읽을 수 있는 글자를 찾지 못했습니다 (이미지만 있는 문서일 수 있어요).")
    return result
