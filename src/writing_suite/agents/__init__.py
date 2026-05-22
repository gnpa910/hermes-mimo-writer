"""Seven specialized agents for the writing pipeline."""

from .brief_parser import BriefParserAgent
from .style_profiler import StyleProfilerAgent
from .outline_drafter import OutlineDrafterAgent
from .content_drafter import ContentDrafterAgent
from .ai_sanitizer import AISanitizerAgent
from .citation_manager import CitationManagerAgent
from .docx_assembler import DocxAssemblerAgent

__all__ = [
    "BriefParserAgent",
    "StyleProfilerAgent",
    "OutlineDrafterAgent",
    "ContentDrafterAgent",
    "AISanitizerAgent",
    "CitationManagerAgent",
    "DocxAssemblerAgent",
]
