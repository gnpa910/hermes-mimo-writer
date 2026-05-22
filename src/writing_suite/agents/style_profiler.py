"""Agent 2: Style Profiler.

Analyzes 1-N sample texts and builds a style fingerprint that downstream
drafting agents can match. Critical for maintaining voice consistency across
sections.
"""
from __future__ import annotations

import json

from ..models import StyleProfile
from .base import Agent
from .brief_parser import _extract_json


SYSTEM_PROMPT = """You are a stylometric analyst. Given one or more sample
texts, extract the author's writing fingerprint. Return ONLY this JSON:

{
  "register": "formal" | "semi-formal" | "casual",
  "avg_sentence_length": float,
  "vocabulary_complexity": "simple" | "moderate" | "advanced",
  "pov": "first" | "second" | "third",
  "paragraph_density": "short" | "medium" | "long",
  "discourse_markers": [str],   // e.g. ["furthermore", "in addition"]
  "common_phrases": [str],
  "avoid_phrases": [str],       // patterns to avoid in new writing
  "notes": str | null
}

Be specific. Notes should call out distinctive habits (e.g. "uses rhetorical
questions to open paragraphs", "avoids contractions").
Output ONLY the JSON.
"""


class StyleProfilerAgent(Agent[list[str], StyleProfile]):
    """Input: list of sample texts. Output: StyleProfile."""

    name = "style_profiler"
    system_prompt = SYSTEM_PROMPT
    use_lite_model = False  # style analysis benefits from Pro reasoning
    temperature = 0.2
    max_tokens = 1024

    async def run(self, input_data: list[str]) -> StyleProfile:
        if not input_data:
            return StyleProfile()  # default profile when no samples provided

        joined = "\n\n---SAMPLE---\n\n".join(input_data[:5])  # cap at 5 samples
        prompt = f"Analyze these samples and produce the style fingerprint:\n\n{joined}"
        raw = await self._chat(prompt)
        data = _extract_json(raw)
        return StyleProfile(**data)
