"""Agent 4: Content Drafter.

Drafts each section in turn, streaming output via MiMo SSE. This is the
heaviest token consumer — typical 1000-word essay uses 30K-80K tokens here
(retrieval-style context + multi-step reasoning per section).
"""
from __future__ import annotations

import asyncio
import logging

from ..mimo_client import ChatMessage
from ..models import Brief, Draft, DraftSection, Outline, StyleProfile
from .base import Agent


log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an academic writer. Draft the requested section
following the brief and style profile exactly. Match the target word count
within ±15%. Use [author, year] inline citation placeholders that the
Citation Manager will resolve later — invent author/year that's plausible
for the topic.

Rules:
- Match the language and citation style from the brief.
- Mirror the style profile (register, sentence length, POV).
- No headings or markdown — pure prose for the section body.
- No "In conclusion" / "Furthermore" filler unless the style profile prefers it.
- Cite at least once per ~150 words. Use [Surname, YYYY] format.
- Return only the section prose. No commentary, no JSON.
"""


class ContentDrafterAgent(
    Agent[tuple[Brief, StyleProfile, Outline], Draft]
):
    name = "content_drafter"
    system_prompt = SYSTEM_PROMPT
    use_lite_model = False
    temperature = 0.75
    max_tokens = 3072

    async def run(
        self, input_data: tuple[Brief, StyleProfile, Outline]
    ) -> Draft:
        brief, style, outline = input_data

        # Draft sections in parallel — MiMo TPM=10M is generous enough.
        # Cap at 3 concurrent to stay within RPM=100 in batch contexts.
        sem = asyncio.Semaphore(3)
        tasks = [
            self._draft_section(brief, style, outline, idx, sem)
            for idx in range(len(outline.sections))
        ]
        sections = await asyncio.gather(*tasks)
        return Draft(title=outline.title, sections=sections)

    async def _draft_section(
        self,
        brief: Brief,
        style: StyleProfile,
        outline: Outline,
        idx: int,
        sem: asyncio.Semaphore,
    ) -> DraftSection:
        async with sem:
            section = outline.sections[idx]
            prompt = self._build_prompt(brief, style, outline, idx)
            content = await self._chat(prompt, max_tokens=section.target_words * 4)
            words = len(content.split())
            citations = self._extract_citation_keys(content)
            log.info(
                "drafted section=%r words=%d citations=%d",
                section.heading,
                words,
                len(citations),
            )
            return DraftSection(
                heading=section.heading,
                content=content.strip(),
                word_count=words,
                citations=citations,
            )

    @staticmethod
    def _build_prompt(
        brief: Brief, style: StyleProfile, outline: Outline, idx: int
    ) -> str:
        section = outline.sections[idx]
        prev_headings = [s.heading for s in outline.sections[:idx]]
        next_headings = [s.heading for s in outline.sections[idx + 1 :]]
        return (
            f"Brief: {brief.model_dump_json()}\n\n"
            f"Style: {style.model_dump_json()}\n\n"
            f"Outline title: {outline.title}\n"
            f"Previous sections: {prev_headings}\n"
            f"Following sections: {next_headings}\n\n"
            f"Now draft section {idx + 1} of {len(outline.sections)}:\n"
            f"  heading: {section.heading}\n"
            f"  target_words: {section.target_words}\n"
            f"  bullet_points: {section.bullet_points}\n\n"
            "Write ONLY the section prose."
        )

    @staticmethod
    def _extract_citation_keys(text: str) -> list[str]:
        """Extract [Surname, YYYY] markers from drafted text."""
        import re

        pattern = re.compile(r"\[([A-Z][A-Za-z\-\s]+),\s*(\d{4}[a-z]?)\]")
        keys = []
        seen = set()
        for match in pattern.finditer(text):
            key = f"{match.group(1).strip()}_{match.group(2)}"
            if key not in seen:
                seen.add(key)
                keys.append(key)
        return keys
