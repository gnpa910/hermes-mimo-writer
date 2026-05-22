"""Async client for the Xiaomi MiMo Token Plan API.

The Token Plan endpoint accepts OpenAI-compatible chat/completions requests
with an `api-key` header (not Bearer). MiMo V2.5-Pro returns reasoning_content
on tool-calling chains; downstream agents must echo it back in multi-turn
conversations or the API returns 400.

Refs:
    https://platform.xiaomimimo.com/docs/en-US/welcome
    https://platform.xiaomimimo.com/docs/en-US/api/openai
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import Settings


log = logging.getLogger(__name__)


class MimoAPIError(RuntimeError):
    """Wrapped error from the MiMo API."""


@dataclass
class ChatMessage:
    role: str
    content: str
    reasoning_content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.reasoning_content is not None:
            payload["reasoning_content"] = self.reasoning_content
        if self.tool_calls is not None:
            payload["tool_calls"] = self.tool_calls
        return payload


@dataclass
class ChatResult:
    content: str
    reasoning_content: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def token_total(self) -> int:
        return self.total_tokens or (self.prompt_tokens + self.completion_tokens)


class MimoClient:
    """Async chat client targeting the MiMo Token Plan endpoint."""

    def __init__(self, settings: Settings, *, http_client: httpx.AsyncClient | None = None):
        self._settings = settings
        self._http = http_client or httpx.AsyncClient(
            base_url=settings.mimo_endpoint,
            timeout=settings.request_timeout,
            headers={
                "api-key": settings.mimo_api_key,
                "Content-Type": "application/json",
            },
        )
        self._owns_http = http_client is None

    async def __aenter__(self) -> "MimoClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    def _model_for(self, lite: bool) -> str:
        return self._settings.mimo_model_lite if lite else self._settings.mimo_model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        lite: bool = False,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatResult:
        """Single-shot non-streaming chat completion."""
        payload: dict[str, Any] = {
            "model": self._model_for(lite),
            "messages": [m.to_payload() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._settings.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=20),
            retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
            reraise=True,
        ):
            with attempt:
                resp = await self._http.post("/chat/completions", json=payload)
                if resp.status_code >= 500:
                    resp.raise_for_status()
                if resp.status_code >= 400:
                    raise MimoAPIError(
                        f"MiMo API {resp.status_code}: {resp.text[:500]}"
                    )
                data = resp.json()
                return self._parse_result(data)

        raise MimoAPIError("retry loop exhausted without result")

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        lite: bool = False,
    ) -> AsyncIterator[str]:
        """Server-Sent Events streaming. Yields content chunks as they arrive."""
        payload = {
            "model": self._model_for(lite),
            "messages": [m.to_payload() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with self._http.stream("POST", "/chat/completions", json=payload) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise MimoAPIError(
                    f"MiMo stream {resp.status_code}: {body.decode()[:500]}"
                )
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                chunk = line[6:].strip()
                if chunk == "[DONE]":
                    return
                try:
                    parsed = json.loads(chunk)
                except json.JSONDecodeError:
                    log.debug("skipping malformed SSE chunk: %r", chunk)
                    continue
                delta = parsed.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content

    @staticmethod
    def _parse_result(data: dict[str, Any]) -> ChatResult:
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        return ChatResult(
            content=message.get("content") or "",
            reasoning_content=message.get("reasoning_content"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            raw=data,
        )
