"""업로드·작업 조회 API 뼈대 (BE-사전1 → 이후 BE-06/BE-07로 확장).

지금은 파일 내용을 저장하지 않고 이름·크기만 기록해 모킹 응답을 돌려준다.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.job import JobResponse, UploadedFile, UploadResponse
from app.services import mock_store

router = APIRouter(prefix="/api", tags=["files"])

ALLOWED_EXTENSIONS = {"pptx", "docx", "hwp", "pdf"}
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50MB (BE-05에서 팀 합의 후 조정)


@router.post("/files", response_model=UploadResponse, status_code=201)
async def upload_files(files: list[UploadFile] = File(...)) -> UploadResponse:
    """여러 파일을 받아 파일마다 file_id·job_id를 발급한다."""
    uploaded: list[UploadedFile] = []
    for f in files:
        name = f.filename or "unnamed"
        ext = Path(name).suffix.lower().lstrip(".")
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "UNSUPPORTED_TYPE",
                    "message": f"{name}: 지원하지 않는 형식입니다 (pptx, docx, hwp, pdf만 가능).",
                },
            )
        size = len(await f.read())
        if size > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail={"code": "FILE_TOO_LARGE", "message": f"{name}: 50MB를 넘는 파일입니다."},
            )
        job = mock_store.create_job(filename=name, source_type=ext, size_bytes=size)
        uploaded.append(
            UploadedFile(
                file_id=job.file_id,
                job_id=job.job_id,
                filename=job.filename,
                source_type=job.source_type,
                size_bytes=job.size_bytes,
                status=job.status(),
            )
        )
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
