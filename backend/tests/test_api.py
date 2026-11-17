from fastapi.testclient import TestClient

from app.main import app
from app.services import mock_store

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
    assert body["schema_version"] == "0.1"
    assert len(body["files"]) == 2
    first = body["files"][0]
    assert first["status"] == "queued"

    job = client.get(f"/api/jobs/{first['job_id']}").json()
    assert job["file_id"] == first["file_id"]
    assert job["status"] in {"queued", "running", "succeeded"}


def test_job_finishes_with_analysis():
    res = client.post("/api/files", files=[("files", ("a.docx", b"x", "application/octet-stream"))])
    job_id = res.json()["files"][0]["job_id"]
    mock_store.get_job(job_id).created_at -= 10  # 시간을 앞으로 돌림
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "succeeded"
    assert len(job["analysis"]["keywords"]) >= 3
    assert len(job["recommendation"]["folder_candidates"]) == 3


def test_failed_file():
    res = client.post("/api/files", files=[("files", ("fail_test.pdf", b"x", "application/pdf"))])
    job_id = res.json()["files"][0]["job_id"]
    mock_store.get_job(job_id).created_at -= 10
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert job["error"]["code"] == "PARSE_ERROR"


def test_rejects_unsupported_type():
    res = client.post("/api/files", files=[("files", ("photo.png", b"x", "image/png"))])
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "UNSUPPORTED_TYPE"


def test_unknown_job_404():
    assert client.get("/api/jobs/job-nope").status_code == 404
