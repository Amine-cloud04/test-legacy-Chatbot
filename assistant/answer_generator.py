"""Offline answer generation from retrieved evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from config import Settings
from db.models import SearchResult
from assistant.local_llm import LocalLLM


@dataclass(slots=True)
class GeneratedAnswer:
    """A grounded answer assembled from retrieved chunks."""

    answer: str
    confidence: str
    limitations: str
    provider: str


class AnswerGenerator:
    """Generate a user-facing answer without external APIs.

    This class intentionally avoids unsupported claims. It extracts the strongest
    evidence sentences from retrieved chunks, cites them, and reports uncertainty
    when evidence is thin. A local LLM can replace this class later while keeping
    the same response contract.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.local_llm = LocalLLM(settings)

    def generate(self, query: str, results: list[SearchResult], query_keywords: list[str]) -> GeneratedAnswer:
        """Generate a concise grounded answer from retrieved search results."""

        if not results:
            return GeneratedAnswer(
                answer="Je n'ai pas trouvé d'éléments indexés permettant de répondre à cette question.",
                confidence="low",
                limitations="Aucun fragment correspondant n'a été récupéré dans la base de connaissances actuelle.",
                provider="extractive",
            )

        evidence = self._top_evidence(results, query_keywords)
        if not evidence:
            return GeneratedAnswer(
                answer="J'ai trouvé des documents liés, mais le texte récupéré ne contient pas assez d'éléments clairs pour répondre directement.",
                confidence="low",
                limitations="Le jeu de résultats contient uniquement des correspondances faibles ou indirectes.",
                provider="extractive",
            )

        llm_result = self.local_llm.generate(query, results)
        if llm_result and llm_result.text:
            answer = llm_result.text
            if "[" not in answer:
                answer = f"{answer}\n\nSources used: {self._source_line(results)}."
            return GeneratedAnswer(
                answer=answer,
                confidence=self._confidence(results, evidence, query_keywords),
                limitations=self._limitations(query, results, query_keywords),
                provider=llm_result.provider,
            )

        lines = ["D'après les documents indexés, les éléments de preuve les plus solides sont :"]
        for sentence, result in evidence[:4]:
            lines.append(f"- {sentence} [{self._citation(result)}]")

        project_names = []
        for result in results:
            if result.title not in project_names:
                project_names.append(result.title)
        if project_names:
            lines.append(f"\nProjets les plus pertinents : {', '.join(project_names[:5])}.")

        return GeneratedAnswer(
            answer="\n".join(lines),
            confidence=self._confidence(results, evidence, query_keywords),
            limitations=self._limitations(query, results, query_keywords),
            provider="extractive",
        )

    def _top_evidence(
        self,
        results: list[SearchResult],
        query_keywords: list[str],
    ) -> list[tuple[str, SearchResult]]:
        scored: list[tuple[float, str, SearchResult]] = []
        keyword_set = {keyword.lower() for keyword in query_keywords}
        for result_rank, result in enumerate(results, start=1):
            for sentence in self._sentences(result.content):
                tokens = set(self._tokens(sentence))
                overlap = len(tokens & keyword_set)
                if keyword_set and overlap == 0:
                    continue
                score = overlap * 2.0 + result.score + (1.0 / result_rank)
                scored.append((score, sentence, result))
        unique: list[tuple[str, SearchResult]] = []
        seen: set[str] = set()
        for _, sentence, result in sorted(scored, key=lambda item: item[0], reverse=True):
            key = sentence.lower()
            if key not in seen:
                unique.append((sentence, result))
                seen.add(key)
        return unique

    def _confidence(
        self,
        results: list[SearchResult],
        evidence: list[tuple[str, SearchResult]],
        query_keywords: list[str],
    ) -> str:
        covered_keywords = set()
        for sentence, _ in evidence:
            covered_keywords.update(set(self._tokens(sentence)) & {keyword.lower() for keyword in query_keywords})
        coverage = len(covered_keywords) / max(1, len(set(query_keywords)))
        distinct_projects = len({result.project_id for result in results})
        if coverage >= 0.6 and distinct_projects >= 2:
            return "high"
        if coverage >= 0.35 or evidence:
            return "medium"
        return "low"

    def _limitations(self, query: str, results: list[SearchResult], query_keywords: list[str]) -> str:
        if len(results) < 3:
            return "La réponse repose sur un petit nombre de fragments récupérés ; vérifiez les documents cités avant de prendre une décision de projet."
        missing = [
            keyword
            for keyword in query_keywords
            if not any(keyword.lower() in result.content.lower() for result in results)
        ]
        if missing:
            return f"Les éléments récupérés ne couvrent pas clairement : {', '.join(missing)}."
        return "La réponse est extractive et fondée sur des fragments récupérés ; elle n'infère pas d'information absente des documents."

    def _citation(self, result: SearchResult) -> str:
        return f"{result.filename}, chunk {result.chunk_index + 1}"

    def _source_line(self, results: list[SearchResult]) -> str:
        citations: list[str] = []
        for result in results[:3]:
            citation = self._citation(result)
            if citation not in citations:
                citations.append(citation)
        return "; ".join(f"[{citation}]" for citation in citations)

    def _sentences(self, text: str) -> list[str]:
        normalised = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", normalised)
        return [sentence.strip() for sentence in sentences if 25 <= len(sentence.strip()) <= 350]

    def _tokens(self, text: str) -> list[str]:
        return [token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]+", text)]
