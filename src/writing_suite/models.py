"""Domain models shared across agents."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CitationStyle = Literal["APA", "MLA", "Chicago", "Harvard"]
Language = Literal["en", "id", "ms", "zh"]


class Brief(BaseModel):
    """Parsed assignment brief."""

    title: str
    course: str | None = None
    word_count: int = Field(ge=100, le=20000)
    language: Language = "en"
    citation_style: CitationStyle = "APA"
    audience: str = "university student"
    rubric: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    notes: str | None = None


class StyleProfile(BaseModel):
    """Style fingerprint extracted from sample texts."""

    model_config = {"protected_namespaces": ()}

    register: Literal["formal", "semi-formal", "casual"] = "formal"
    avg_sentence_length: float = 18.0
    vocabulary_complexity: Literal["simple", "moderate", "advanced"] = "moderate"
    pov: Literal["first", "second", "third"] = "third"
    paragraph_density: Literal["short", "medium", "long"] = "medium"
    discourse_markers: list[str] = Field(default_factory=list)
    common_phrases: list[str] = Field(default_factory=list)
    avoid_phrases: list[str] = Field(default_factory=list)
    notes: str | None = None


class OutlineSection(BaseModel):
    heading: str
    target_words: int
    bullet_points: list[str]
    sources_hint: list[str] = Field(default_factory=list)


class Outline(BaseModel):
    title: str
    sections: list[OutlineSection]

    @property
    def total_target_words(self) -> int:
        return sum(s.target_words for s in self.sections)


class Citation(BaseModel):
    key: str
    authors: list[str]
    year: int
    title: str
    publisher: str | None = None
    url: str | None = None
    formatted: str | None = None


class DraftSection(BaseModel):
    heading: str
    content: str
    word_count: int
    citations: list[str] = Field(default_factory=list)


class Draft(BaseModel):
    title: str
    sections: list[DraftSection]
    citations: list[Citation] = Field(default_factory=list)

    @property
    def total_words(self) -> int:
        return sum(s.word_count for s in self.sections)


class TokenLedger(BaseModel):
    """Tracks token consumption per agent for transparency."""

    by_agent: dict[str, int] = Field(default_factory=dict)
    total: int = 0

    def record(self, agent: str, tokens: int) -> None:
        self.by_agent[agent] = self.by_agent.get(agent, 0) + tokens
        self.total += tokens
