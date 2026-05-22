"""Configuration loaded from environment variables (.env supported)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the writing suite."""

    mimo_api_key: str
    mimo_endpoint: str
    mimo_model: str
    mimo_model_lite: str
    output_dir: Path
    request_timeout: float
    max_retries: int

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.getenv("MIMO_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "MIMO_API_KEY is required. Set it in .env or export it. "
                "Get a key from https://platform.xiaomimimo.com/"
            )

        return cls(
            mimo_api_key=api_key,
            mimo_endpoint=os.getenv(
                "MIMO_ENDPOINT", "https://token-plan-sgp.xiaomimimo.com/v1"
            ),
            mimo_model=os.getenv("MIMO_MODEL", "mimo-v2.5-pro"),
            mimo_model_lite=os.getenv("MIMO_MODEL_LITE", "mimo-v2-flash"),
            output_dir=Path(os.getenv("OUTPUT_DIR", "./output")).expanduser(),
            request_timeout=float(os.getenv("MIMO_TIMEOUT", "120")),
            max_retries=int(os.getenv("MIMO_MAX_RETRIES", "3")),
        )

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir
