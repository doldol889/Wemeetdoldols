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
* 오픈소스 LLM인 **Gemma 4 E4B**와 비전 AI 모델을 연동하여 다양한 문서(PPT, DOCX, HWP, PDF 등)의 본문 및 시각 자료를 정밀 분석.
* 의미 있는 표준 파일명 추천, 폴더 구조 제안, 자동 요약 및 Notion 구조화 페이지 변환 시스템 구축.
* 품질 검증(QA)을 위한 **자동/반자동 더미 데이터 생성 파이프라인**을 구축하여 시스템 정확도 및 안정성 확보.
* 로컬/온프레미스 기반 오픈소스 모델 활용으로 외부 API 비용 절감 및 문서 데이터 보안 강화.

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
* **내용:** PPT, DOCX, HWP, PDF 레거시 파일 파싱 $\rightarrow$ **Gemma 4 E4B** 기반 내용 분석 $\rightarrow$ Notion 검색 가능 구조화 페이지 자동 변환.
* **핵심 기능:** 트리 구조 검토 UI를 통한 승인 기반 처리(수락/수정/거부) 및 백업/롤백 지원.

### 3.2 [2차 목표] Auto-save Mode - 신규 파일 반자동 관리 & 자동 요약
* **내용:** PC 특정 폴더(다운로드, 바탕화면) 이벤트 실시간 감지 $\rightarrow$ 신규 파일의 키워드 기반 표준 파일명 및 저장 폴더 상위 3개 추천.
* **배포 연동:** 파일 생성 즉시 자동 요약본을 작성하여 Slack Webhook 또는 Notion 멘션으로 팀원 자동 공유.

### 3.3 [3차 목표] Team Collaboration Mode - 팀 공유 드라이브 확장
* **내용:** Google Drive, OneDrive, NAS 등에 공통 분류 규칙(YAML/JSON) 동기화, 이름 충돌/중복 파일 탐지.
* **시각화:** 팀 파일 저장 현황 통계 대시보드 및 축적된 피드백 학습을 통한 분류 규칙 자동 개선 제안.

---

## 4. 세부 기능 요구사항 (Functional Requirements)

| 모듈 ID | 기능명 | 세부 설명 | 우선순위 |
| :--- | :--- | :--- | :--- |
| **FR-01** | 문서 파싱 파이프라인 | `python-pptx`, `python-docx`, `pyhwpx`/`pyhwp`, `pypdf`를 사용하여 텍스트, 이미지, 표, 목차 추출 및 중간 JSON 정규화 | High (MVP) |
| **FR-02** | Gemma 4 E4B 구조화 | 정규화 텍스트를 **Gemma 4 E4B**에 입력하여 제목 추론, 한 줄 요약, 키워드(3~5개), 목차 및 섹션 요약 JSON 생성 | High (MVP) |
| **FR-03** | 차트/도표 이미지 분석 | 문서 내 차트/도표 이미지를 추출하여 비전 AI 모델로 전달 후 설명 캡션 텍스트 생성 | High (MVP) |
| **FR-04** | Notion API/MCP 연동 | LLM 출력 JSON을 Notion 블록(Heading, Callout, TOC, Image 등)으로 매핑하여 자동 업로드 | High (MVP) |
| **FR-05** | Cleanup 검토 UI & 롤백 | 정리 제안 결과를 트리 구조로 시각화하고 사용자 수락/수정/거부 적용 및 롤백 기능 제공 | High (MVP) |
| **FR-06** | **QA 더미 데이터 생성기** | **QA 평가를 위한 다양한 포맷(PPT, DOCX, HWP, PDF)의 비정형 테스트 문서(200~500개) 및 모의 메타데이터 자동 생성 파이프라인 구축** | **High (MVP)** |
| **FR-07** | 실시간 파일 감지 | `watchdog` 기반 지정 폴더 파일 생성/이동/복사 이벤트 실시간 감지 및 추천 알림 UI 실행 | Medium |
| **FR-08** | 자동 요약 및 배포 | Webhook 기반 신규 문서 업로드 감지 시 핵심 요약 작성 후 Slack/Notion으로 자동 전송 | Medium |
| **FR-09** | 팀 규칙 동기화 & 대시보드 | 관리자 규칙(YAML/JSON) 동기화, 중복 파일 탐지, 팀 활동 시각화 대시보드 구축 | Low |
| **FR-10** | 피드백 기반 추천 고도화 | 사용자 수락/수정/거부 이력을 축적하여 개인 및 팀 단위 추천 정확도 점진적 개선 | Low |

---

## 5. 정량적 성과 목표 (KPIs)

* **파일 변환 성공률:** $90\%$ 이상 (PPT, DOCX, HWP $\rightarrow$ Notion 변환 시 정보 정상 반영 비율)
* **제목 추론 정확도:** $80\%$ 이상 (LLM 추론 제목과 실제 주제 일치도 다수결 평가)
* **요약 품질 & 키워드 적절성:** 5점 척도 기준 평균 **4.0점 이상**
* **분류 모델 성능 지표 (QA 더미셋 기준):** Precision $\ge 0.85$, Recall $\ge 0.85$, $F1\text{-score} \ge 0.85$
* **검색 효율 개선:** 파일 탐색 소요 시간 **$50\%$ 이상 감소**
* **트리거 응답 시간:** 파일 감지부터 요약 페이지 생성 완료까지 **30초 이내**
* **요약 배포 성공률:** $95\%$ 이상

---

## 6. 기술 스택 및 라이브러리 상세 명세 (Detailed Tech Stack & Versions)

프로젝트의 호환성 및 재현 가능성을 보장하기 위해 사용되는 모든 도구 및 라이브러리의 버전을 명시합니다.

### 6.1 프로그래밍 언어 및 런타임 Environment
* **Python:** `v3.11.8` (문서 파싱 및 AI 파이프라인 개발 메인 언어)
* **Node.js (Frontend Runtime):** `v20.12.2 LTS`
* **Package Manager:** `pip v24.0` / `npm v10.5.0`

### 6.2 AI / LLM & 비전 추론 프레임워크
* **Main LLM Model:** **Gemma 4 E4B** (Open-source LLM)
* **LLM Inference Engine:** `vllm v0.4.2` 또는 `Ollama v0.1.32` (로컬/서버 고속 추론 서빙)
* **PyTorch:** `v2.3.0+cu121` (CUDA 12.1 지원)
* **Hugging Face Transformers:** `transformers v4.40.1`
* **Accelerate:** `accelerate v0.29.3`
* **Vision Model:** `torchvision v0.18.0` 및 경량 Vision-Language Model

### 6.3 문서 파싱 및 파일 처리 라이브러리
* **PPT Parsing:** `python-pptx v1.0.0`
* **DOCX Parsing:** `python-docx v1.1.0`
* **HWP Parsing:** `pyhwpx v0.10.5` (Windows/한컴 환경) / `pyhwp v0.1.5` (크로스플랫폼)
* **PDF Parsing:** `pypdf v4.2.0` / `pdfplumber v0.11.0`
* **Image Processing:** `Pillow v10.3.0`

### 6.4 백엔드 및 자동화 라이브러리
* **Web Framework:** `FastAPI v0.111.0`
* **ASGI Server:** `uvicorn v0.29.0`
* **Data Validation:** `pydantic v2.7.1`
* **HTTP Client:** `httpx v0.27.0` / `requests v2.31.0`
* **File Watcher:** `watchdog v4.0.0`
* **Database / ORM:** `SQLite3` (내장) / `SQLAlchemy v2.0.29`

### 6.5 프론트엔드 (UI/UX)
* **UI Library:** `React v18.3.1`
* **Build Tool:** `Vite v5.2.11`
* **Styling:** `Tailwind CSS v3.4.3`
* **Icons & UI Components:** `lucide-react v0.378.0`, `radix-ui v1.0.0`

### 6.6 외부 서비스 API 및 SDK
* **Notion Integration:** `notion-client v2.2.1` / Notion MCP (Model Context Protocol) Server
* **Slack Integration:** `slack-sdk v3.27.1`

### 6.7 QA 더미 데이터 생성 및 데이터 분석
* **Synthetic Data Generation:** `Faker v24.11.0` (가짜 메타데이터, 작성자, 날짜 생성)
* **Data Manipulation:** `pandas v2.2.2`, `numpy v1.26.4`
* **Metrics & Evaluation:** `scikit-learn v1.4.2` (Precision, Recall, F1-Score 계산)

### 6.8 버전 명세 요약표 (pip `requirements.txt` 대응)
```text
python==3.11.8
torch==2.3.0
transformers==4.40.1
accelerate==0.29.3
vllm==0.4.2
python-pptx==1.0.0
python-docx==1.1.0
pyhwpx==0.10.5
pypdf==4.2.0
pdfplumber==0.11.0
Pillow==10.3.0
FastAPI==0.111.0
uvicorn==0.29.0
pydantic==2.7.1
watchdog==4.0.0
notion-client==2.2.1
slack-sdk==3.27.1
Faker==24.11.0
pandas==2.2.2
numpy==1.26.4
scikit-learn==1.4.2
```

---

## 7. QA 더미 데이터 생성 파이프라인 (Dummy Data Generation Pipeline)

### 7.1 파이프라인 개요
* **목적:** 실제 파일 없이도 시스템 성능(분류 정확도, 요약 품질, 처리 속도)을 체계적으로 검증하기 위해 200~500개 분량의 모의 문서 데이터셋 자동 생성.
* **생성 대상 파일 포맷:** PPTX, DOCX, HWP, PDF

### 7.2 더미 데이터 생성 시나리오
1. **정상 문서 세트:** 카테고리(보고서, 회의록, 과제, 발표자료)별 표준 텍스트 및 무작위 도표/이미지가 포함된 정형 파일.
2. **비정형/난잡한 파일명 세트:** `최종_진짜최종_v2.pptx`, `새_마이크로소프트_워드_문서.docx`, `111111.pdf` 등 실제 사용자의 불명확한 파일명 패턴 적용 (`Faker` 라이브러리 활용).
3. **엣지케이스 테스트 세트:**
   * 텍스트 없이 이미지만 10장 이상 포함된 PPTX
   * 표(Table)로만 구성된 DOCX
   * 100페이지 이상의 대용량 장문 PDF
   * 특수문자 및 공백이 무분별하게 섞인 HWP

---

## 8. 예외 처리 및 데이터 보안 (Edge Cases & Security)

1. **로컬 오픈소스 LLM(Gemma 4 E4B) 보안성:**
   * 외부 상용 API(OpenAI/Anthropic)로 데이터를 전송하지 않고 로컬/온프레미스 서버에서 추론을 수행하여 외부 데이터 유출을 원천 차단.
2. **엣지케이스 자동 예외 처리:**
   * 암호화된 HWP/PDF 감지 시 정규화 실패 오류 메시지 반환 및 사용자에게 암호 해제 요청 알림.
   * 이미지 추출 실패 시 텍스트 파싱 결과만으로 Gemma 4 E4B 추론 fallback 진행.
3. **데이터 백업 및 복구:**
   * Cleanup Mode 실행 시 원본 파일은 `.backup` 폴더에 격리 보관 후, 사용자의 롤백 요청 시 원상 복구 수행.