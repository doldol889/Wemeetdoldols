"""모킹용 메모리 저장소 (BE-사전1).

실제 DB(BE-02)·AI 분석(BE-07) 연결 전까지 FE가 쓸 수 있도록,
업로드된 파일 정보를 메모리에 두고 시간이 지나면 상태가 바뀌는 것처럼 흉내 낸다.

    0 ~ 2초   queued
    2 ~ 6초   running
    6초 이후  succeeded (샘플 분석 결과)

파일명에 "fail" 이 들어 있으면 failed 로 끝나서 FE 실패 화면도 확인할 수 있다.
서버를 재시작하면 기록은 사라진다.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.schemas.job import (
    Analysis,
    ErrorInfo,
    FolderCandidate,
    JobResponse,
    JobStatus,
    Recommendation,
    Section,
)

QUEUED_SECONDS = 2
RUNNING_SECONDS = 6


@dataclass
class MockJob:
    file_id: str
    job_id: str
    filename: str
    source_type: str
    size_bytes: int
    stored_path: Optional[str] = None  # BE-06: uploads/ 에 저장된 경로
    sha256: Optional[str] = None       # BE-09: 중복 확인용
    created_at: float = field(default_factory=time.monotonic)

    def status(self, now: Optional[float] = None) -> JobStatus:
        elapsed = (now if now is not None else time.monotonic()) - self.created_at
        if elapsed < QUEUED_SECONDS:
            return JobStatus.QUEUED
        if elapsed < RUNNING_SECONDS:
            return JobStatus.RUNNING
        if "fail" in self.filename.lower():
            return JobStatus.FAILED
        return JobStatus.SUCCEEDED


_jobs: dict[str, MockJob] = {}


def create_job(
    filename: str,
    source_type: str,
    size_bytes: int,
    stored_path: Optional[str] = None,
    sha256: Optional[str] = None,
) -> MockJob:
    job = MockJob(
        file_id=f"file-{uuid.uuid4().hex[:8]}",
        job_id=f"job-{uuid.uuid4().hex[:8]}",
        filename=filename,
        source_type=source_type,
        size_bytes=size_bytes,
        stored_path=stored_path,
        sha256=sha256,
    )
    _jobs[job.job_id] = job
    return job


def get_job(job_id: str) -> Optional[MockJob]:
    return _jobs.get(job_id)


def find_job_by_sha256(sha256: str) -> Optional[MockJob]:
    """같은 내용의 파일로 만든 작업이 이미 있으면 돌려준다 (BE-09 중복 확인용)."""
    for job in _jobs.values():
        if job.sha256 == sha256:
            return job
    return None


def to_response(job: MockJob, now: Optional[float] = None) -> JobResponse:
    status = job.status(now)
    response = JobResponse(
        file_id=job.file_id,
        job_id=job.job_id,
        source_type=job.source_type,
        status=status,
    )
    if status == JobStatus.FAILED:
        response.error = ErrorInfo(
            code="PARSE_ERROR",
            message="(모킹) 문서를 읽는 중 오류가 발생했습니다.",
        )
    elif status == JobStatus.SUCCEEDED:
        response.analysis = _sample_analysis(job.filename)
        response.recommendation = _sample_recommendation(job.filename, job.source_type)
    return response


def _sample_analysis(filename: str) -> Analysis:
    return Analysis(
        title=f"(모킹) {filename} 분석 결과",
        one_line_summary="일정 및 개발 역할을 정리한 문서",
        keywords=["회의", "일정", "역할"],
        sections=[Section(heading="개요", summary="회의 목적과 논의 항목", source_page=1)],
        visual_captions=[],
        category="회의록",
    )


def _sample_recommendation(filename: str, source_type: str) -> Recommendation:
    return Recommendation(
        filename=f"2026-11-13_프로젝트_회의록.{source_type}",
        folder_candidates=[
            FolderCandidate(path="프로젝트/회의록", rank=1),
            FolderCandidate(path="회의자료", rank=2),
            FolderCandidate(path="문서/프로젝트", rank=3),
        ],
    )
