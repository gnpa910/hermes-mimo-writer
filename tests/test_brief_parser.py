"""Tests for the brief parser agent."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from writing_suite.agents.brief_parser import BriefParserAgent, _extract_json
from writing_suite.models import Brief, TokenLedger


def test_extract_json_clean():
    raw = '{"title": "x", "word_count": 1000}'
    assert _extract_json(raw) == {"title": "x", "word_count": 1000}


def test_extract_json_with_markdown_fence():
    raw = '```json\n{"title": "x", "word_count": 1000}\n```'
    assert _extract_json(raw) == {"title": "x", "word_count": 1000}


def test_extract_json_with_prose_around():
    raw = 'Here is the JSON:\n{"title": "x", "word_count": 1000}\nThanks!'
    assert _extract_json(raw) == {"title": "x", "word_count": 1000}


def test_extract_json_raises_when_missing():
    with pytest.raises(ValueError, match="no JSON object"):
        _extract_json("just text no json")


@pytest.mark.asyncio
async def test_brief_parser_returns_brief_model():
    mock_client = AsyncMock()
    ledger = TokenLedger()
    agent = BriefParserAgent(mock_client, ledger)
    agent._chat = AsyncMock(
        return_value='{"title": "Education and AI", "word_count": 1500, "language": "id", "citation_style": "APA", "audience": "students", "rubric": ["analysis"], "keywords": ["ai"], "course": null, "notes": null}'
    )

    result = await agent.run("Tugas: tulis 1500 kata tentang AI dalam pendidikan.")

    assert isinstance(result, Brief)
    assert result.word_count == 1500
    assert result.language == "id"
    assert "ai" in result.keywords


@pytest.mark.asyncio
async def test_brief_parser_uses_lite_model():
    """Verify cost-saver flag is set."""
    assert BriefParserAgent.use_lite_model is True
    assert BriefParserAgent.temperature == 0.1  # parsing is deterministic
