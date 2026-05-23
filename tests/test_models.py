"""Tests for domain models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from writing_suite.models import (
    Brief,
    Citation,
    Draft,
    DraftSection,
    Outline,
    OutlineSection,
    StyleProfile,
    TokenLedger,
)


class TestBrief:
    def test_minimal_brief(self):
        b = Brief(title="Test", word_count=1000)
        assert b.language == "en"
        assert b.citation_style == "APA"
        assert b.rubric == []

    def test_word_count_lower_bound(self):
        with pytest.raises(ValidationError):
            Brief(title="t", word_count=50)

    def test_word_count_upper_bound(self):
        with pytest.raises(ValidationError):
            Brief(title="t", word_count=50000)

    def test_language_validation(self):
        Brief(title="t", word_count=1000, language="id")
        Brief(title="t", word_count=1000, language="ms")
        with pytest.raises(ValidationError):
            Brief(title="t", word_count=1000, language="fr")

    def test_citation_style_validation(self):
        for style in ["APA", "MLA", "Chicago", "Harvard"]:
            Brief(title="t", word_count=1000, citation_style=style)
        with pytest.raises(ValidationError):
            Brief(title="t", word_count=1000, citation_style="IEEE")


class TestStyleProfile:
    def test_default(self):
        s = StyleProfile()
        assert s.register == "formal"
        assert s.pov == "third"

    def test_register_values(self):
        for reg in ["formal", "semi-formal", "casual"]:
            StyleProfile(register=reg)
        with pytest.raises(ValidationError):
            StyleProfile(register="extreme")


class TestOutline:
    def test_total_target_words(self):
        o = Outline(
            title="T",
            sections=[
                OutlineSection(heading="A", target_words=100, bullet_points=["x"]),
                OutlineSection(heading="B", target_words=200, bullet_points=["y"]),
            ],
        )
        assert o.total_target_words == 300


class TestDraft:
    def test_total_words(self):
        d = Draft(
            title="T",
            sections=[
                DraftSection(heading="A", content="x", word_count=100),
                DraftSection(heading="B", content="y", word_count=250),
            ],
        )
        assert d.total_words == 350

    def test_default_citations_empty(self):
        d = Draft(title="T", sections=[])
        assert d.citations == []


class TestCitation:
    def test_minimal(self):
        c = Citation(key="Smith_2020", authors=["Smith, J."], year=2020, title="x")
        assert c.publisher is None
        assert c.url is None


class TestTokenLedger:
    def test_initial_state(self):
        led = TokenLedger()
        assert led.total == 0
        assert led.by_agent == {}

    def test_record_single_agent(self):
        led = TokenLedger()
        led.record("brief_parser", 100)
        assert led.total == 100
        assert led.by_agent["brief_parser"] == 100

    def test_record_accumulates(self):
        led = TokenLedger()
        led.record("a", 50)
        led.record("a", 30)
        led.record("b", 20)
        assert led.total == 100
        assert led.by_agent == {"a": 80, "b": 20}
