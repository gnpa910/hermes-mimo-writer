"""Pipeline orchestrator.

Sequences the seven agents in dependency order, propagates token ledgers,
and emits a final DOCX. Mirrors Hermes Agent's delegate_task → return-summary
pattern: each agent returns typed output; orchestrator stitches them.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .agents import (
    AISanitizerAgent,
    BriefParserAgent,
    CitationManagerAgent,
    ContentDrafterAgent,
    DocxAssemblerAgent,
    OutlineDrafterAgent,
    StyleProfilerAgent,
)
from .agents.docx_assembler import AssemblyOptions
from .config import Settings
from .mimo_client import MimoClient
from .models import Brief, Draft, StyleProfile, TokenLedger


log = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    brief: Brief
    style: StyleProfile
    draft: Draft
    sanitized: Draft
    output_path: Path
    ledger: TokenLedger


@dataclass
class PipelineInput:
    brief_text: str
    style_samples: list[str]
    output_path: Path
    skip_sanitize: bool = False


class WritingPipeline:
    """7-agent academic writing pipeline."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.ledger = TokenLedger()

    async def run(self, pi: PipelineInput) -> PipelineResult:
        async with MimoClient(self.settings) as client:
            brief_parser = BriefParserAgent(client, self.ledger)
            style_profiler = StyleProfilerAgent(client, self.ledger)
            outline_drafter = OutlineDrafterAgent(client, self.ledger)
            content_drafter = ContentDrafterAgent(client, self.ledger)
            sanitizer = AISanitizerAgent(client, self.ledger)
            citations = CitationManagerAgent(client, self.ledger)
            assembler = DocxAssemblerAgent(client, self.ledger)

            log.info("[1/7] parsing brief")
            brief = await brief_parser.run(pi.brief_text)
            log.info("[2/7] profiling style (%d samples)", len(pi.style_samples))
            style = await style_profiler.run(pi.style_samples)
            log.info("[3/7] drafting outline")
            outline = await outline_drafter.run((brief, style))
            log.info("[4/7] drafting %d sections", len(outline.sections))
            draft = await content_drafter.run((brief, style, outline))

            if pi.skip_sanitize:
                sanitized = draft
            else:
                log.info("[5/7] sanitizing AI signatures")
                sanitized = await sanitizer.run((brief, style, draft))

            log.info("[6/7] resolving citations")
            citation_list = await citations.run((brief, sanitized))
            sanitized.citations = citation_list

            log.info("[7/7] assembling docx")
            options = AssemblyOptions(output_path=pi.output_path)
            output_path = await assembler.run(
                (brief, sanitized, citation_list, options)
            )

        log.info(
            "pipeline complete words=%d tokens=%d",
            sanitized.total_words,
            self.ledger.total,
        )
        return PipelineResult(
            brief=brief,
            style=style,
            draft=draft,
            sanitized=sanitized,
            output_path=output_path,
            ledger=self.ledger,
        )
