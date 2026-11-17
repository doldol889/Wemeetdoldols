# 통합 테스트 샘플 · 체크리스트 (BE-06 · BE-07 · BE-09)

두 사람 PR을 main에 합친 뒤, 서버를 켜고 이 폴더의 파일로 확인한다.

## 준비

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

새 터미널을 하나 더 열고, 이 폴더(`test-samples`)로 이동해서 아래 명령을 실행한다.
(PowerShell이면 `curl` 대신 반드시 `curl.exe`)

## 샘플 파일

| 파일 | 내용 | 기대 결과 |
| --- | --- | --- |
| `sample.pptx` | 슬라이드 3장 (한글) | 201 → 잠시 후 `succeeded`, `extraction.page_count` 3 |
| `sample.docx` | 문단 2개 + 표 | 201 → `succeeded`, 본문 미리보기에 "11월 3주차 백엔드 회의록" |
| `sample.pdf` | 2페이지 (한글·영문) | 201 → `succeeded`, `extraction.page_count` 2 |
| `sample_copy.pdf` | `sample.pdf`와 **내용이 같음** | `sample.pdf` 다음에 올리면 **409 `DUPLICATE_FILE`** + 첫 번째 job_id |
| `empty.pdf` | 0바이트 | **400 `EMPTY_FILE`** |
| `image.png` | 그림 파일 | **400 `UNSUPPORTED_TYPE`** |
| `encrypted.pdf` | 암호 PDF (비밀번호 1234) | 201 → 잠시 후 **`failed`, `ENCRYPTED_FILE`** |

서버를 껐다 켜면 기록이 사라지니, 중복 테스트는 서버를 켠 채로 이어서 한다.

## 확인 체크리스트

### 1. 정상 파일 (BE-06 저장 + BE-07 추출)
- [ ] `curl.exe -F "files=@sample.pptx" http://127.0.0.1:8000/api/files` → 201, `job_id` 받기
- [ ] 브라우저 `127.0.0.1:8000/api/jobs/<job_id>` → `succeeded`
  - [ ] `extraction.text_preview`에 실제 슬라이드 글자가 보임
  - [ ] `analysis.title`, `one_line_summary`, `keywords`(3~5개) 있음
  - [ ] `review_status` = `pending`
- [ ] `backend/uploads/` 에 `<file_id>.pptx` 파일이 생김 (원래 파일명 아님)
- [ ] `sample.docx`, `sample.pdf` 도 같은 방법으로 확인
- [ ] 결과 화면 캡처 → M1 마일스톤 페이지에 첨부

### 2. 검사 (BE-09)
- [ ] `sample_copy.pdf` 업로드 → 409 `DUPLICATE_FILE`, `job_id`가 `sample.pdf`의 job_id와 같음
- [ ] `empty.pdf` 업로드 → 400 `EMPTY_FILE`
- [ ] `image.png` 업로드 → 400 `UNSUPPORTED_TYPE`
- [ ] `encrypted.pdf` 업로드 → 201 후 조회하면 `failed` + `ENCRYPTED_FILE`
- [ ] 서버 터미널 로그에 문서 본문이 찍히지 않음 (파일명·크기·job_id·에러 코드만)

### 3. 검토 저장 (BE-12)
`sample.pptx`의 job_id로 (PowerShell은 따옴표 주의 — `/docs` 화면에서 Try it out 으로 해도 됨)
- [ ] `POST /api/jobs/<job_id>/decision` 본문 `{"decision": "accept"}` → 200, `review_status` = `accepted`
- [ ] 본문 `{"decision": "modify", "edits": {"title": "새 제목"}}` → `modified`, `review_edits.title` = "새 제목"
- [ ] 분석 중인 파일에 결정 보내기 → 409 `JOB_NOT_READY`
- [ ] `GET /api/jobs?ids=<job1>,<job2>,job-nope` → `jobs` 2개 + `not_found` = `["job-nope"]`

### 4. 자동 테스트
- [ ] `python -m pytest` 전부 통과 (PDF 1개 skipped 는 괜찮음)

### 5. 마무리
- [ ] 노션 TO-DO: BE-06 · BE-09 · BE-12 완료 처리
- [ ] M1 마일스톤 페이지 백엔드 칸에 통합 테스트 결과 + 캡처
