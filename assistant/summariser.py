"""Extractive summarisation and keyword extraction."""

from __future__ import annotations

import math
import re
from collections import Counter

from config import Settings


class Summariser:
    """Generate offline extractive summaries and metadata from text."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def summarise(self, text: str, query_keywords: list[str] | None = None) -> dict[str, object]:
        """Return bullet summary, keywords, and technologies mentioned."""

        sentences = self._sentences(text)
        if not sentences:
            return {"summary": "", "keywords": [], "technologies": []}
        tokenised = [self._tokens(sentence) for sentence in sentences]
        document_frequency = Counter(token for tokens in tokenised for token in set(tokens))
        sentence_scores: list[tuple[float, str]] = []
        query_set = set(query_keywords or [])
        for index, (sentence, tokens) in enumerate(zip(sentences, tokenised)):
            score = 0.0
            for token in tokens:
                score += math.log((1 + len(sentences)) / (1 + document_frequency[token])) + 1
                if token in query_set:
                    score += 1.0
            if index in {0, len(sentences) - 1}:
                score *= 1.15
            sentence_scores.append((score / max(1, len(tokens)), sentence))
        selected = [sentence for _, sentence in sorted(sentence_scores, reverse=True)[:5]]
        keywords = self.keywords(text)
        technologies = [term for term in self.settings.tech_terms if term.lower() in text.lower()]
        return {
            "summary": "\n".join(f"- {sentence}" for sentence in selected),
            "keywords": keywords,
            "technologies": technologies,
        }

    def summarise_with_local_llm(self, text: str) -> str:
        """Future hook for llama.cpp or ctransformers local-only abstractive summaries."""

        if not self.settings.local_llm_path:
            return ""
        raise NotImplementedError("Configure llama-cpp-python or ctransformers here for a local model path.")

    def keywords(self, text: str, limit: int = 10) -> list[str]:
        """Return high-value keywords using simple TF-style scoring."""

        counts = Counter(token for token in self._tokens(text) if len(token) >= 4)
        return [word for word, _ in counts.most_common(limit)]

    def _sentences(self, text: str) -> list[str]:
        return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]

    def _tokens(self, text: str) -> list[str]:
        return [token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]+", text)]
