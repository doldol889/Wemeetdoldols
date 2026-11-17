"""WeMeet 백엔드 진입점.

실행:  uvicorn app.main:app --reload
문서:  http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import decisions, files

app = FastAPI(
    title="WeMeet API",
    description="AI 기반 파일 자동 분류 및 정리 시스템 — 모킹 단계 (schema 0.1)",
    version="0.1.0",
)

# 프론트엔드(Vite 기본 포트) 로컬 개발용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router)
app.include_router(decisions.router)  # BE-12 검토 결과 저장 · 여러 작업 조회


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}
