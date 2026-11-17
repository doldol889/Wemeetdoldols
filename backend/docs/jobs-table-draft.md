# [BE-사전2] 작업 상태값 · jobs 테이블 초안

> 금요일(11/13) 회의에서 FE·AI와 확정할 **초안**입니다. 확정되면 `app/schemas/job.py`의 `SCHEMA_VERSION`을 올립니다.

## 1. 작업 상태값 (`status`)

| 값 | 의미 | 누가 바꾸나 | FE 표시 |
|---|---|---|---|
| `queued` | 업로드 완료, 분석 대기 | BE (업로드 직후) | 대기 중 |
| `running` | 파싱 · LLM 분석 진행 중 | BE (AI 모듈 호출 시작) | 분석 중 (스피너) |
| `succeeded` | 분석 완료, `analysis` 채워짐 | BE (AI 결과 저장 후) | 완료 → 결과 보기 버튼 |
| `failed` | 실패, `error` 채워짐 | BE (예외 발생 시) | 실패 + 사유 + 재시도 버튼 |

### 상태 전이

```text
queued ──▶ running ──▶ succeeded
              │
              └──────▶ failed ──(재시도)──▶ queued
```

- `succeeded`, `failed` 는 최종 상태 — 더 이상 바뀌지 않음 (재시도는 **새 job** 생성 권장)
- 재시도 횟수는 `attempt` 컬럼으로 관리

### 실패 코드 (`error.code`) 초안

| 코드 | 상황 |
|---|---|
| `UNSUPPORTED_TYPE` | pptx/docx/hwp/pdf 외 형식 |
| `FILE_TOO_LARGE` | 크기 제한 초과 |
| `PARSE_ERROR` | 문서 파싱 실패 (손상 파일, 빈 문서 등) |
| `ENCRYPTED_FILE` | 암호화된 PDF/HWP |
| `LLM_ERROR` | Claude API 오류 · 재시도 소진 |
| `RATE_LIMITED` | API 사용량 제한 |

## 2. jobs 테이블 초안 (SQLite / SQLAlchemy)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | TEXT PK | `job-xxxxxxxx` |
| `document_id` | TEXT FK → documents.id | 어떤 파일의 작업인지 |
| `status` | TEXT | `queued` / `running` / `succeeded` / `failed` |
| `attempt` | INTEGER | 시도 횟수 (기본 1) |
| `error_code` | TEXT NULL | 실패 시 코드 |
| `error_message` | TEXT NULL | 실패 시 사용자용 메시지 (원문 내용 X) |
| `result_json` | TEXT NULL | AI 분석 결과 JSON (`analysis` + `recommendation`) |
| `model_name` | TEXT NULL | 사용한 Claude 모델 (BE-08 `llm_usage`와 연결) |
| `created_at` | DATETIME | 생성 시각 |
| `started_at` | DATETIME NULL | running 진입 시각 |
| `finished_at` | DATETIME NULL | succeeded/failed 시각 |

### 함께 필요한 documents 테이블 (최소)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | TEXT PK | `file-xxxxxxxx` |
| `original_name` | TEXT | 업로드한 파일명 |
| `source_type` | TEXT | pptx / docx / hwp / pdf |
| `size_bytes` | INTEGER | 크기 |
| `stored_path` | TEXT | 서버 임시 저장 경로 (BE-05) |
| `sha256` | TEXT | 중복 업로드 확인용 (BE-09) |
| `created_at` | DATETIME | 업로드 시각 |

## 3. 결정 사항 (11/17 확정)

- [x] 상태값은 4개(`queued` / `running` / `succeeded` / `failed`)로 확정 — MVP에 취소 기능 없음
- [x] 실패 재시도는 **새 job 생성** — 실패 기록 보존
- [x] FE 상태 확인은 **2초 간격 폴링**으로 시작 (SSE는 Auto-save 단계에서 검토)
- [x] 파일 크기 제한 **50MB** 유지
- [x] 결과 JSON 필드 확정 (`schema_version` 0.2)
  - `analysis`: `title`, `one_line_summary`, `keywords`(3~5개), `sections`, `visual_captions`, `category`
  - AI 응답이 `summary`로 오면 백엔드가 `one_line_summary`로 변환, 키워드 5개 초과 시 앞 5개 사용
  - 신규 `extraction`: `page_count`, `char_count`, `text_preview`(본문 앞 300자) — BE-07에서 추가
- [x] 에러 코드 추가: `EMPTY_FILE`(빈 파일), `DUPLICATE_FILE`(중복 파일, 409 + 기존 `job_id` 반환)
