# WeMeet Backend (모킹 단계)

[BE-사전1] 업로드 · 작업 조회 API 뼈대와 모킹 응답입니다.
실제 DB · AI 분석이 붙기 전에도 FE가 바로 연동할 수 있게 만든 버전입니다.

## 실행

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs (여기서 바로 파일 올려보고 테스트 가능)
- 상태 확인: http://localhost:8000/health

## API (모킹)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/api/files` | 파일 여러 개 업로드 → 파일마다 `file_id`, `job_id` 발급 |
| `GET` | `/api/jobs/{job_id}` | 작업 상태 · 결과 조회 |

### 모킹 동작

- 업로드 후 **0~2초 `queued` → 2~6초 `running` → 6초 후 `succeeded`** (샘플 분석 결과 포함)
- 파일명에 `fail`이 들어가면 마지막에 `failed`로 끝남 → FE 실패 화면 테스트용
- 허용 확장자: `pptx`, `docx`, `hwp`, `pdf` / 50MB 초과 시 413
- 서버를 재시작하면 기록이 사라짐 (메모리 저장)

### curl 예시

```bash
curl -F "files=@회의록.pdf" -F "files=@발표자료.pptx" http://localhost:8000/api/files
curl http://localhost:8000/api/jobs/job-xxxxxxxx
```

## 폴더 구조

```text
app/
  main.py              # FastAPI 앱, CORS(Vite 5173)
  api/files.py         # 업로드·작업 조회 엔드포인트
  schemas/job.py       # 상태값 · 응답 스키마 (Todo.md 4.2 JSON 계약)
  services/mock_store.py  # 메모리 모킹 저장소
docs/
  be-pre1-mock-api.md  # [BE-사전1] 개발 기록 · 테스트 결과 · 이슈
  jobs-table-draft.md  # [BE-사전2] 상태값 · jobs 테이블 초안
tests/
  test_api.py          # pytest
```

## 테스트

```bash
pip install pytest httpx
pytest
```

## 다음 단계 (금요일 이후)

- BE-06: 파일을 실제로 임시 폴더에 저장, 메타데이터 DB 기록
- BE-07: `mock_store` → 실제 AI 파싱/분석 호출로 교체 (BackgroundTasks)
- BE-08: `jobs`, `llm_usage` 테이블 (SQLAlchemy) — `docs/jobs-table-draft.md` 기준
