"""업로드 검사 테스트 (BE-06 저장 + BE-09 빈 파일·중복 검사).

인애가 팀원 files.py 작업 전에 '정해진 형식'대로 먼저 써 둔 테스트.
팀원 PR이 합쳐지면 통과해야 한다.

약속한 형식
  - 빈 파일            → 400, detail.code == "EMPTY_FILE"
  - 같은 내용 두 번     → 두 번째 409, detail.code == "DUPLICATE_FILE", detail.job_id == 첫 번째 job_id
  - 업로드 후           → uploads/<file_id>.<확장자> 파일 생성 (테스트 끝나면 삭제)
"""
import uuid
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import mock_store  # noqa: E402

client = TestClient(app)


def unique_bytes() -> bytes:
    """테스트끼리 중복으로 잡히지 않게 매번 다른 내용을 만든다."""
    return f"%PDF-1.4 test {uuid.uuid4().hex}".encode()


@pytest.fixture
def cleanup():
    """테스트 중 저장된 파일을 기록해 두었다가 끝나면 지운다."""
    paths: list[Path] = []
    yield paths
    for p in paths:
        try:
            p.unlink()
        except (FileNotFoundError, PermissionError):
            pass


def upload(name: str, content: bytes, mime: str = "application/pdf"):
    return client.post("/api/files", files=[("files", (name, content, mime))])


def stored_path_of(job_id: str) -> Path:
    job = mock_store.get_job(job_id)
    assert job is not None, "업로드 후 작업이 만들어져야 함"
    assert job.stored_path, "create_job 에 stored_path 를 넘겨야 함 (BE-06)"
    return Path(job.stored_path)


# ---------------------------------------------------------------- BE-06 저장
def test_upload_saves_file_as_file_id(cleanup):
    res = upload("회의록 (최종).pdf", unique_bytes())
    assert res.status_code == 201
    f = res.json()["files"][0]

    path = stored_path_of(f["job_id"])
    cleanup.append(path)
    assert path.exists(), "uploads/ 에 파일이 저장돼야 함"
    assert path.name == f"{f['file_id']}.pdf", "저장 파일명은 <file_id>.<확장자> (원래 파일명 사용 금지)"
    assert path.parent.name == "uploads"


def test_saved_file_has_same_content(cleanup):
    content = unique_bytes()
    res = upload("a.pdf", content)
    path = stored_path_of(res.json()["files"][0]["job_id"])
    cleanup.append(path)
    assert path.read_bytes() == content


def test_sha256_is_recorded(cleanup):
    import hashlib

    content = unique_bytes()
    res = upload("b.pdf", content)
    job = mock_store.get_job(res.json()["files"][0]["job_id"])
    cleanup.append(Path(job.stored_path))
    assert job.sha256 == hashlib.sha256(content).hexdigest()


# ---------------------------------------------------------------- BE-09 빈 파일
def test_empty_file_rejected():
    res = upload("empty.pdf", b"")
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "EMPTY_FILE"


# ---------------------------------------------------------------- BE-09 중복
def test_duplicate_file_returns_409_with_first_job_id(cleanup):
    content = unique_bytes()
    first = upload("original.pdf", content)
    assert first.status_code == 201
    first_job_id = first.json()["files"][0]["job_id"]
    cleanup.append(stored_path_of(first_job_id))

    second = upload("copy.pdf", content)  # 이름이 달라도 내용이 같으면 중복
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["code"] == "DUPLICATE_FILE"
    assert detail["job_id"] == first_job_id


def test_different_content_is_not_duplicate(cleanup):
    a = upload("same-name.pdf", unique_bytes())
    b = upload("same-name.pdf", unique_bytes())  # 이름이 같아도 내용이 다르면 OK
    assert a.status_code == 201 and b.status_code == 201
    for r in (a, b):
        cleanup.append(stored_path_of(r.json()["files"][0]["job_id"]))
