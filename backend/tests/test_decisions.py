"""BE-12 검토 결과 저장 · 여러 작업 조회 테스트 (인애 담당)."""
import pytest

from app.schemas.job import JobStatus, ReviewEdits, ReviewStatus
from app.services import mock_store


def finished_job():
    """분석이 끝난(succeeded) 모킹 작업을 만든다."""
    job = mock_store.create_job("report.pdf", "pdf", 100)
    job.created_at -= 10  # 시간을 앞으로 돌려 succeeded 상태로
    assert job.status() == JobStatus.SUCCEEDED
    return job


# ---------------------------------------------------------------- 저장 로직 (mock_store)
def test_new_job_is_pending():
    job = finished_job()
    assert mock_store.to_response(job).review_status == ReviewStatus.PENDING


def test_accept():
    job = finished_job()
    mock_store.apply_decision(job, "accept")
    assert mock_store.to_response(job).review_status == ReviewStatus.ACCEPTED


def test_modify_saves_edits():
    job = finished_job()
    mock_store.apply_decision(job, "modify", ReviewEdits(title="새 제목", folder="과제/2학기"))
    res = mock_store.to_response(job)
    assert res.review_status == ReviewStatus.MODIFIED
    assert res.review_edits.title == "새 제목"
    assert res.review_edits.filename is None


def test_modify_without_edits_is_error():
    job = finished_job()
    with pytest.raises(mock_store.DecisionError) as e:
        mock_store.apply_decision(job, "modify", ReviewEdits())
    assert e.value.code == "INVALID_DECISION"


def test_change_mind_overwrites():
    job = finished_job()
    mock_store.apply_decision(job, "modify", ReviewEdits(title="A"))
    mock_store.apply_decision(job, "reject")
    res = mock_store.to_response(job)
    assert res.review_status == ReviewStatus.REJECTED
    assert res.review_edits is None


def test_cannot_review_before_analysis_done():
    job = mock_store.create_job("a.pdf", "pdf", 10)  # 방금 만든 작업 = queued
    with pytest.raises(mock_store.DecisionError) as e:
        mock_store.apply_decision(job, "accept")
    assert e.value.code == "JOB_NOT_READY"
    assert e.value.status_code == 409


# ---------------------------------------------------------------- API (FastAPI가 설치된 환경에서만)
@pytest.fixture
def client():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def test_api_decision_flow(client):
    job = finished_job()
    res = client.post(f"/api/jobs/{job.job_id}/decision",
                      json={"decision": "modify", "edits": {"filename": "새파일.pdf"}})
    assert res.status_code == 200
    body = res.json()
    assert body["review_status"] == "modified"
    assert body["review_edits"]["filename"] == "새파일.pdf"
    # 다시 조회해도 저장돼 있어야 함
    assert client.get(f"/api/jobs/{job.job_id}").json()["review_status"] == "modified"


def test_api_decision_errors(client):
    assert client.post("/api/jobs/job-nope/decision", json={"decision": "accept"}).status_code == 404
    queued = mock_store.create_job("b.pdf", "pdf", 10)
    res = client.post(f"/api/jobs/{queued.job_id}/decision", json={"decision": "accept"})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "JOB_NOT_READY"
    # decision 값이 틀리면 422 (FastAPI 기본 검증)
    assert client.post(f"/api/jobs/{queued.job_id}/decision", json={"decision": "maybe"}).status_code == 422


def test_api_list_jobs(client):
    a, b = finished_job(), finished_job()
    res = client.get("/api/jobs", params={"ids": f"{a.job_id},{b.job_id},job-nope"})
    assert res.status_code == 200
    body = res.json()
    assert [j["job_id"] for j in body["jobs"]] == [a.job_id, b.job_id]
    assert body["not_found"] == ["job-nope"]


# ---------------------------------------------------------------- create_job file_id 인자 (팀원 BE-06 요청)
def test_create_job_with_given_file_id():
    fid = mock_store.new_file_id()
    job = mock_store.create_job("a.pdf", "pdf", 10, file_id=fid)
    assert job.file_id == fid and fid.startswith("file-")


def test_create_job_without_file_id_still_works():
    job = mock_store.create_job("a.pdf", "pdf", 10)
    assert job.file_id.startswith("file-")