"""작업 저장소 (메모리) + 분석 실행.

두 가지 방식으로 동작한다.

1) 실제 처리 (BE-07) — create_job 에 stored_path 가 들어오면
   뒤에서(스레드) 바로 분석을 시작한다:
       queued → running(텍스트 추출 · 분석) → succeeded / failed
   files.py 는 create_job 만 부르면 되고, 처리 시작은 여기서 알아서 한다.

2) 모킹 (BE-사전1) — stored_path 가 없으면 예전처럼 시간에 따라 상태가 바뀐다:
       0 ~ 2초 queued → 2 ~ 6초 running → 6초 이후 succeeded (샘플 결과)
   파일명에 "fail" 이 들어 있으면 failed 로 끝난다 (FE 실패 화면 테스트용).

서버를 재시작하면 기록은 사라진다 (DB는 BE-08에서).
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.schemas.job import (
    Analysis,
    ErrorInfo,
    Extraction,
    FolderCandidate,
    JobResponse,
    JobStatus,
    Recommendation,
    ReviewEdits,
    ReviewStatus,
    Section,
)

logger = logging.getLogger(__name__)

QUEUED_SECONDS = 2
RUNNING_SECONDS = 6
PREVIEW_CHARS = 300


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

    # 실제 처리 결과 (stored_path 가 있을 때만 사용)
    real_status: JobStatus = JobStatus.QUEUED
    error: Optional[ErrorInfo] = None
    analysis: Optional[Analysis] = None
    extraction: Optional[Extraction] = None

    # 사용자 검토 결과 (BE-12)
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_edits: Optional[ReviewEdits] = None

    def status(self, now: Optional[float] = None) -> JobStatus:
        if self.stored_path:
            return self.real_status
        # ---- 모킹 (stored_path 없음)
        elapsed = (now if now is not None else time.monotonic()) - self.created_at
        if elapsed < QUEUED_SECONDS:
            return JobStatus.QUEUED
        if elapsed < RUNNING_SECONDS:
            return JobStatus.RUNNING
        if "fail" in self.filename.lower():
            return JobStatus.FAILED
        return JobStatus.SUCCEEDED


_jobs: dict[str, MockJob] = {}
def new_file_id() -> str:
    """file_id 를 미리 만든다. files.py 가 uploads/<file_id>.<확장자> 로 먼저 저장할 때 사용."""
    return f"file-{uuid.uuid4().hex[:8]}"


def create_job(
    filename: str,
    source_type: str,
    size_bytes: int,
    stored_path: Optional[str] = None,
    sha256: Optional[str] = None,
    run_in_background: bool = True,
    file_id: Optional[str] = None,
) -> MockJob:
    job = MockJob(
        file_id=file_id or new_file_id(),
        job_id=f"job-{uuid.uuid4().hex[:8]}",
        filename=filename,
        source_type=source_type,
        size_bytes=size_bytes,
        stored_path=stored_path,
        sha256=sha256,
    )
    _jobs[job.job_id] = job
    if stored_path:
        if run_in_background:
            threading.Thread(target=process_job, args=(job,), daemon=True).start()
        else:  # 테스트에서 바로 결과를 확인할 때
            process_job(job)
    return job


def get_job(job_id: str) -> Optional[MockJob]:
    return _jobs.get(job_id)


def find_job_by_sha256(sha256: str) -> Optional[MockJob]:
    """같은 내용의 파일로 만든 작업이 이미 있으면 돌려준다 (BE-09 중복 확인용)."""
    for job in _jobs.values():
        if job.sha256 == sha256:
            return job
    return None


# ---------------------------------------------------------------- 검토 결과 저장 (BE-12)
class DecisionError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def apply_decision(job: MockJob, decision: str, edits: Optional[ReviewEdits] = None) -> None:
    """수락 / 수정 / 거부를 저장한다. 다시 누르면 마지막 결정으로 덮어쓴다."""
    if job.status() != JobStatus.SUCCEEDED:
        raise DecisionError(409, "JOB_NOT_READY", "분석이 끝난 파일만 검토할 수 있습니다.")

    if decision == "accept":
        job.review_status = ReviewStatus.ACCEPTED
        job.review_edits = None
    elif decision == "reject":
        job.review_status = ReviewStatus.REJECTED
        job.review_edits = None
    elif decision == "modify":
        if edits is None or not any([edits.title, edits.filename, edits.folder]):
            raise DecisionError(400, "INVALID_DECISION", "수정할 값(title, filename, folder 중 하나 이상)을 보내 주세요.")
        job.review_status = ReviewStatus.MODIFIED
        job.review_edits = edits
    else:
        raise DecisionError(400, "INVALID_DECISION", f"알 수 없는 결정입니다: {decision}")


# ---------------------------------------------------------------- 실제 처리 (BE-07)
def process_job(job: MockJob) -> None:
    """저장된 파일에서 텍스트를 추출하고 분석한다. 결과는 job 에 기록."""
    from app.services import analyzer, parser  # 순환 import 방지

    job.real_status = JobStatus.RUNNING
    try:
        result = parser.extract(job.stored_path)
        job.extraction = Extraction(
            page_count=result.page_count,
            char_count=len(result.text),
            text_preview=result.text[:PREVIEW_CHARS],
        )
        job.analysis = analyzer.analyze(result.text, job.filename)
        job.real_status = JobStatus.SUCCEEDED
        logger.info("job %s succeeded (%s, %d chars)", job.job_id, job.source_type, len(result.text))
    except parser.ParseError as e:
        job.error = ErrorInfo(code=e.code, message=e.message)
        job.real_status = JobStatus.FAILED
        logger.info("job %s failed: %s", job.job_id, e.code)
    except Exception as e:  # 예상 못 한 오류 — 문서 내용은 로그에 남기지 않는다
        job.error = ErrorInfo(code="PARSE_ERROR", message="분석 중 알 수 없는 오류가 발생했습니다.")
        job.real_status = JobStatus.FAILED
        logger.exception("job %s failed unexpectedly: %s", job.job_id, type(e).__name__)


# ---------------------------------------------------------------- 응답 만들기
def to_response(job: MockJob, now: Optional[float] = None) -> JobResponse:
    status = job.status(now)
    response = JobResponse(
        file_id=job.file_id,
        job_id=job.job_id,
        source_type=job.source_type,
        status=status,
        review_status=job.review_status,
        review_edits=job.review_edits,
    )

    if job.stored_path:  # ---- 실제 처리 결과
        if status == JobStatus.FAILED:
            response.error = job.error
        elif status == JobStatus.SUCCEEDED:
            response.analysis = job.analysis
            response.extraction = job.extraction
            # 파일명 · 폴더 추천은 BE-10 / AI-26 이후 — 지금은 샘플 유지
            response.recommendation = _sample_recommendation(job.filename, job.source_type)
        return response

    # ---- 모킹
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
