"""Local LLM fallback tests."""

from __future__ import annotations

from config import Settings
from assistant.local_llm import LocalLLM


def test_local_llm_is_unavailable_without_model_path(tmp_path):
    settings = Settings(local_llm_path=tmp_path / "missing.gguf")
    llm = LocalLLM(settings)
    assert not llm.available()
    assert llm.generate("question", []) is None
