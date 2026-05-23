"""Tests for config loading."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from writing_suite.config import Settings


def test_from_env_requires_api_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="MIMO_API_KEY"):
            Settings.from_env()


def test_from_env_uses_defaults(tmp_path):
    with patch.dict(
        os.environ,
        {"MIMO_API_KEY": "tp-x", "OUTPUT_DIR": str(tmp_path)},
        clear=True,
    ):
        s = Settings.from_env()
        assert s.mimo_endpoint == "https://token-plan-sgp.xiaomimimo.com/v1"
        assert s.mimo_model == "mimo-v2.5-pro"
        assert s.mimo_model_lite == "mimo-v2-flash"
        assert s.output_dir == tmp_path


def test_from_env_overrides(tmp_path):
    with patch.dict(
        os.environ,
        {
            "MIMO_API_KEY": "tp-y",
            "MIMO_MODEL": "mimo-v2.5",
            "MIMO_ENDPOINT": "https://custom.example/v1",
            "OUTPUT_DIR": str(tmp_path),
            "MIMO_TIMEOUT": "30",
        },
        clear=True,
    ):
        s = Settings.from_env()
        assert s.mimo_model == "mimo-v2.5"
        assert s.mimo_endpoint == "https://custom.example/v1"
        assert s.request_timeout == 30.0


def test_ensure_output_dir_creates(tmp_path):
    s = Settings(
        mimo_api_key="x",
        mimo_endpoint="x",
        mimo_model="x",
        mimo_model_lite="x",
        output_dir=tmp_path / "deep" / "nested",
        request_timeout=10,
        max_retries=1,
    )
    out = s.ensure_output_dir()
    assert out.exists()
    assert out.is_dir()
