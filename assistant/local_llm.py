"""Local-only LLM wrapper for grounded RAG answers."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from config import Settings
from db.models import SearchResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LocalLLMResult:
    """Generated text and backend metadata from a local model."""

    text: str
    provider: str


class LocalLLM:
    """Generate answers with an optional local model file.

    Supported backends are intentionally local-only:
    - ctransformers for GGUF/GGML style model files.
    - llama-cpp-python for GGUF model files.

    If the backend, dependency, or model path is unavailable, this class returns
    None so the assistant can fall back to extractive grounded answers.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: object | None = None

    def available(self) -> bool:
        """Return True when a local model path or remote service URL is configured."""

        return bool(
            self.settings.local_llm_service_url
            or (self.settings.local_llm_path and self.settings.local_llm_path.exists())
        )

    def generate(self, query: str, results: list[SearchResult]) -> LocalLLMResult | None:
        """Generate a grounded answer from retrieved chunks using a local model or remote service."""

        if not self.available():
            return None
        prompt = self._prompt(query, results)
        if self.settings.local_llm_service_url:
            result = self._generate_remote(prompt)
            if result or not (self.settings.local_llm_path and self.settings.local_llm_path.exists()):
                return result
            logger.warning("Remote LLM failed; falling back to local model path.")
        backend = self.settings.local_llm_backend.lower().strip()
        if backend == "llama-cpp":
            return self._generate_llama_cpp(prompt)
        return self._generate_ctransformers(prompt)

    def _generate_ctransformers(self, prompt: str) -> LocalLLMResult | None:
        try:
            from ctransformers import AutoModelForCausalLM
        except ImportError:
            logger.warning("ctransformers is not installed; falling back to extractive answer")
            return None

        if self._model is None:
            self._model = AutoModelForCausalLM.from_pretrained(
                str(self.settings.local_llm_path),
                model_type=self.settings.local_llm_model_type,
                gpu_layers=0,
                context_length=2048,
            )
        text = str(
            self._model(
                prompt,
                max_new_tokens=self.settings.local_llm_max_new_tokens,
                temperature=0.1,
                repetition_penalty=1.1,
                stop=["</s>", "<|user|>", "Question:", "Question :"],
            )
        ).strip()
        return LocalLLMResult(text=text, provider="local-llm:ctransformers")

    def _generate_llama_cpp(self, prompt: str) -> LocalLLMResult | None:
        try:
            from llama_cpp import Llama
        except ImportError:
            logger.warning("llama-cpp-python is not installed; falling back to extractive answer")
            return None

        if self._model is None:
            self._model = Llama(
                model_path=str(self.settings.local_llm_path),
                n_ctx=4096,
                n_threads=None,
                n_gpu_layers=0,
                verbose=False,
            )
        response = self._model(
            prompt,
            max_tokens=self.settings.local_llm_max_new_tokens,
            temperature=0.1,
            stop=["</answer>", "Question:", "Question :"],
        )
        text = str(response["choices"][0]["text"]).strip()
        return LocalLLMResult(text=text, provider="local-llm:llama-cpp")

    def _generate_remote(self, prompt: str) -> LocalLLMResult | None:
        try:
            import httpx
        except ImportError:
            logger.warning("httpx is not installed; falling back to extractive answer")
            return None

        url = self.settings.local_llm_service_url.rstrip("/") + "/api/generate"
        payload = {
            "model": self.settings.local_llm_service_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": self.settings.local_llm_max_new_tokens,
                "temperature": 0.1,
            },
        }

        try:
            response = httpx.post(url, json=payload, timeout=self.settings.local_llm_timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning("Remote LLM request failed: %s", exc)
            return None

        text = ""
        if isinstance(data, dict):
            if data.get("response"):
                text = str(data["response"]).strip()
            else:
                choices = data.get("choices") or []
                if choices:
                    choice = choices[0]
                    text = choice.get("text") or choice.get("message", {}).get("content", "")
                if not text and "result" in data:
                    result = data["result"]
                    if isinstance(result, dict):
                        text = result.get("output", "")
                    else:
                        text = str(result)
        text = str(text).strip()
        if not text:
            logger.warning("Remote LLM returned no text")
            return None
        return LocalLLMResult(text=text, provider=f"remote-llm:{self.settings.local_llm_service_model}")

    def _prompt(self, query: str, results: list[SearchResult]) -> str:
        context_parts: list[str] = []
        remaining = self.settings.local_llm_context_chars
        for result in self._context_results(results):
            citation = f"{result.filename}, chunk {result.chunk_index + 1}"
            content = result.content.strip()[:900]
            block = f"[{citation}]\n{content}\n"
            if remaining <= 0:
                break
            context_parts.append(block[:remaining])
            remaining -= len(block)
        context = "\n".join(context_parts)
        return (
            "Vous êtes un assistant interne de connaissances R&D. "
            "Répondez uniquement en français, quelle que soit la langue de la question. "
            "Répondez uniquement à partir du contexte fourni et ne fabriquez aucune source. "
            "Citez chaque affirmation avec l'étiquette de source entre crochets. "
            "Si les preuves sont insuffisantes, dites-le brièvement.\n\n"
            f"Question : {query}\n\n"
            f"Contexte :\n{context}\n\n"
            "Rédigez une réponse concise en 3 à 5 puces, en français.\n"
            "Réponse :"
        )

    def _context_results(self, results: list[SearchResult]) -> list[SearchResult]:
        if not results:
            return []
        max_score = max(result.score for result in results)
        threshold = max_score * 0.25
        selected = [result for result in results if result.score >= threshold]
        return (selected or results[:1])[:3]
