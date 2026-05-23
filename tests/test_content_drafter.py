"""Tests for content drafter."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from writing_suite.agents.content_drafter import ContentDrafterAgent
from writing_suite.models import Draft, TokenLedger


@pytest.mark.asyncio
async def test_content_drafter_drafts_each_section(
    sample_brief, sample_style, sample_outline
):
    mock_client = AsyncMock()
    agent = ContentDrafterAgent(mock_client, TokenLedger())
    agent._chat = AsyncMock(
        return_value="This is drafted content with citation [Smith, 2021]."
    )

    result = await agent.run((sample_brief, sample_style, sample_outline))

    assert isinstance(result, Draft)
    assert len(result.sections) == len(sample_outline.sections)
    assert agent._chat.call_count == len(sample_outline.sections)


@pytest.mark.asyncio
async def test_content_drafter_extracts_citation_keys(
    sample_brief, sample_style, sample_outline
):
    mock_client = AsyncMock()
    agent = ContentDrafterAgent(mock_client, TokenLedger())
    agent._chat = AsyncMock(
        return_value="Recent work [Smith, 2021] and [Jones, 2022a] explores this."
    )

    result = await agent.run((sample_brief, sample_style, sample_outline))

    for section in result.sections:
        assert "Smith_2021" in section.citations
        assert "Jones_2022a" in section.citations


def test_extract_citation_keys_dedupes():
    text = "[Smith, 2021] and [Smith, 2021] same source twice."
    keys = ContentDrafterAgent._extract_citation_keys(text)
    assert keys == ["Smith_2021"]


def test_extract_citation_keys_handles_compound_names():
    text = "Per [Van Der Berg, 2020], reform is needed."
    keys = ContentDrafterAgent._extract_citation_keys(text)
    assert keys == ["Van Der Berg_2020"]


def test_content_drafter_uses_pro_model():
    assert ContentDrafterAgent.use_lite_model is False
