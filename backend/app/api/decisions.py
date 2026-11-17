"""검토 결과 저장 · 여러 작업 조회 API (BE-12, M2).

FE 검토 화면:
  - 파일마다 [수락] [수정] [거부] → POST /api/jobs/{job_id}/decision
  - 아래 진행 바 · 분석 화면의 "검토 완료" 표시 → 조회 결과의 review_status
FE 분석 화면:
  - 파일이 여러 개일 때 한 번에 상태 확인 → GET /api/jobs?ids=job-a,job-b
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.job import DecisionRequest, JobListResponse, JobResponse
from app.services import mock_store

router = APIRouter(prefix="/api", tags=["review"])

MAX_IDS = 50


@router.post("/jobs/{job_id}/decision", response_model=JobResponse)
async def save_decision(job_id: str, body: DecisionRequest) -> JobResponse:
    """수락 / 수정 / 거부를 저장하고, 바뀐 작업 정보를 돌려준다.

    요청 예시
      {"decision": "accept"}
      {"decision": "modify", "edits": {"title": "새 제목", "filename": "새파일명.pdf", "folder": "과제/2학기"}}
      {"decision": "reject"}
    """
    job = mock_store.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": f"{job_id} 작업을 찾을 수 없습니다."},
        )
    try:
        mock_store.apply_decision(job, body.decision, body.edits)
    except mock_store.DecisionError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})
    return mock_store.to_response(job)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(ids: str = Query(..., description="쉼표로 구분한 job_id 목록, 예: job-a,job-b")) -> JobListResponse:
    """여러 작업의 상태 · 결과를 한 번에 조회한다. 없는 id는 not_found 에 담는다."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list or len(id_list) > MAX_IDS:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_IDS", "message": f"job_id를 1~{MAX_IDS}개 보내 주세요."},
        )
    jobs, not_found = [], []
    for job_id in id_list:
        job = mock_store.get_job(job_id)
        if job is None:
            not_found.append(job_id)
        else:
            jobs.append(mock_store.to_response(job))
    return JobListResponse(jobs=jobs, not_found=not_found)
