"""Agent 1: Brief Parser.

Extracts structured requirements from a free-form rubric/prompt. Uses the
lite MiMo model since this is straightforward classification work — saves
tokens vs Pro for the overall pipeline.
"""
from __future__ import annotations

import json
import re

from ..models import Brief
from .base import Agent


SYSTEM_PROMPT = """You are an academic brief parser. Given a free-form
assignment prompt or rubric, extract structured fields and return ONLY a
JSON object with these keys:

{
  "title": str,
  "course": str | null,
  "word_count": int,        // target word count, default 1000
  "language": "en" | "id" | "ms" | "zh",
  "citation_style": "APA" | "MLA" | "Chicago" | "Harvard",
  "audience": str,
  "rubric": [str],          // grading criteria, one per line
  "keywords": [str],
  "notes": str | null
}

Rules:
- Detect language from the prompt itself (Indonesian = id, Malay = ms).
- Word count: look for "1000 kata", "1500 words", "minimum N", etc. Default 1000.
- Citation style: detect "APA", "MLA", "Harvard". Default APA.
- Output ONLY the JSON. No markdown fence, no commentary.
"""


class BriefParserAgent(Agent[str, Brief]):
    name = "brief_parser"
    system_prompt = SYSTEM_PROMPT
    use_lite_model = True
    temperature = 0.1
    max_tokens = 1024

    async def run(self, input_data: str) -> Brief:
        raw = await self._chat(input_data)
        data = _extract_json(raw)
        return Brief(**data)


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


def _extract_json(text: str) -> dict:
    """Defensive JSON extraction — strip code fences if model adds them."""
    text = text.strip()
    fence_match = _JSON_FENCE.search(text)
    if fence_match:
        text = fence_match.group(1)
    # Find first '{' and last '}' to handle leading/trailing prose
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object found in model output: {text[:200]}")
    return json.loads(text[start : end + 1])
