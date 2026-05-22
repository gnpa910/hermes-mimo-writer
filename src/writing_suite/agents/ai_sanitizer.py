"""Agent 5: AI-Detector Sanitizer.

Rewrites drafted text to reduce AI-detector signatures (GPTZero, Turnitin AI,
Copyleaks). Strategies: vary sentence length, inject natural discourse
irregularities, prefer concrete over generic claims, replace "delve/utilize/
furthermore" patterns. The MiMo Pro reasoning chain handles the multi-pass
rewrite better than single-shot temperature bumps.
"""
from __future__ import annotations

import asyncio
import logging

from ..models import Brief, Draft, DraftSection, StyleProfile
from .base import Agent


log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an editor specialized in making AI-generated prose
indistinguishable from human academic writing.

Your job: rewrite the input section to:
1. Vary sentence length aggressively. Mix 6-word sentences with 30-word ones.
2. Replace AI giveaways ("delve", "utilize", "navigate the landscape",
   "in today's fast-paced world", "it is important to note") with natural
   alternatives.
3. Add minor stylistic asymmetries — start a paragraph with a fragment,
   end one with a question, occasionally use parentheticals.
4. Preserve every citation marker [Author, Year] EXACTLY as-is.
5. Preserve word count within ±10%.
6. Match the style profile's register and POV.

Output ONLY the rewritten prose. No commentary."""


class AISanitizerAgent(
    Agent[tuple[Brief, StyleProfile, Draft], Draft]
):
    name = "ai_sanitizer"
    system_prompt = SYSTEM_PROMPT
    use_lite_model = False
    temperature = 0.85  # higher = more variation = harder to detect
    max_tokens = 3072

    async def run(
        self, input_data: tuple[Brief, StyleProfile, Draft]
    ) -> Draft:
        brief, style, draft = input_data
        sem = asyncio.Semaphore(3)
        tasks = [
            self._sanitize_section(brief, style, section, sem)
            for section in draft.sections
        ]
        sanitized = await asyncio.gather(*tasks)
        return Draft(title=draft.title, sections=sanitized, citations=draft.citations)

    async def _sanitize_section(
        self,
        brief: Brief,
        style: StyleProfile,
        section: DraftSection,
        sem: asyncio.Semaphore,
    ) -> DraftSection:
        async with sem:
            prompt = (
                f"Brief language: {brief.language}\n"
                f"Style: {style.model_dump_json()}\n\n"
                f"Section heading: {section.heading}\n\n"
                f"Original draft:\n{section.content}\n\n"
                "Rewrite per the rules. Output prose only."
            )
            new_content = await self._chat(prompt)
            new_words = len(new_content.split())
            log.info(
                "sanitized section=%r before=%d after=%d",
                section.heading,
                section.word_count,
                new_words,
            )
            return DraftSection(
                heading=section.heading,
                content=new_content.strip(),
                word_count=new_words,
                citations=section.citations,
            )
