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
        """Return True when a local model path is configured and exists."""

        return bool(self.settings.local_llm_path and self.settings.local_llm_path.exists())

    def generate(self, query: str, results: list[SearchResult]) -> LocalLLMResult | None:
        """Generate a grounded answer from retrieved chunks using a local model."""

        if not self.available():
            return None
        prompt = self._prompt(query, results)
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
                stop=["</s>", "<|user|>", "Question:"],
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
            stop=["</answer>", "Question:"],
        )
        text = str(response["choices"][0]["text"]).strip()
        return LocalLLMResult(text=text, provider="local-llm:llama-cpp")

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
            "<|system|>\n"
            "You are an internal R&D knowledge assistant. Answer only from the context. "
            "Do not invent sources. Cite every claim with the bracketed source label. "
            "If evidence is insufficient, say so briefly.\n"
            "</s>\n"
            "<|user|>\n"
            f"Question: {query}\n\n"
            f"Context:\n{context}\n\n"
            "Write a concise answer in 3 to 5 bullets.\n"
            "</s>\n"
            "<|assistant|>\n"
        )

    def _context_results(self, results: list[SearchResult]) -> list[SearchResult]:
        if not results:
            return []
        max_score = max(result.score for result in results)
        threshold = max_score * 0.25
        selected = [result for result in results if result.score >= threshold]
        return (selected or results[:1])[:3]
