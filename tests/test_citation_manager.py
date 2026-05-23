"""Tests for citation manager."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from writing_suite.agents.citation_manager import CitationManagerAgent
from writing_suite.models import Citation, TokenLedger


SAMPLE_CITATIONS_JSON = """
{
  "citations": [
    {
      "key": "Smith_2021",
      "authors": ["Smith, J."],
      "year": 2021,
      "title": "AI in Classrooms",
      "publisher": "Routledge",
      "url": null,
      "formatted": "Smith, J. (2021). AI in Classrooms. Routledge."
    },
    {
      "key": "Jones_2022",
      "authors": ["Jones, A.", "Brown, B."],
      "year": 2022,
      "title": "Adaptive Learning Systems",
      "publisher": "Journal of EdTech",
      "url": null,
      "formatted": "Jones, A. & Brown, B. (2022). Adaptive Learning Systems. Journal of EdTech."
    }
  ]
}
"""


@pytest.mark.asyncio
async def test_citation_manager_returns_empty_when_no_keys(sample_brief):
    """Draft with no citations = empty result, no MiMo call."""
    from writing_suite.models import Draft

    draft = Draft(title="T", sections=[])
    mock_client = AsyncMock()
    agent = CitationManagerAgent(mock_client, TokenLedger())
    agent._chat = AsyncMock()

    result = await agent.run((sample_brief, draft))

    assert result == []
    agent._chat.assert_not_called()


@pytest.mark.asyncio
async def test_citation_manager_resolves_keys(sample_brief, sample_draft):
    mock_client = AsyncMock()
    agent = CitationManagerAgent(mock_client, TokenLedger())
    agent._chat = AsyncMock(return_value=SAMPLE_CITATIONS_JSON)

    result = await agent.run((sample_brief, sample_draft))

    assert len(result) == 2
    assert all(isinstance(c, Citation) for c in result)
    keys = {c.key for c in result}
    assert "Smith_2021" in keys
    assert "Jones_2022" in keys


@pytest.mark.asyncio
async def test_citation_manager_dedupes_keys_across_sections(
    sample_brief, sample_draft
):
    """Same citation in multiple sections = resolved once."""
    sample_draft.sections[1].citations.append("Smith_2021")  # duplicate

    captured = []

    async def fake_chat(prompt, **kw):
        captured.append(prompt)
        return SAMPLE_CITATIONS_JSON

    mock_client = AsyncMock()
    agent = CitationManagerAgent(mock_client, TokenLedger())
    agent._chat = fake_chat

    await agent.run((sample_brief, sample_draft))

    # Smith_2021 should appear once in the keys list passed to MiMo
    prompt = captured[0]
    assert prompt.count("Smith_2021") <= 3  # 1 in keys list + max 2 in section topics
