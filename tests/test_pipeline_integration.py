"""Integration test for the full pipeline with mocked MiMo."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from writing_suite.config import Settings
from writing_suite.mimo_client import ChatResult
from writing_suite.pipeline import PipelineInput, WritingPipeline


def _result(content: str, tokens: int = 100) -> ChatResult:
    return ChatResult(
        content=content,
        prompt_tokens=tokens // 2,
        completion_tokens=tokens // 2,
        total_tokens=tokens,
    )


PARSER_OUT = json.dumps(
    {
        "title": "AI in Education",
        "course": "EDU101",
        "word_count": 800,
        "language": "en",
        "citation_style": "APA",
        "audience": "students",
        "rubric": ["analysis"],
        "keywords": ["ai"],
        "notes": None,
    }
)

STYLE_OUT = json.dumps(
    {
        "register": "formal",
        "avg_sentence_length": 18.0,
        "vocabulary_complexity": "moderate",
        "pov": "third",
        "paragraph_density": "medium",
        "discourse_markers": [],
        "common_phrases": [],
        "avoid_phrases": [],
        "notes": None,
    }
)

OUTLINE_OUT = json.dumps(
    {
        "title": "AI in Education",
        "sections": [
            {
                "heading": "Introduction",
                "target_words": 200,
                "bullet_points": ["context"],
                "sources_hint": [],
            },
            {
                "heading": "Body",
                "target_words": 400,
                "bullet_points": ["analysis"],
                "sources_hint": [],
            },
            {
                "heading": "Conclusion",
                "target_words": 200,
                "bullet_points": ["summary"],
                "sources_hint": [],
            },
        ],
    }
)

DRAFT_SECTION_OUT = "This is a sample paragraph with [Smith, 2021] cited."

CITATION_OUT = json.dumps(
    {
        "citations": [
            {
                "key": "Smith_2021",
                "authors": ["Smith, J."],
                "year": 2021,
                "title": "X",
                "publisher": "Y",
                "url": None,
                "formatted": "Smith, J. (2021). X. Y.",
            }
        ]
    }
)


@pytest.mark.asyncio
async def test_full_pipeline_with_mocked_mimo(tmp_path):
    settings = Settings(
        mimo_api_key="tp-test",
        mimo_endpoint="https://mock.test/v1",
        mimo_model="mimo-v2.5-pro",
        mimo_model_lite="mimo-v2-flash",
        output_dir=tmp_path,
        request_timeout=5.0,
        max_retries=1,
    )

    call_count = {"n": 0}

    async def fake_chat(messages, **kw):
        call_count["n"] += 1
        # First call: brief parser. Then style. Then outline. Then 3 drafts. Then 3 sanitizes. Then citations.
        n = call_count["n"]
        if n == 1:
            return _result(PARSER_OUT)
        if n == 2:
            return _result(STYLE_OUT)
        if n == 3:
            return _result(OUTLINE_OUT)
        if 4 <= n <= 6:
            return _result(DRAFT_SECTION_OUT)
        if 7 <= n <= 9:
            return _result(DRAFT_SECTION_OUT + " (sanitized)")
        return _result(CITATION_OUT)

    output = tmp_path / "essay.docx"
    pi = PipelineInput(
        brief_text="Write a 800-word essay on AI in education. APA style.",
        style_samples=["This is a sample text for style profiling."],
        output_path=output,
    )

    with patch(
        "writing_suite.mimo_client.MimoClient.chat", side_effect=fake_chat
    ):
        pipeline = WritingPipeline(settings)
        result = await pipeline.run(pi)

    assert output.exists()
    assert result.brief.word_count == 800
    assert len(result.draft.sections) == 3
    assert result.ledger.total > 0
    assert "brief_parser" in result.ledger.by_agent
    assert "content_drafter" in result.ledger.by_agent


@pytest.mark.asyncio
async def test_pipeline_skip_sanitize_flag(tmp_path):
    settings = Settings(
        mimo_api_key="tp-test",
        mimo_endpoint="https://mock.test/v1",
        mimo_model="mimo-v2.5-pro",
        mimo_model_lite="mimo-v2-flash",
        output_dir=tmp_path,
        request_timeout=5.0,
        max_retries=1,
    )

    call_count = {"n": 0}

    async def fake_chat(messages, **kw):
        call_count["n"] += 1
        n = call_count["n"]
        # No style samples = style profiler returns default without calling MiMo
        if n == 1:
            return _result(PARSER_OUT)
        if n == 2:
            return _result(OUTLINE_OUT)
        if 3 <= n <= 5:
            return _result(DRAFT_SECTION_OUT)
        return _result(CITATION_OUT)

    pi = PipelineInput(
        brief_text="x",
        style_samples=[],
        output_path=tmp_path / "noskip.docx",
        skip_sanitize=True,
    )

    with patch("writing_suite.mimo_client.MimoClient.chat", side_effect=fake_chat):
        pipeline = WritingPipeline(settings)
        await pipeline.run(pi)

    # 1 parser + 0 style (no samples) + 1 outline + 3 drafts + 0 sanitize + 1 citations = 6
    assert call_count["n"] == 6
