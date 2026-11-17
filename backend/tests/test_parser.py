"""BE-07 텍스트 추출 · 분석 테스트 (인애 담당).

실제 DOCX / PPTX / PDF 파일을 테스트 안에서 만들어서 추출해 본다.
Claude 키는 쓰지 않는다 (규칙 기반 분석으로 확인).
"""
import pytest

from app.schemas.job import JobStatus
from app.services import analyzer, mock_store, parser


@pytest.fixture(autouse=True)
def no_claude_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def make_docx(path):
    from docx import Document

    doc = Document()
    doc.add_paragraph("주간 회의록")
    doc.add_paragraph("백엔드 업로드 API 완료. 프론트엔드 연결은 다음 주. 백엔드 테스트 진행.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "담당"
    table.rows[0].cells[1].text = "백엔드"
    doc.save(path)


def make_pptx(path, slides=2):
    from pptx import Presentation

    prs = Presentation()
    for i in range(slides):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"발표 슬라이드 {i + 1}"
        slide.placeholders[1].text = "위밋 프로젝트 파일 분류 시스템 소개"
    prs.save(path)


def make_blank_pdf(path, password=None):
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    if password:
        writer.encrypt(password)
    with open(path, "wb") as f:
        writer.write(f)


# ---------------------------------------------------------------- parser
def test_extract_docx(tmp_path):
    p = tmp_path / "meeting.docx"
    make_docx(p)
    result = parser.extract(p)
    assert "주간 회의록" in result.text
    assert "담당 | 백엔드" in result.text  # 표도 추출


def test_extract_pptx_counts_slides(tmp_path):
    p = tmp_path / "deck.pptx"
    make_pptx(p, slides=3)
    result = parser.extract(p)
    assert result.page_count == 3
    assert "발표 슬라이드 1" in result.text


def test_extract_pdf_with_text(tmp_path):
    pytest.importorskip("reportlab")  # PDF를 만들 도구가 있을 때만
    from reportlab.pdfgen import canvas

    p = tmp_path / "doc.pdf"
    c = canvas.Canvas(str(p))
    c.drawString(72, 720, "WeMeet project report")
    c.showPage()
    c.drawString(72, 720, "Second page")
    c.save()
    result = parser.extract(p)
    assert result.page_count == 2
    assert "WeMeet" in result.text


def test_encrypted_pdf(tmp_path):
    p = tmp_path / "secret.pdf"
    make_blank_pdf(p, password="1234")
    with pytest.raises(parser.ParseError) as e:
        parser.extract(p)
    assert e.value.code == "ENCRYPTED_FILE"


def test_pdf_without_text(tmp_path):
    p = tmp_path / "blank.pdf"
    make_blank_pdf(p)
    with pytest.raises(parser.ParseError) as e:
        parser.extract(p)
    assert e.value.code == "PARSE_ERROR"


def test_broken_file(tmp_path):
    p = tmp_path / "broken.docx"
    p.write_bytes(b"this is not a real docx")
    with pytest.raises(parser.ParseError) as e:
        parser.extract(p)
    assert e.value.code == "PARSE_ERROR"


def test_hwp_not_supported_yet(tmp_path):
    p = tmp_path / "a.hwp"
    p.write_bytes(b"x")
    with pytest.raises(parser.ParseError) as e:
        parser.extract(p)
    assert e.value.code == "PARSE_ERROR"


# ---------------------------------------------------------------- analyzer
def test_normalize_ai_output():
    a = analyzer.normalize({"title": "T", "summary": "요약", "keywords": [str(i) for i in range(10)]})
    assert a.one_line_summary == "요약"  # summary → one_line_summary
    assert len(a.keywords) == 5            # 10개 → 5개


def test_normalize_too_few_keywords():
    a = analyzer.normalize({"title": "T", "one_line_summary": "s", "keywords": ["하나"]})
    assert len(a.keywords) == 3


def test_parse_json_in_code_block():
    raw = '```json\n{"title": "A", "summary": "B", "keywords": ["x","y","z"]}\n```'
    assert analyzer._parse_json(raw)["title"] == "A"


# ---------------------------------------------------------------- 전체 처리 (mock_store)
def test_job_with_stored_file_succeeds(tmp_path):
    p = tmp_path / "meeting.docx"
    make_docx(p)
    job = mock_store.create_job("meeting.docx", "docx", p.stat().st_size,
                                stored_path=str(p), sha256="s1", run_in_background=False)
    res = mock_store.to_response(job)
    assert res.status == JobStatus.SUCCEEDED
    assert res.schema_version == "0.2"
    assert res.extraction.char_count > 0
    assert "주간 회의록" in res.extraction.text_preview
    assert res.analysis.title == "주간 회의록"
    assert 3 <= len(res.analysis.keywords) <= 5
    assert res.error is None


def test_job_with_broken_file_fails(tmp_path):
    p = tmp_path / "broken.pptx"
    p.write_bytes(b"broken")
    job = mock_store.create_job("broken.pptx", "pptx", 6,
                                stored_path=str(p), run_in_background=False)
    res = mock_store.to_response(job)
    assert res.status == JobStatus.FAILED
    assert res.error.code == "PARSE_ERROR"
    assert res.analysis is None


def test_job_runs_in_background(tmp_path):
    import time

    p = tmp_path / "deck.pptx"
    make_pptx(p)
    job = mock_store.create_job("deck.pptx", "pptx", p.stat().st_size, stored_path=str(p))
    for _ in range(50):  # 최대 5초 대기
        if job.status() in (JobStatus.SUCCEEDED, JobStatus.FAILED):
            break
        time.sleep(0.1)
    assert job.status() == JobStatus.SUCCEEDED


def test_without_stored_path_still_mock():
    job = mock_store.create_job("a.pdf", "pdf", 10)
    assert job.status() == JobStatus.QUEUED  # 예전 모킹 그대로 (FE 연결용)
