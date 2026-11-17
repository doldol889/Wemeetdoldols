# [BE-사전1] 업로드·작업 조회 API 뼈대 + 모킹 응답

- 담당: 성인애 (백엔드)
- 완료: 2026-11-09 · 로컬에서 업로드 → 상태 조회 → 분석 결과 응답까지 동작 확인
- 한 줄 요약: 실제 AI 분석 전에, FE·AI가 기다리지 않고 바로 연동할 수 있도록 **파일 접수 창구(API)를 모킹으로 먼저 구현**

## 왜 했나

- 실제 파일 분석은 AI 파트 담당이라 아직 없음 → 백엔드가 **정해진 샘플 결과를 돌려주는 가짜 서버**를 먼저 만듦
- FE는 이 주소에 바로 붙여 업로드·"분석 중" 화면 개발 가능, AI는 결과를 어떤 JSON 형식으로 주면 되는지 미리 확인 가능
- 나중에 AI가 완성되면 **샘플 결과 부분만 실제 분석 호출로 교체** (BE-07)

## 만든 API

| 메서드 | 경로 | 역할 |
| --- | --- | --- |
| POST | `/api/files` | 파일 여러 개 업로드 → 파일마다 `file_id` · `job_id` 발급 |
| GET | `/api/jobs/{job_id}` | 작업 상태 · 분석 결과 조회 |
| GET | `/health` | 서버 상태 확인 |

## 모킹 동작

- 업로드 후 **0~2초 `queued` → 2~6초 `running` → 6초 후 `succeeded`** (샘플 분석 결과 포함)
- 파일명에 `fail`이 들어가면 `failed`로 끝남 → FE 실패 화면 테스트용
- 허용 형식: pptx · docx · hwp · pdf / 50MB 초과 시 거부
- 응답 JSON은 TODO.md 4.2 데이터 계약 형식(`schema_version` 0.1) 그대로
- 서버 재시작 시 기록 사라짐 (아직 DB 없음, 메모리 저장)

## 테스트 결과

**1) 업로드** — VS Code 새 터미널에서 실행

```bash
curl.exe -F "files=@파일경로.pdf" http://127.0.0.1:8000/api/files
```

```json
{"schema_version":"0.1","files":[{"file_id":"file-39219f5e","job_id":"job-5c232c85","filename":"pose_v1 관절 추출 결과 안내 (B → C).pdf","source_type":"pdf","size_bytes":176241,"status":"queued"}]}
```

**2) 상태 조회** — 브라우저에서 `127.0.0.1:8000/api/jobs/job-5c232c85`

- `status: succeeded`, `error: null`
- `analysis`: 제목 · 한 줄 요약 · 키워드 3개 · 섹션 반환 확인
- `recommendation`: 추천 파일명 + 폴더 후보 3개(rank 1~3) 반환 확인
- 한글 · 공백 · 특수문자(→) 파일명도 정상 처리

## 이슈 · 메모

- **/docs 화면에서 여러 파일 업로드 불가** — 최신 FastAPI 문서 화면이 파일 배열을 글자 입력칸으로 표시함. 코드 문제 아님 → `curl.exe`로 테스트 (단일 파일 업로드 테스트용 주소 추가 예정)
- PowerShell에서는 `curl`이 아니라 **`curl.exe`**로 입력해야 함
- 브라우저 주소창에 `/api/files` 입력 시 `Method Not Allowed` → 업로드(POST)는 터미널, 조회(GET)는 브라우저
- 새 PC 세팅 시: Python 3.12 설치(Add to PATH 체크) + Windows 설정 → 앱 실행 별칭에서 python.exe · python3.exe 끄기
- OneDrive 폴더 안에서 가상환경 사용 시 동기화로 느려질 수 있음 → OneDrive 밖 경로 권장

## 다음 단계

- [ ] JSON 형식 · 상태값 확정 (FE·AI와 합의, `docs/jobs-table-draft.md` 참고)
- [ ] BE-06: 업로드 파일 실제 저장 + 메타데이터 기록
- [ ] BE-07: 모킹 → 실제 AI 파싱 · 분석 호출로 교체
- [ ] BE-09: 빈 파일 · 손상 파일 · 중복 업로드 검증
- [ ] (선택) /docs 테스트용 단일 파일 업로드 주소 추가
