"""Local LLM fallback tests."""

from __future__ import annotations

import httpx

from config import Settings
from assistant.local_llm import LocalLLM


def test_local_llm_is_unavailable_without_model_path(tmp_path):
    settings = Settings(local_llm_service_url="")
    llm = LocalLLM(settings)
    assert not llm.available()
    assert llm.generate("question", []) is None


def test_local_llm_is_available_with_service_url():
    settings = Settings(local_llm_service_url="http://127.0.0.1:11434")
    llm = LocalLLM(settings)
    assert llm.available()


def test_settings_default_to_local_only_mode():
    settings = Settings()
    assert settings.local_llm_service_url == "http://127.0.0.1:11434"


def test_generate_remote_parses_ollama_response(monkeypatch):
    settings = Settings(local_llm_service_url="http://127.0.0.1:11434", local_llm_service_model="llama3.2:3b")
    llm = LocalLLM(settings)

    class FakeResponse:
        def __init__(self, lines):
            self._lines = lines

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield from self._lines

    class FakeClient:
        def stream(self, method, url, json):
            payloads = [
                '{"response": "Bonjour depuis "}',
                '{"response": "Ollama", "done": true}',
            ]
            return FakeResponse(payloads)

    monkeypatch.setattr(llm, "_client_session", lambda: FakeClient())
    result = llm._generate_remote("Question")
    assert result is not None
    assert result.text == "Bonjour depuis Ollama"
