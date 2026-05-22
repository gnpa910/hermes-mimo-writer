"""Agent 3: Outline Drafter.

Takes a Brief + StyleProfile and produces a section-by-section Outline.
Uses MiMo Pro for its long-chain reasoning — outline coherence is the
foundation everything else depends on.
"""
from __future__ import annotations

import json

from ..models import Brief, Outline, OutlineSection, StyleProfile
from .base import Agent
from .brief_parser import _extract_json


SYSTEM_PROMPT = """You are an academic outline architect. Given a brief and
a style profile, produce a structured outline. Return ONLY this JSON:

{
  "title": str,
  "sections": [
    {
      "heading": str,
      "target_words": int,
      "bullet_points": [str],
      "sources_hint": [str]
    }
  ]
}

Rules:
- Total target_words across sections = brief.word_count (±5%).
- Standard structure: Introduction (~10%), 3-5 body sections (~75%), Conclusion (~10%), References list (excluded from word count).
- Bullet points should be specific claims, not generic placeholders.
- sources_hint: 1-3 search queries that would find supporting sources.
- Match the brief's language. If language=id, headings in Bahasa Indonesia.
- Output ONLY the JSON.
"""


class OutlineDrafterAgent(Agent[tuple[Brief, StyleProfile], Outline]):
    name = "outline_drafter"
    system_prompt = SYSTEM_PROMPT
    use_lite_model = False
    temperature = 0.5
    max_tokens = 3072

    async def run(self, input_data: tuple[Brief, StyleProfile]) -> Outline:
        brief, style = input_data
        prompt = self._build_prompt(brief, style)
        raw = await self._chat(prompt)
        data = _extract_json(raw)
        sections = [OutlineSection(**s) for s in data["sections"]]
        return Outline(title=data["title"], sections=sections)

    @staticmethod
    def _build_prompt(brief: Brief, style: StyleProfile) -> str:
        return (
            f"Brief:\n{brief.model_dump_json(indent=2)}\n\n"
            f"Style profile:\n{style.model_dump_json(indent=2)}\n\n"
            "Produce the outline."
        )
