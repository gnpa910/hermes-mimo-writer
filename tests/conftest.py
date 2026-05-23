"""Shared test fixtures."""
from __future__ import annotations

import pytest

from writing_suite.config import Settings
from writing_suite.models import (
    Brief,
    Draft,
    DraftSection,
    Outline,
    OutlineSection,
    StyleProfile,
    TokenLedger,
)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        mimo_api_key="tp-test-key",
        mimo_endpoint="https://token-plan-sgp.xiaomimimo.com/v1",
        mimo_model="mimo-v2.5-pro",
        mimo_model_lite="mimo-v2-flash",
        output_dir=tmp_path / "output",
        request_timeout=10.0,
        max_retries=1,
    )


@pytest.fixture
def sample_brief() -> Brief:
    return Brief(
        title="The Role of AI in Modern Education",
        course="EDU101",
        word_count=1000,
        language="en",
        citation_style="APA",
        rubric=["Critical analysis", "5+ sources", "Original argument"],
        keywords=["artificial intelligence", "education", "pedagogy"],
    )


@pytest.fixture
def sample_style() -> StyleProfile:
    return StyleProfile(
        register="formal",
        avg_sentence_length=20.0,
        vocabulary_complexity="moderate",
        pov="third",
        paragraph_density="medium",
    )


@pytest.fixture
def sample_outline() -> Outline:
    return Outline(
        title="The Role of AI in Modern Education",
        sections=[
            OutlineSection(
                heading="Introduction",
                target_words=150,
                bullet_points=["Define AI in education", "Thesis statement"],
            ),
            OutlineSection(
                heading="Personalized Learning",
                target_words=350,
                bullet_points=["Adaptive systems", "Student outcomes"],
            ),
            OutlineSection(
                heading="Conclusion",
                target_words=150,
                bullet_points=["Summary", "Future directions"],
            ),
        ],
    )


@pytest.fixture
def sample_draft() -> Draft:
    return Draft(
        title="The Role of AI in Modern Education",
        sections=[
            DraftSection(
                heading="Introduction",
                content="AI in education has grown rapidly [Smith, 2021]. This paper examines its role.",
                word_count=14,
                citations=["Smith_2021"],
            ),
            DraftSection(
                heading="Personalized Learning",
                content="Adaptive systems improve outcomes [Jones, 2022]. Studies show 30% gains.",
                word_count=10,
                citations=["Jones_2022"],
            ),
        ],
    )


@pytest.fixture
def empty_ledger() -> TokenLedger:
    return TokenLedger()
