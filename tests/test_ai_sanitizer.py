"""Tests for AI sanitizer."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from writing_suite.agents.ai_sanitizer import AISanitizerAgent
from writing_suite.models import Draft, DraftSection, TokenLedger


@pytest.mark.asyncio
async def test_sanitizer_rewrites_each_section(sample_brief, sample_style, sample_draft):
    mock_client = AsyncMock()
    agent = AISanitizerAgent(mock_client, TokenLedger())
    agent._chat = AsyncMock(return_value="Rewritten prose. Short. And then a longer sentence with more variation.")

    result = await agent.run((sample_brief, sample_style, sample_draft))

    assert isinstance(result, Draft)
    assert len(result.sections) == len(sample_draft.sections)
    assert all("Rewritten" in s.content for s in result.sections)


@pytest.mark.asyncio
async def test_sanitizer_preserves_citations(sample_brief, sample_style):
    """Citations must survive sanitization."""
    draft = Draft(
        title="T",
        sections=[
            DraftSection(
                heading="Intro",
                content="orig",
                word_count=10,
                citations=["Smith_2021", "Jones_2022"],
            )
        ],
    )
    mock_client = AsyncMock()
    agent = AISanitizerAgent(mock_client, TokenLedger())
    agent._chat = AsyncMock(return_value="new content with [Smith, 2021]")

    result = await agent.run((sample_brief, sample_style, draft))

    assert result.sections[0].citations == ["Smith_2021", "Jones_2022"]


def test_sanitizer_uses_high_temperature():
    """Variation matters more than precision here."""
    assert AISanitizerAgent.temperature >= 0.8
