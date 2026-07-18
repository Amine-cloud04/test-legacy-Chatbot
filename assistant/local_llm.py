"""Local Ollama wrapper for grounded RAG answers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Callable, Iterable

import httpx

from config import Settings
from db.models import SearchResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LocalLLMResult:
    """Generated text and backend metadata from the local Ollama model."""

    text: str
    provider: str


class LocalLLM:
    """Generate answers with the local Ollama service."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: httpx.Client | None = None

    def available(self) -> bool:
        """Return True when an Ollama endpoint is configured."""

        return bool(self.settings.local_llm_service_url)

    def generate(
        self,
        query: str,
        results: list[SearchResult],
        on_chunk: Callable[[str], None] | None = None,
    ) -> LocalLLMResult | None:
        """Generate a grounded answer from retrieved chunks."""

        if not self.available():
            return None
        prompt = self._prompt(query, results)
        return self._generate_remote(prompt, on_chunk=on_chunk)

    def stream(self, query: str, results: list[SearchResult]) -> Iterable[str]:
        """Yield answer chunks as they are streamed by Ollama."""

        buffer: list[str] = []

        def collect(chunk: str) -> None:
            buffer.append(chunk)

        result = self.generate(query, results, on_chunk=collect)
        if result is None:
            return []
        return buffer

    def _client_session(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.settings.local_llm_timeout)
        return self._client

    def _generate_remote(self, prompt: str, on_chunk: Callable[[str], None] | None = None) -> LocalLLMResult | None:
        url = self.settings.local_llm_service_url.rstrip("/") + "/api/generate"
        payload = {
            "model": self.settings.local_llm_service_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": self.settings.local_llm_max_new_tokens,
                "temperature": 0.1,
                "top_p": 0.9,
            },
        }

        text_parts: list[str] = []
        try:
            with self._client_session().stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        data = json.loads(raw_line)
                    except json.JSONDecodeError:
                        logger.debug("Ignoring non-JSON Ollama stream line: %s", raw_line)
                        continue
                    chunk = str(data.get("response") or "")
                    if chunk:
                        text_parts.append(chunk)
                        if on_chunk is not None:
                            on_chunk(chunk)
                    if data.get("done"):
                        break
        except Exception as exc:
            logger.warning("Remote LLM request failed: %s", exc)
            return None

        text = "".join(text_parts).strip()
        if not text:
            logger.warning("Remote LLM returned no text")
            return None
        return LocalLLMResult(text=text, provider=f"remote-llm:{self.settings.local_llm_service_model}")

    def _prompt(self, query: str, results: list[SearchResult]) -> str:
        context = self._build_context(results)
        return (
            "Vous êtes un assistant technique interne Safran pour la R&D et les projets d'ingénierie.\n"
            "Répondez exclusivement en français naturel et professionnel, même si la question ou le contexte contient de l'anglais.\n"
            "N'utilisez jamais de phrases anglaises complètes ; gardez seulement les acronymes techniques indispensables.\n"
            "N'inventez aucune information et n'utilisez que le contexte fourni.\n"
            "Synthétisez les informations issues de plusieurs documents quand c'est utile.\n"
            "Si les éléments sont insuffisants, dites-le clairement et brièvement.\n"
            "Si des documents se contredisent, expliquez la différence au lieu de choisir arbitrairement.\n"
            "Citez naturellement les sources entre crochets au fil de la réponse.\n"
            "Évitez les longs copier-coller du contexte.\n\n"
            f"Question : {query}\n\n"
            f"Contexte récupéré :\n{context}\n\n"
            "Répondez en 3 à 6 puces maximum.\n"
            "Réponse :"
        )

    def _build_context(self, results: list[SearchResult]) -> str:
        if not results:
            return ""

        selected = self._context_results(results)
        context_parts: list[str] = []
        remaining = self.settings.local_llm_context_chars
        for result in selected:
            citation = f"{result.filename}, chunk {result.chunk_index + 1}"
            body = self._normalize_context(result.content)
            block = f"[{citation}]\n{body}\n"
            if len(block) > remaining:
                block = block[:remaining].rstrip()
            if not block:
                continue
            context_parts.append(block)
            remaining -= len(block)
            if remaining <= 0:
                break
        return "\n".join(context_parts)

    def _context_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Select a compact, non-duplicated set of chunks for prompting."""

        ordered = sorted(results, key=lambda result: (-result.score, result.project_id, result.chunk_index))
        selected: list[SearchResult] = []
        seen_signatures: set[str] = set()
        per_project_counts: dict[int, int] = {}
        for result in ordered:
            if per_project_counts.get(result.project_id, 0) >= 2:
                continue
            signature = self._normalize_context(result.content)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            selected.append(result)
            per_project_counts[result.project_id] = per_project_counts.get(result.project_id, 0) + 1
            if len(selected) >= 5:
                break
        selected.sort(key=lambda result: (result.project_id, result.chunk_index))
        return selected

    def _normalize_context(self, text: str) -> str:
        """Collapse redundant whitespace so repeated chunks are easier to detect."""

        return " ".join(text.split()).strip()
