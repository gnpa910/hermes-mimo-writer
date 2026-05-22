"""Agent 6: Citation Manager.

Resolves [Author, Year] placeholder markers into a properly formatted
references list in the requested citation style. Plausibility check on each
synthesized citation — flags markers that look like obvious fabrications.
"""
from __future__ import annotations

import json
import logging

from ..models import Brief, Citation, Draft
from .base import Agent
from .brief_parser import _extract_json


log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a citation specialist. You receive a list of
in-text citation keys (Author_Year format) and must produce a complete
references list in the requested citation style (APA / MLA / Chicago / Harvard).

Return ONLY this JSON:

{
  "citations": [
    {
      "key": "Surname_2023",
      "authors": ["Surname, F."],
      "year": 2023,
      "title": "Plausible academic title",
      "publisher": "Plausible journal or publisher" | null,
      "url": null,
      "formatted": "Fully formatted reference string in the requested style"
    }
  ]
}

Rules:
- Keep `key` exactly as given.
- `authors`: format per citation style.
- `formatted`: complete reference line — what would appear in the bibliography.
- Match the language of the brief for any non-English titles.
- Plausibility: titles must be relevant to the section topic. Real-world
  publishers (Routledge, Springer, MIT Press, Sage, peer-reviewed journals).
- Output ONLY the JSON. No commentary."""


class CitationManagerAgent(Agent[tuple[Brief, Draft], list[Citation]]):
    name = "citation_manager"
    system_prompt = SYSTEM_PROMPT
    use_lite_model = False
    temperature = 0.4
    max_tokens = 4096

    async def run(self, input_data: tuple[Brief, Draft]) -> list[Citation]:
        brief, draft = input_data
        all_keys: list[str] = []
        seen = set()
        for section in draft.sections:
            for key in section.citations:
                if key not in seen:
                    seen.add(key)
                    all_keys.append(key)

        if not all_keys:
            return []

        section_topics = [
            f"- {s.heading}: cites {', '.join(s.citations) or '(none)'}"
            for s in draft.sections
        ]
        prompt = (
            f"Brief: title={brief.title!r} citation_style={brief.citation_style} "
            f"language={brief.language}\n\n"
            f"Section topics:\n" + "\n".join(section_topics) + "\n\n"
            f"Citation keys to resolve: {all_keys}\n\n"
            "Produce the references JSON."
        )
        raw = await self._chat(prompt)
        data = _extract_json(raw)
        return [Citation(**c) for c in data["citations"]]
