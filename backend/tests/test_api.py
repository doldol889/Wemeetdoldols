from app.schemas.job import SCHEMA_VERSION
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.services import mock_store
import functools
import uuid
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "test-samples"


@pytest.fixture
def sync_jobs(monkeypatch):
    """업로드 직후 분석까지 바로 끝나게 한다 (create_job의 run_in_background=False 사용)."""
    monkeypatch.setattr(
        mock_store, "create_job",
        functools.partial(mock_store.create_job, run_in_background=False),
    )


def _remove_stored(job_id: str) -> None:
    """테스트가 uploads/에 저장한 파일을 지운다."""
    job = mock_store.get_job(job_id)
    if job and job.stored_path:
        Path(job.stored_path).unlink(missing_ok=True)

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_upload_and_poll_job():
    res = client.post(
        "/api/files",
        files=[
            ("files", ("회의록.pdf", b"%PDF-1.4 dummy", "application/pdf")),
            ("files", ("발표.pptx", b"dummy", "application/octet-stream")),
        ],
    )
    assert res.status_code == 201
    body = res.json()
    assert body["schema_version"] == SCHEMA_VERSION
    assert len(body["files"]) == 2
    first = body["files"][0]
    assert first["status"] in ("queued", "running")

    job = client.get(f"/api/jobs/{first['job_id']}").json()
    assert job["file_id"] == first["file_id"]
    assert job["status"] in {"queued", "running", "succeeded"}


def test_job_finishes_with_analysis(sync_jobs):
    sample = next(SAMPLES_DIR.glob("*.docx"), None)
    if sample is None:
        pytest.skip("test-samples/에 docx 샘플이 없음")
    res = client.post(
        "/api/files",
        files=[("files", (sample.name, sample.read_bytes(), "application/octet-stream"))],
    )
    assert res.status_code == 201, res.text
    job_id = res.json()["files"][0]["job_id"]
    try:
        job = client.get(f"/api/jobs/{job_id}").json()
        assert job["status"] == "succeeded", job.get("error")
        assert len(job["analysis"]["keywords"]) >= 3
        assert len(job["recommendation"]["folder_candidates"]) == 3
    finally:
        _remove_stored(job_id)


def test_failed_file(sync_jobs):
    content = f"not a real pdf {uuid.uuid4().hex}".encode()  # 매번 다른 내용 → 중복 안 걸림
    res = client.post("/api/files", files=[("files", ("fail_test.pdf", content, "application/pdf"))])
    assert res.status_code == 201, res.text
    job_id = res.json()["files"][0]["job_id"]
    try:
        job = client.get(f"/api/jobs/{job_id}").json()
        assert job["status"] == "failed"
        assert job["error"]["code"] == "PARSE_ERROR"
    finally:
        _remove_stored(job_id)

def test_rejects_unsupported_type():
    res = client.post("/api/files", files=[("files", ("photo.png", b"x", "image/png"))])
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "UNSUPPORTED_TYPE"


def test_unknown_job_404():
    assert client.get("/api/jobs/job-nope").status_code == 404
