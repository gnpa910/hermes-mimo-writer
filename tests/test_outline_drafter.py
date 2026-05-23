"""Tests for outline drafter."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from writing_suite.agents.outline_drafter import OutlineDrafterAgent
from writing_suite.models import Brief, Outline, StyleProfile, TokenLedger


SAMPLE_OUTLINE_JSON = """
{
  "title": "AI in Education",
  "sections": [
    {"heading": "Introduction", "target_words": 100, "bullet_points": ["context", "thesis"], "sources_hint": ["AI education review"]},
    {"heading": "Personalized Learning", "target_words": 350, "bullet_points": ["adaptive", "feedback"], "sources_hint": []},
    {"heading": "Equity Concerns", "target_words": 350, "bullet_points": ["digital divide", "bias"], "sources_hint": []},
    {"heading": "Conclusion", "target_words": 100, "bullet_points": ["summary"], "sources_hint": []}
  ]
}
"""


@pytest.mark.asyncio
async def test_outline_drafter_produces_valid_outline(sample_brief, sample_style):
    mock_client = AsyncMock()
    agent = OutlineDrafterAgent(mock_client, TokenLedger())
    agent._chat = AsyncMock(return_value=SAMPLE_OUTLINE_JSON)

    result = await agent.run((sample_brief, sample_style))

    assert isinstance(result, Outline)
    assert result.title == "AI in Education"
    assert len(result.sections) == 4
    assert result.total_target_words == 900  # 100+350+350+100


@pytest.mark.asyncio
async def test_outline_drafter_includes_brief_and_style_in_prompt(
    sample_brief, sample_style
):
    mock_client = AsyncMock()
    agent = OutlineDrafterAgent(mock_client, TokenLedger())
    captured = []

    async def fake_chat(prompt, **kw):
        captured.append(prompt)
        return SAMPLE_OUTLINE_JSON

    agent._chat = fake_chat

    await agent.run((sample_brief, sample_style))

    prompt = captured[0]
    assert "AI in Modern Education" in prompt
    assert "formal" in prompt  # from style


def test_outline_drafter_uses_pro_model():
    assert OutlineDrafterAgent.use_lite_model is False
