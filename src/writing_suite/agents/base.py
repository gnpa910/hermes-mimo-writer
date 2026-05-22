"""Base class for all agents in the writing pipeline.

Each agent is a small async unit that takes typed input, calls MiMo for
reasoning, and returns typed output. Agents are composed by the orchestrator
in `pipeline.py`. This mirrors Hermes Agent's `delegate_task` pattern where
each subagent has its own focused goal.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ..mimo_client import ChatMessage, MimoClient
from ..models import TokenLedger


log = logging.getLogger(__name__)

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Agent(ABC, Generic[InputT, OutputT]):
    """Abstract base for a single-purpose agent."""

    name: str = "agent"
    system_prompt: str = ""
    use_lite_model: bool = False
    temperature: float = 0.7
    max_tokens: int = 4096

    def __init__(self, client: MimoClient, ledger: TokenLedger | None = None):
        self.client = client
        self.ledger = ledger or TokenLedger()

    @abstractmethod
    async def run(self, input_data: InputT) -> OutputT:
        """Execute the agent."""

    async def _chat(
        self,
        user_prompt: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        """Wrap MimoClient.chat with logging + ledger updates."""
        messages = [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]
        result = await self.client.chat(
            messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            lite=self.use_lite_model,
            response_format=response_format,
        )
        self.ledger.record(self.name, result.token_total)
        log.info(
            "agent=%s tokens=%d (prompt=%d completion=%d)",
            self.name,
            result.token_total,
            result.prompt_tokens,
            result.completion_tokens,
        )
        return result.content
