"""작업(Job)·분석 결과 응답 스키마.

Todo.md 4.2 "권장 API·데이터 계약" JSON을 그대로 따른다.
필드명은 금요일 회의에서 FE·AI와 확정하기 전까지 '초안'이며,
바뀌면 SCHEMA_VERSION 을 올린다.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "0.3"  # 0.2: extraction 추가 · 0.3: review(검토 결과) 추가 (11/17)


class JobStatus(str, Enum):
    """작업 상태값 (BE-사전2). 자세한 전이 규칙은 docs/jobs-table-draft.md 참고."""

    QUEUED = "queued"        # 업로드 완료, 분석 대기 중
    RUNNING = "running"      # 파싱/LLM 분석 진행 중
    SUCCEEDED = "succeeded"  # 분석 완료, analysis 채워짐
    FAILED = "failed"        # 실패, error 채워짐


class ReviewStatus(str, Enum):
    """사용자 검토 상태 (BE-12). FE 검토 화면의 수락 / 수정 / 거부."""

    PENDING = "pending"    # 아직 검토 안 함 (분석 완료 후 기본값)
    ACCEPTED = "accepted"  # AI 추천 그대로 수락
    MODIFIED = "modified"  # 사용자가 고쳐서 저장
    REJECTED = "rejected"  # 거부 (정리하지 않음)


class ErrorInfo(BaseModel):
    code: str = Field(..., examples=["PARSE_ERROR"])
    message: str = Field(..., examples=["암호화된 PDF는 분석할 수 없습니다."])


class Section(BaseModel):
    heading: str
    summary: str
    source_page: Optional[int] = None


class Analysis(BaseModel):
    title: str
    one_line_summary: str
    keywords: list[str] = Field(..., min_length=3, max_length=5)
    sections: list[Section] = []
    visual_captions: list[str] = []
    category: Optional[str] = None


class Extraction(BaseModel):
    """실제 텍스트 추출 결과 요약 (BE-07, schema 0.2)."""

    page_count: int
    char_count: int
    text_preview: str  # 본문 앞 300자


class FolderCandidate(BaseModel):
    path: str
    rank: int = Field(..., ge=1, le=3)


class Recommendation(BaseModel):
    filename: str
    folder_candidates: list[FolderCandidate] = Field(..., max_length=3)


class ReviewEdits(BaseModel):
    """사용자가 '수정'할 때 바꾼 값. 안 바꾼 칸은 비워 둔다."""

    title: Optional[str] = None
    filename: Optional[str] = None
    folder: Optional[str] = None


class JobResponse(BaseModel):
    """GET /api/jobs/{job_id} 응답."""

    schema_version: str = SCHEMA_VERSION
    file_id: str
    job_id: str
    source_type: str
    status: JobStatus
    error: Optional[ErrorInfo] = None
    analysis: Optional[Analysis] = None
    recommendation: Optional[Recommendation] = None
    extraction: Optional[Extraction] = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_edits: Optional[ReviewEdits] = None


class DecisionRequest(BaseModel):
    """POST /api/jobs/{job_id}/decision 요청 본문."""

    decision: Literal["accept", "modify", "reject"]
    edits: Optional[ReviewEdits] = None


class UploadedFile(BaseModel):
    file_id: str
    job_id: str
    filename: str
    source_type: str
    size_bytes: int
    status: JobStatus


class UploadResponse(BaseModel):
    """POST /api/files 응답."""

    schema_version: str = SCHEMA_VERSION
    files: list[UploadedFile]


class JobListResponse(BaseModel):
    """GET /api/jobs?ids=... 응답 (여러 작업 한 번에 조회)."""

    schema_version: str = SCHEMA_VERSION
    jobs: list[JobResponse]
    not_found: list[str] = []
