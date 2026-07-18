"""Local LLM fallback tests."""

from __future__ import annotations

import httpx

from config import Settings
from assistant.local_llm import LocalLLM


def test_local_llm_is_unavailable_without_model_path(tmp_path):
    settings = Settings(local_llm_path=tmp_path / "missing.gguf", local_llm_service_url="")
    llm = LocalLLM(settings)
    assert not llm.available()
    assert llm.generate("question", []) is None


def test_local_llm_is_available_with_service_url():
    settings = Settings(local_llm_service_url="http://127.0.0.1:11434")
    llm = LocalLLM(settings)
    assert llm.available()


def test_settings_default_to_local_ollama_service():
    settings = Settings()
    assert settings.local_llm_service_url == "http://127.0.0.1:11434"


def test_generate_remote_parses_ollama_response(monkeypatch):
    settings = Settings(local_llm_service_url="http://127.0.0.1:11434", local_llm_service_model="llama3.2:3b")
    llm = LocalLLM(settings)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "Bonjour depuis Ollama"}

    def fake_post(url, json, timeout):
        return FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)
    result = llm._generate_remote("Question")
    assert result is not None
    assert result.text == "Bonjour depuis Ollama"
