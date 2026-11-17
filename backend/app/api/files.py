"""업로드·작업 조회 API.

BE-06: 업로드 파일을 backend/uploads/에 저장하고 sha256을 작업 정보에 기록한다.
BE-09: 빈 파일·중복 파일을 거부한다. 로그에는 문서 본문을 남기지 않는다.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.job import JobResponse, UploadedFile, UploadResponse
from app.services import mock_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["files"])

ALLOWED_EXTENSIONS = {"pptx", "docx", "hwp", "pdf"}
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50MB (BE-05에서 팀 합의 후 조정)

# backend/uploads/ (서버를 어느 폴더에서 켜도 같은 위치)
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"


def _reject(status_code: int, code: str, message: str, **extra) -> HTTPException:
    """에러 응답을 만들고 로그를 남긴다. 로그에는 파일명·에러 코드만 (본문 금지)."""
    logger.warning("upload rejected: code=%s message=%s", code, message)
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, **extra},
    )


async def _save_upload(f: UploadFile) -> UploadedFile:
    """파일 하나를 검사하고 저장한 뒤 작업을 만든다.

    검사 순서: 확장자 → 크기 → 빈 파일 → 중복 → 저장
    """
    name = f.filename or "unnamed"
    ext = Path(name).suffix.lower().lstrip(".")

    # 1) 확장자
    if ext not in ALLOWED_EXTENSIONS:
        raise _reject(
            400, "UNSUPPORTED_TYPE",
            f"{name}: 지원하지 않는 형식입니다 (pptx, docx, hwp, pdf만 가능).",
        )

    content = await f.read()
    size = len(content)

    # 2) 크기
    if size > MAX_FILE_BYTES:
        raise _reject(413, "FILE_TOO_LARGE", f"{name}: 50MB를 넘는 파일입니다.")

    # 3) 빈 파일
    if size == 0:
        raise _reject(400, "EMPTY_FILE", f"{name}: 내용이 없는 파일입니다.")

    # 4) 중복
    sha = hashlib.sha256(content).hexdigest()
    existing = mock_store.find_job_by_sha256(sha)
    if existing is not None:
        raise _reject(
            409, "DUPLICATE_FILE", f"{name}: 이미 올린 파일입니다.",
            job_id=existing.job_id,
        )

    # 5) 저장 (원래 파일명은 한글·공백 때문에 쓰지 않고 file_id로 저장)
    file_id = mock_store.new_file_id()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_path = UPLOAD_DIR / f"{file_id}.{ext}"
    stored_path.write_bytes(content)

    job = mock_store.create_job(
        filename=name,
        source_type=ext,
        size_bytes=size,
        stored_path=str(stored_path),
        sha256=sha,
        file_id=file_id,
    )
    logger.info("upload saved: filename=%s size=%d job_id=%s", name, size, job.job_id)

    return UploadedFile(
        file_id=job.file_id,
        job_id=job.job_id,
        filename=job.filename,
        source_type=job.source_type,
        size_bytes=job.size_bytes,
        status=job.status(),
    )


@router.post("/files", response_model=UploadResponse, status_code=201)
async def upload_files(files: list[UploadFile] = File(...)) -> UploadResponse:
    """여러 파일을 받아 파일마다 file_id·job_id를 발급한다."""
    uploaded: list[UploadedFile] = []
    for f in files:
        uploaded.append(await _save_upload(f))
    return UploadResponse(files=uploaded)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """작업 상태·결과를 조회한다. FE는 1~2초 간격으로 폴링하면 된다."""
    job = mock_store.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": f"{job_id} 작업을 찾을 수 없습니다."},
        )
    return mock_store.to_response(job)