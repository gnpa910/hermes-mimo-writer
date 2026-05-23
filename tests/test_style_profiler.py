"""Tests for the style profiler agent."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from writing_suite.agents.style_profiler import StyleProfilerAgent
from writing_suite.models import StyleProfile, TokenLedger


@pytest.mark.asyncio
async def test_empty_samples_returns_default_profile():
    """No samples = default profile, no MiMo call."""
    mock_client = AsyncMock()
    agent = StyleProfilerAgent(mock_client, TokenLedger())
    agent._chat = AsyncMock()  # should not be called

    result = await agent.run([])

    assert isinstance(result, StyleProfile)
    assert result.register == "formal"
    agent._chat.assert_not_called()


@pytest.mark.asyncio
async def test_with_samples_calls_chat():
    mock_client = AsyncMock()
    agent = StyleProfilerAgent(mock_client, TokenLedger())
    agent._chat = AsyncMock(
        return_value='{"register": "casual", "avg_sentence_length": 12.0, "vocabulary_complexity": "simple", "pov": "first", "paragraph_density": "short", "discourse_markers": [], "common_phrases": [], "avoid_phrases": [], "notes": null}'
    )

    result = await agent.run(["This is my voice. I write casually."])

    assert result.register == "casual"
    assert result.pov == "first"
    agent._chat.assert_called_once()


@pytest.mark.asyncio
async def test_caps_samples_at_five():
    mock_client = AsyncMock()
    agent = StyleProfilerAgent(mock_client, TokenLedger())
    captured_prompt = []

    async def fake_chat(prompt, **kw):
        captured_prompt.append(prompt)
        return '{"register": "formal", "avg_sentence_length": 15.0, "vocabulary_complexity": "moderate", "pov": "third", "paragraph_density": "medium", "discourse_markers": [], "common_phrases": [], "avoid_phrases": [], "notes": null}'

    agent._chat = fake_chat

    samples = [f"sample {i}" for i in range(10)]
    await agent.run(samples)

    # Should only include 5 samples in the prompt
    assert captured_prompt[0].count("---SAMPLE---") == 4  # 5 samples = 4 separators


def test_uses_pro_model_for_quality():
    assert StyleProfilerAgent.use_lite_model is False
    assert StyleProfilerAgent.temperature == 0.2  # low temp for analytical task
