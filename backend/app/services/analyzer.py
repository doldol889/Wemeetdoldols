"""추출한 텍스트로 제목 · 한 줄 요약 · 키워드를 만든다 (BE-07).

- backend/.env 에 ANTHROPIC_API_KEY 가 있으면 Claude API로 분석한다.
- 키가 없거나 anthropic 패키지가 없으면, 간단한 규칙으로 만든 임시 결과를 돌려준다
  (첫 줄 = 제목, 첫 문장 = 요약, 자주 나온 단어 = 키워드). 서버는 키 없이도 동작한다.

AI 파트 [AI-사전2] 프롬프트를 바탕으로, 결과 필드는 공통 형식(schema 0.2)에 맞춘다.
  - summary 로 오면 one_line_summary 로 바꾼다
  - 키워드는 최대 5개, 최소 3개
"""
from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter

from app.schemas.job import Analysis

logger = logging.getLogger(__name__)

try:  # .env 파일이 있으면 읽는다 (없어도 괜찮음)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

CLAUDE_MODEL = os.getenv("WEMEET_CLAUDE_MODEL", "claude-haiku-5-5")
MAX_INPUT_CHARS = 20_000  # 긴 문서는 앞부분만 보낸다 (비용 · 실패 방지)

PROMPT = """다음 문서를 분석해서 아래 형식의 JSON만 반환하세요. 다른 말은 쓰지 마세요.

{{
  "title": "문서 내용을 대표하는 제목",
  "one_line_summary": "문서 핵심 내용을 한 문장으로 요약",
  "keywords": ["키워드1", "키워드2", "키워드3"]
}}

규칙: keywords 는 3~5개.

문서:
{text}
"""


def analyze(text: str, filename: str) -> Analysis:
    """Claude 키가 있으면 Claude, 없으면 규칙 기반 결과."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return _analyze_with_claude(text)
        except Exception as e:  # 키 오류 · 네트워크 · 형식 오류 → 규칙 기반으로 대체
            logger.warning("Claude 분석 실패, 규칙 기반으로 대체: %s", type(e).__name__)
    return _analyze_with_rules(text, filename)


# ---------------------------------------------------------------- Claude
def _analyze_with_claude(text: str) -> Analysis:
    from anthropic import Anthropic  # 키가 있을 때만 필요

    client = Anthropic()  # ANTHROPIC_API_KEY 환경변수를 자동으로 읽음
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": PROMPT.format(text=text[:MAX_INPUT_CHARS])}],
    )
    raw = message.content[0].text
    return normalize(_parse_json(raw))


def _parse_json(raw: str) -> dict:
    """```json ... ``` 처럼 감싸져 와도 JSON 부분만 꺼내서 읽는다."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("JSON을 찾지 못함")
    return json.loads(match.group(0))


def normalize(data: dict) -> Analysis:
    """AI 결과를 공통 형식으로 맞춘다 (summary → one_line_summary, 키워드 3~5개)."""
    summary = data.get("one_line_summary") or data.get("summary") or ""
    keywords = [str(k).strip() for k in data.get("keywords", []) if str(k).strip()][:5]
    while len(keywords) < 3:
        keywords.append("문서")
    return Analysis(
        title=str(data.get("title") or "제목 없음")[:100],
        one_line_summary=str(summary)[:300],
        keywords=keywords,
        sections=data.get("sections", []),
        visual_captions=data.get("visual_captions", []),
        category=data.get("category"),
    )


# ---------------------------------------------------------------- 규칙 기반 (키 없을 때)
_STOPWORDS = {
    "그리고", "그러나", "하지만", "또한", "이번", "대한", "위한", "있는", "있습니다", "합니다",
    "the", "and", "for", "with", "this", "that", "are", "from",
}


def _analyze_with_rules(text: str, filename: str) -> Analysis:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0][:60] if lines else filename

    body = " ".join(lines)
    first_sentence = re.split(r"(?<=[.!?。])\s|\n", body, maxsplit=1)[0]
    summary = first_sentence[:100] + ("…" if len(first_sentence) > 100 else "")

    words = re.findall(r"[가-힣A-Za-z][가-힣A-Za-z0-9]{1,}", body)
    counts = Counter(w for w in words if w.lower() not in _STOPWORDS)
    keywords = [w for w, _ in counts.most_common(5)]

    return normalize({
        "title": title,
        "one_line_summary": f"(임시 요약) {summary}",
        "keywords": keywords,
    })
