"""Tests for the MiMo client."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from writing_suite.config import Settings
from writing_suite.mimo_client import (
    ChatMessage,
    ChatResult,
    MimoAPIError,
    MimoClient,
)


@pytest.fixture
def mock_settings() -> Settings:
    from pathlib import Path

    return Settings(
        mimo_api_key="tp-test",
        mimo_endpoint="https://mock-mimo.test/v1",
        mimo_model="mimo-v2.5-pro",
        mimo_model_lite="mimo-v2-flash",
        output_dir=Path("/tmp/x"),
        request_timeout=5.0,
        max_retries=1,
    )


@respx.mock
@pytest.mark.asyncio
async def test_chat_returns_parsed_result(mock_settings):
    respx.post("https://mock-mimo.test/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "x",
                "choices": [
                    {
                        "message": {
                            "content": "hello world",
                            "reasoning_content": "thinking...",
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )
    )

    async with MimoClient(mock_settings) as client:
        result = await client.chat(
            [ChatMessage(role="user", content="hi")], temperature=0.5, max_tokens=100
        )

    assert isinstance(result, ChatResult)
    assert result.content == "hello world"
    assert result.reasoning_content == "thinking..."
    assert result.token_total == 15


@respx.mock
@pytest.mark.asyncio
async def test_chat_uses_lite_model_when_requested(mock_settings):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"total_tokens": 1},
            },
        )

    respx.post("https://mock-mimo.test/v1/chat/completions").mock(side_effect=handler)

    async with MimoClient(mock_settings) as client:
        await client.chat([ChatMessage(role="user", content="x")], lite=True)

    assert captured["body"]["model"] == "mimo-v2-flash"


@respx.mock
@pytest.mark.asyncio
async def test_chat_raises_on_4xx(mock_settings):
    respx.post("https://mock-mimo.test/v1/chat/completions").mock(
        return_value=httpx.Response(401, text="invalid api key")
    )

    async with MimoClient(mock_settings) as client:
        with pytest.raises(MimoAPIError, match="401"):
            await client.chat([ChatMessage(role="user", content="x")])


@respx.mock
@pytest.mark.asyncio
async def test_chat_message_includes_reasoning_content_when_set():
    msg = ChatMessage(
        role="assistant", content="result", reasoning_content="step by step"
    )
    payload = msg.to_payload()
    assert payload["reasoning_content"] == "step by step"
    assert payload["content"] == "result"


def test_chat_message_omits_reasoning_when_none():
    msg = ChatMessage(role="user", content="hi")
    payload = msg.to_payload()
    assert "reasoning_content" not in payload


@respx.mock
@pytest.mark.asyncio
async def test_stream_yields_content_chunks(mock_settings):
    sse_body = (
        "data: " + json.dumps({"choices": [{"delta": {"content": "Hello"}}]}) + "\n"
        "data: " + json.dumps({"choices": [{"delta": {"content": " world"}}]}) + "\n"
        "data: [DONE]\n"
    )
    respx.post("https://mock-mimo.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=sse_body, headers={"content-type": "text/event-stream"})
    )

    chunks: list[str] = []
    async with MimoClient(mock_settings) as client:
        async for c in client.stream([ChatMessage(role="user", content="hi")]):
            chunks.append(c)

    assert chunks == ["Hello", " world"]
