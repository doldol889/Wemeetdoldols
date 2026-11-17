# Product Requirement Document (PRD)

## 프로젝트명: 위밋 (WeMeet) - AI 기반 파일 자동 분류 및 정리 시스템

---

## 1. 개요 (Overview)

### 1.1 배경 및 문제 정의
* **디지털 데이터 급증:** 개인 PC 및 클라우드 내 파일 수의 지속적 증가로 인한 파일 관리 한계 직면.
* **수작업 정리의 비효율성:** 폴더 생성, 파일명 지정, 카테고리 분류 등 수동 관리에 소요되는 시간과 비용 증가.
* **비일관적/불명확한 파일명:** `최종_진짜최종_v3.pptx`와 같이 실제 내용을 반영하지 못하는 파일명으로 인해 필요한 정보 재검색 난항.
* **기존 도구의 한계:** 확장자, 생성일 등 표면적 메타데이터에 의존하며, 파일의 '실제 문맥과 내용'에 기반한 자동 분류 기능 부재.

### 1.2 목적
* Anthropic의 **Claude** 모델(텍스트·이미지·PDF 입력 지원)을 API로 연동하여 다양한 문서(PPTX, DOCX, HWP, PDF)의 본문 및 시각 자료를 정밀 분석. 별도 비전 모델 없이 Claude 하나로 텍스트 분석과 차트/도표 해석을 모두 처리.
* 의미 있는 표준 파일명 추천, 폴더 구조 제안, 자동 요약 및 Notion 구조화 페이지 변환 시스템 구축.
* 품질 검증(QA)을 위한 **자동/반자동 더미 데이터 생성 파이프라인**을 구축하여 시스템 정확도 및 안정성 확보.
* 상용 LLM API 활용으로 GPU 장비·모델 서빙 없이 빠르게 구축하고, AI 호출 계층은 어댑터로 분리하여 향후 다른 모델(로컬 오픈소스 모델 포함)로 교체 가능하게 설계.
* 문서가 외부 API로 전송되는 점을 고려하여 사용자 동의 절차와 API 사용량·비용 관리 체계를 함께 구축.

---

## 2. 사용자 페르소나 및 목표 (User Personas & Goals)

1. **개인 사용자 (학생/직장인):**
   * **Goal:** 무분별하게 쌓인 기존 파일을 AI 승인 기반으로 일괄 정리하고, 신규 다운로드 파일의 표준 파일명 및 추천 저장 위치를 제공받아 파일 정리 시간 $50\%$ 이상 단축.
2. **팀/조직 관리자:**
   * **Goal:** 팀 공통 네이밍 컨벤션 및 폴더 구조 규칙을 전체 팀원에게 동기화하고, 팀 공유 드라이브 내 이름 충돌 및 중복 파일을 자동 관리.
3. **QA 엔지니어 및 AI 개발자:**
   * **Goal:** 실제 환경과 유사한 대규모 더미 문서 데이터셋(200~500개)을 활용해 분류 모델의 Precision, Recall, F1-Score 및 시스템 응답 속도를 반복 측정 및 검증.

---

## 3. 핵심 목표 및 단계별 추진 범위 (Milestones & Scope)

### 3.1 [1차 목표] MVP - 레거시 파일 Notion AI 구조화 변환 (Cleanup Mode)
* **내용:** PPT, DOCX, HWP, PDF 레거시 파일 파싱 $\rightarrow$ **Claude** 기반 내용 분석 $\rightarrow$ Notion 검색 가능 구조화 페이지 자동 변환.
* **핵심 기능:** 트리 구조 검토 UI를 통한 승인 기반 처리(수락/수정/거부) 및 백업/롤백 지원.

### 3.2 [2차 목표] Auto-save Mode - 신규 파일 반자동 관리 & 자동 요약
* **내용:** PC 특정 폴더(다운로드, 바탕화면) 이벤트 실시간 감지 $\rightarrow$ 신규 파일의 키워드 기반 표준 파일명 및 저장 폴더 상위 3개 추천.
* **배포 연동:** 파일 생성 즉시 자동 요약본을 작성하여, 사용자가 사전에 활성화·동의한 Slack Webhook 또는 Notion 채널에 한해 팀원에게 자동 공유.

### 3.3 [3차 목표] Team Collaboration Mode - 팀 공유 드라이브 확장
* **내용:** Google Drive, OneDrive, NAS 등에 공통 분류 규칙(YAML/JSON) 동기화, 이름 충돌/중복 파일 탐지.
* **시각화:** 팀 파일 저장 현황 통계 대시보드 및 축적된 피드백 학습을 통한 분류 규칙 자동 개선 제안.

---

## 4. 세부 기능 요구사항 (Functional Requirements)

| 모듈 ID | 기능명 | 세부 설명 | 우선순위 |
| :--- | :--- | :--- | :--- |
| **FR-01** | 문서 파싱 파이프라인 | `python-pptx`, `python-docx`, `pyhwpx`/`pyhwp`, `pypdf`/`pdfplumber`를 사용하여 텍스트, 이미지, 표, 목차 추출 및 중간 JSON 정규화 (HWPX 지원 여부는 별도 확인) | High (MVP) |
| **FR-02** | Claude 구조화 | 정규화 텍스트를 **Claude API**에 입력하여 제목 추론, 한 줄 요약, 키워드(3~5개), 목차 및 섹션 요약 JSON 생성. 출력은 tool use(JSON 스키마 지정)로 형식 강제. 매우 긴 문서는 비용·지연을 고려해 섹션 단위 분할 후 통합 요약 | High (MVP) |
| **FR-03** | 차트/도표 이미지 분석 | 문서 내 차트/도표 이미지를 추출하여 Claude API에 이미지로 함께 입력, 설명 캡션 텍스트 생성 (별도 비전 모델 불필요) | High (MVP) |
| **FR-04** | Notion API/MCP 연동 | LLM 출력 JSON을 Notion 블록(Heading, Callout, TOC, Image 등)으로 매핑하여 자동 업로드. Notion API 제한(요청당 블록 수, rich text 길이)에 맞춘 분할 전송, 이미지는 Notion 파일 업로드 기능 또는 외부 URL 사용 | High (MVP) |
| **FR-05** | Cleanup 검토 UI & 롤백 | 정리 제안 결과를 트리 구조로 시각화하고 사용자 수락/수정/거부 적용 및 롤백 기능 제공 | High (MVP) |
| **FR-06** | **QA 더미 데이터 생성기** | **QA 평가를 위한 다양한 포맷(PPT, DOCX, HWP, PDF)의 비정형 테스트 문서(200~500개) 및 모의 메타데이터 자동 생성 파이프라인 구축** | **High (MVP)** |
| **FR-07** | 실시간 파일 감지 | `watchdog` 기반 지정 폴더 파일 생성/이동/복사 이벤트 실시간 감지 및 추천 알림 UI 실행 | Medium |
| **FR-08** | 자동 요약 및 배포 | Webhook 기반 신규 문서 업로드 감지 시 핵심 요약 작성 후 Slack/Notion으로 자동 전송 | Medium |
| **FR-09** | 팀 규칙 동기화 & 대시보드 | 관리자 규칙(YAML/JSON) 동기화, 중복 파일 탐지, 팀 활동 시각화 대시보드 구축 | Low |
| **FR-10** | 피드백 기반 추천 고도화 | 사용자 수락/수정/거부 이력을 축적하여 개인 및 팀 단위 추천 정확도 점진적 개선 | Low |

---

## 5. 정량적 성과 목표 (KPIs)

* **파일 변환 성공률:** $90\%$ 이상 (PPTX, DOCX, HWP, PDF $\rightarrow$ Notion 변환 시 정보 정상 반영 비율, 형식별로 별도 산출)
* **제목 추론 정확도:** $80\%$ 이상 (LLM 추론 제목과 실제 주제 일치도 다수결 평가)
* **요약 품질 & 키워드 적절성:** 5점 척도 기준 평균 **4.0점 이상**
* **분류 모델 성능 지표 (QA 더미셋 기준):** Precision $\ge 0.85$, Recall $\ge 0.85$, $F1\text{-score} \ge 0.85$ (카테고리별 지표의 macro 평균 기준, 카테고리별 수치 병기)
* **검색 효율 개선:** 파일 탐색 소요 시간 **$50\%$ 이상 감소**
* **트리거 응답 시간:** 파일 감지부터 요약 페이지 생성 완료까지 **30초 이내**
* **요약 배포 성공률:** $95\%$ 이상
* **API 비용 (측정 항목):** 문서 1건당 평균 입력/출력 토큰 수와 비용, QA 전체 평가 1회당 비용을 기록 (목표치는 1주차 예산 확정 후 설정)

---

## 6. 기술 스택 및 라이브러리 상세 명세 (Detailed Tech Stack & Versions)

프로젝트의 호환성 및 재현 가능성을 보장하기 위해 사용되는 모든 도구 및 라이브러리의 버전을 명시합니다.

### 6.1 프로그래밍 언어 및 런타임 Environment
* **Python:** `v3.11.8` (문서 파싱 및 AI 파이프라인 개발 메인 언어)
* **Node.js (Frontend Runtime):** `v20.12.2 LTS`
* **Package Manager:** `pip v24.0` / `npm v10.5.0`

### 6.2 AI / LLM 프레임워크 (Claude API)
> **모델 변경 (2026-11-06):** 로컬 오픈소스 모델(Gemma 4) 대신 Anthropic **Claude** 모델을 API로 사용. 이에 따라 `transformers`, `vllm`, `Ollama`, `torch`, `accelerate`, `torchvision` 및 GPU 장비 요구사항을 모두 제거.

* **모델 (작업별 분리, 최종 선택은 AI-01 비교 후 확정):**
  * 문서 구조화·섹션 요약·차트 캡션 (FR-02, FR-03): `claude-sonnet-5-5` (Claude Sonnet 5.5)
  * 파일명·폴더 추천, 배포용 짧은 요약 등 경량·고빈도 작업 (FR-07, FR-08): `claude-haiku-5-5` (Claude Haiku 5.5)
  * 품질이 부족한 경우에 한해 상위 모델 `claude-opus-5-5` 비교 검토
* **호출 방식:** FastAPI 백엔드 → `anthropic` Python SDK로 Claude Messages API 직접 호출
  * 이미지(차트/도표)는 메시지에 이미지 블록으로 함께 전달 → 별도 비전 모델 불필요
  * PDF는 텍스트 파싱 결과를 기본 입력으로 사용하고, 파싱 품질이 낮은 PDF는 Claude API의 PDF 직접 입력을 보조 수단으로 검토
  * JSON 출력은 tool use(입력 스키마 지정)로 형식을 강제하고 `pydantic`으로 재검증
* **API 키·계정:**
  * Anthropic Console에서 발급한 **API 키(종량제)** 사용, 환경변수 `ANTHROPIC_API_KEY`로 백엔드 서버에서만 보관 (FE·Git 저장소 노출 금지)
  * 개인 Claude 구독(Pro/Max) 계정이나 Claude Code CLI를 서비스 백엔드의 추론 경로로 사용하지 않음
* **비용·성능 관리:**
  * 공통 시스템 프롬프트·출력 스키마에 프롬프트 캐싱 적용
  * QA 더미셋 200~500건 대량 평가는 Message Batches API(비동기 일괄 처리)로 비용 절감
  * 요청별 모델명·입력/출력 토큰·지연 시간·비용을 DB에 기록
  * API 한도 초과(rate limit)·과부하 오류 시 지수 백오프 재시도
* **추론 어댑터:** `LLMClient` 인터페이스 뒤에 Claude 구현과 모킹 구현(BE-04)을 두어, 테스트·오프라인 개발 및 향후 모델 교체가 가능하도록 구성
* **개발 도구 (서비스와 별개):** 팀원은 코드 작성에 Claude Code를 사용

### 6.3 문서 파싱 및 파일 처리 라이브러리
* **PPT Parsing:** `python-pptx v1.0.0`
* **DOCX Parsing:** `python-docx v1.1.0`
* **HWP Parsing:** `pyhwpx v0.10.5` (Windows + 한컴오피스 설치 환경 전용, 한글 프로그램 자동화 방식) / `pyhwp` (크로스플랫폼, HWP 5.0 바이너리 대상, 정확한 배포 버전은 PyPI에서 확인 — HWPX 미지원 가능성 있음)
  * Linux 서버에서 HWP를 처리할 경우 `pyhwp`의 텍스트 추출 또는 별도 변환 경로를 1주차에 검증
* **PDF Parsing:** `pypdf v4.2.0` / `pdfplumber v0.11.0` (암호화 PDF 판별은 `pypdf`의 `is_encrypted` 활용)
* **Image Processing:** `Pillow v10.3.0`

### 6.4 백엔드 및 자동화 라이브러리
* **Web Framework:** `FastAPI v0.111.0`
* **Multipart Upload:** `python-multipart` (FastAPI 파일 업로드 `UploadFile` 처리에 필요)
* **ASGI Server:** `uvicorn v0.29.0`
* **Data Validation:** `pydantic v2.7.1`
* **HTTP Client:** `httpx v0.27.0` / `requests v2.31.0`
* **File Watcher:** `watchdog v4.0.0`
* **Database / ORM:** `SQLite3` (내장) / `SQLAlchemy v2.0.29`

### 6.5 프론트엔드 (UI/UX)
* **UI Library:** `React v18.3.1`
* **Build Tool:** `Vite v5.2.11`
* **Styling:** `Tailwind CSS v3.4.3`
* **Icons & UI Components:** `lucide-react v0.378.0`, Radix UI Primitives (`@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu` 등 사용 컴포넌트별 개별 패키지, 버전은 `package-lock.json`으로 고정)

### 6.6 외부 서비스 API 및 SDK
* **Notion Integration:** `notion-client v2.2.1` / Notion MCP (Model Context Protocol) Server
* **Slack Integration:** `slack-sdk v3.27.1`

### 6.7 QA 더미 데이터 생성 및 데이터 분석
* **Synthetic Data Generation:** `Faker v24.11.0` (가짜 메타데이터, 작성자, 날짜 생성, `ko_KR` 로케일 사용)
* **더미 문서 파일 생성:** PPTX/DOCX는 `python-pptx`/`python-docx`로 생성, PDF는 `reportlab`(본문·표·이미지가 포함된 PDF 생성용, `pypdf`는 생성 기능이 제한적)로 생성, HWP는 `pyhwpx`(Windows + 한컴 환경)로 생성
* **차트 이미지 생성:** `matplotlib` (더미 문서에 삽입할 차트/도표 이미지 생성)
* **Data Manipulation:** `pandas v2.2.2`, `numpy v1.26.4`
* **Metrics & Evaluation:** `scikit-learn v1.4.2` (Precision, Recall, F1-Score 계산)

### 6.8 버전 명세 요약표 (pip `requirements.txt` 대응)
> Python 버전(`3.11.8`)은 pip 패키지가 아니므로 `requirements.txt`가 아닌 `.python-version` 또는 README에 명시. `TBD` 항목은 1주차 설치 검증 후 고정 버전으로 교체.

**`requirements.txt` (백엔드·파싱·QA 공통)**
```text
# 문서 파싱
python-pptx==1.0.0
python-docx==1.1.0
pyhwpx==0.10.5; sys_platform == "win32"   # Windows + 한컴오피스 필요
pyhwp                                      # 크로스플랫폼 HWP, 버전 TBD
pypdf==4.2.0
pdfplumber==0.11.0
Pillow==10.3.0

# 백엔드
fastapi==0.111.0
python-multipart
uvicorn==0.29.0
pydantic==2.7.1
httpx==0.27.0
requests==2.31.0
SQLAlchemy==2.0.29
watchdog==4.0.0

# AI (Claude API)
anthropic                                  # Claude Python SDK, 버전 TBD (httpx·pydantic 호환 확인 후 고정)

# 외부 연동
notion-client==2.2.1
slack-sdk==3.27.1

# QA 더미 데이터·평가
Faker==24.11.0
reportlab                                  # 더미 PDF 생성, 버전 TBD
matplotlib                                 # 더미 차트 이미지, 버전 TBD
pandas==2.2.2
numpy==1.26.4
scikit-learn==1.4.2
```

> GPU·로컬 모델 서빙이 없으므로 AI 추론용 별도 requirements 파일은 두지 않음.

---

## 7. QA 더미 데이터 생성 파이프라인 (Dummy Data Generation Pipeline)

### 7.1 파이프라인 개요
* **목적:** 실제 파일 없이도 시스템 성능(분류 정확도, 요약 품질, 처리 속도)을 체계적으로 검증하기 위해 200~500개 분량의 모의 문서 데이터셋 자동 생성.
* **생성 대상 파일 포맷:** PPTX, DOCX, HWP, PDF

### 7.2 더미 데이터 생성 시나리오
1. **정상 문서 세트:** 카테고리(보고서, 회의록, 과제, 발표자료)별 표준 텍스트 및 무작위 도표/이미지가 포함된 정형 파일.
2. **비정형/난잡한 파일명 세트:** `최종_진짜최종_v2.pptx`, `새_마이크로소프트_워드_문서.docx`, `111111.pdf` 등 실제 사용자의 불명확한 파일명 패턴 적용 (패턴 템플릿 + `Faker` 무작위 값 조합).
3. **엣지케이스 테스트 세트:**
   * 텍스트 없이 이미지만 10장 이상 포함된 PPTX
   * 표(Table)로만 구성된 DOCX
   * 100페이지 이상의 대용량 장문 PDF
   * 특수문자 및 공백이 무분별하게 섞인 HWP
   * 암호화된 PDF/HWP, 빈 문서, 손상 파일 (8.2 예외 처리 검증용)
4. **정답 라벨:** 모든 생성 문서에 대해 카테고리·의도된 제목·핵심 키워드를 담은 라벨 파일(CSV/JSON)을 함께 생성하고, 동일 시드로 재생성 가능하도록 구성.

> 더미 HWP 생성은 Windows + 한컴오피스 환경이 필요하므로, 해당 환경이 없으면 HWP 세트는 수작업 제작 샘플로 대체하고 그 개수를 평가 보고서에 명시.

---

## 8. 예외 처리 및 데이터 보안 (Edge Cases & Security)

1. **외부 API 사용에 따른 데이터 보안:**
   * AI 분석 시 문서 본문과 이미지가 **Anthropic API로 전송**됨. 분석 시작 전 사용자에게 외부 전송 사실을 안내하고 동의를 받으며, 사용자가 지정한 폴더·파일은 분석 대상에서 제외할 수 있도록 함.
   * Anthropic API의 데이터 보존 기간·학습 사용 여부 등 처리 정책은 1주차에 공식 약관으로 확인하여 README와 동의 문구에 반영.
   * 원문 전체를 로그·DB에 남기지 않고, 필요한 분석 결과만 저장.
   * API 키는 서버 환경변수로만 관리하고, 주기적 교체 및 사용량 알림 설정.
   * Notion/Slack 연동(FR-04, FR-08)도 요약·구조화 결과를 외부로 전송하므로, 사용자가 승인한 문서와 활성화한 채널에 한해 전송.
2. **엣지케이스 자동 예외 처리:**
   * 암호화된 HWP/PDF 감지 시 정규화 실패 오류 메시지 반환 및 사용자에게 암호 해제 요청 알림.
   * 이미지 추출 실패 시 텍스트 파싱 결과만으로 Claude 추론 fallback 진행.
   * Claude API 한도 초과·과부하·네트워크 오류 시 지수 백오프 재시도 후, 계속 실패하면 작업을 `failed`로 표시하고 사용자가 재시도할 수 있게 함.
3. **데이터 백업 및 복구:**
   * Cleanup Mode 실행 시 원본 파일은 `.backup` 폴더에 격리 보관 후, 사용자의 롤백 요청 시 원상 복구 수행.
   * 롤백 범위: 로컬 파일명·위치는 원상 복구. 이미 생성된 Notion 페이지는 자동 삭제 대신 보관(archive) 처리 여부를 사용자에게 확인.

---

## 9. 문서 변경 이력

| 날짜 | 변경 내용 |
| :--- | :--- |
| 2026-11-06 | Gemma 4 지원을 위해 AI 추론 라이브러리 버전 정정(`transformers >= 5.5.0` 등), 모델 식별자 명시, Gemma 4 12B 멀티모달 활용으로 FR-03 조정, `requirements.txt` 오류 수정(python 줄 제거, `pyhwpx` Windows 한정, 누락 패키지 추가) 및 AI용 파일 분리, Radix UI 패키지명 정정, KPI에 PDF 포함·macro 평균 명시, 외부 전송 보안 문구 보정, Notion API 제한·롤백 범위 추가, 더미 데이터 정답 라벨 시나리오 추가 |
| 2026-11-06 | 메인 모델을 **Gemma 4 E4B → Gemma 4 12B**(`google/gemma-4-12B-it`, Ollama `gemma4:12b`)로 변경. 사양(11.95B, 256K 컨텍스트, Apache 2.0)·하드웨어 요구사항·E4B 하향 대안 명시, Ollama를 1순위 추론 엔진으로 조정 |
| 2026-11-06 | **AI 모델을 로컬 Gemma 4에서 Claude API로 전면 변경.** 1.2 목적, FR-02/FR-03, 6.2(Sonnet 5.5·Haiku 5.5 작업별 분리, `anthropic` SDK, API 키 관리, 프롬프트 캐싱·Batches API, 추론 어댑터), 6.8(`anthropic` 추가, AI 추론용 requirements 파일 삭제), 8.1(외부 전송 동의·약관 확인), 8.2(API 오류 재시도) 개정, KPI에 API 비용 측정 항목 추가 |