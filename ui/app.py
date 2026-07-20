"""Streamlit UI for the Safran R&D Knowledge Assistant."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from assistant.query_processor import QueryProcessor
from assistant.response_builder import ResponseBuilder
from config import Settings
from db.database import Database
from ingest.pipeline import IngestPipeline
from ingest.sync_manifest import format_manifest_caption, load_manifest
from search.hybrid_engine import HybridEngine
from search.ranker import Ranker
from search.vector_engine import VECTOR_AVAILABLE


def search(settings: Settings, query: str, top_k: int, on_chunk=None) -> dict[str, object]:
    """Run parsing, search, reranking, and response building."""

    with Database(settings.db_path) as database:
        database.init_schema()
        parsed = QueryProcessor(settings).parse(query)
        results = HybridEngine(settings, database).search(query, top_k)
        ranked = Ranker(settings).rerank(query, results)
        return ResponseBuilder(settings, database).build(query, ranked, parsed.keywords, on_chunk=on_chunk)


def render_result(result: dict[str, object]) -> None:
    """Afficher une carte d'évidence extensible."""

    title = str(result["title"])
    with st.expander(f"Preuve #{result['rank']} - {title}", expanded=int(result["rank"]) == 1):
        st.caption(f"{result['source_ref']} | Modifié : {result['date_modified'] or 'inconnu'}")
        st.progress(float(result["relevance_score"]))
        st.markdown(str(result["summary"]))
        st.write("Mots-clés")
        st.write(" ".join(f"`{kw}`" for kw in result["keywords"]))
        st.write("Technologies")
        technologies = result["technologies"] or ["aucune détectée"]
        st.write(" ".join(f"`{tech}`" for tech in technologies))
        st.code(str(result["matching_excerpt"])[:2000])
        with st.expander("Preuve complète récupérée"):
            st.write(str(result["matching_excerpt"]))


def _display_answer_provider(provider: str) -> str:
    """Return a French label for the answer provider."""

    if provider == "extractive":
        return "extractif"
    if provider.startswith("remote-llm:"):
        return "modèle local"
    return provider


def main() -> None:
    """Render the Streamlit application."""

    st.set_page_config(page_title="Assistant de connaissances Safran", layout="wide")
    settings = Settings.from_env()
    st.session_state.setdefault("queries", [])
    manifest = load_manifest(settings.sync_manifest_path) if settings.sync_manifest_path else None

    with st.sidebar:
        st.header("Assistant de connaissances Safran")
        if settings.review_mode:
            st.caption("Mode revue hors ligne — pas d'accès SharePoint.")
        else:
            st.caption("Synchro recommandée : dossier OneDrive/SharePoint local via `./sync_from_folder.sh`.")
        if not settings.review_mode and st.button("Ingérer les documents locaux"):
            with st.spinner("Ingestion des documents locaux..."):
                with Database(settings.db_path) as database:
                    database.init_schema()
                    summary = IngestPipeline(settings, database).run("local")
                st.success(f"{summary.processed} traités, {summary.skipped} ignorés, {summary.failed} échecs")
                st.info("Pour une synchro complète avec manifeste, utilisez `./sync_from_folder.sh`.")
        with Database(settings.db_path) as database:
            database.init_schema()
            stats = database.stats()
        st.metric("Projets", stats["projects"])
        st.metric("Fragments", stats["chunks"])
        st.caption(format_manifest_caption(manifest))
        st.caption(f"Dernière ingestion DB : {stats['last_ingestion'] or 'jamais'}")
        if manifest is not None:
            st.caption(f"Source : `{manifest.source_path}`")
        local_llm_service_url = getattr(settings, "local_llm_service_url", "")
        local_llm_model = getattr(settings, "local_llm_service_model", "llama3.2:3b")
        if local_llm_service_url:
            st.success(f"Ollama actif : {local_llm_model} via {local_llm_service_url}")
        else:
            st.info("Ollama n'est pas configuré ; l'application utilise des réponses extraites et justifiées.")
        top_k = st.slider("Résultats", 1, 20, settings.top_k)
        settings.use_vector_search = st.toggle("Recherche vectorielle", value=settings.use_vector_search and VECTOR_AVAILABLE, disabled=not VECTOR_AVAILABLE)
        st.subheader("Requêtes récentes")
        for index, previous in enumerate(st.session_state["queries"][-5:][::-1]):
            if st.button(previous, key=f"query-{index}-{previous}"):
                st.session_state["active_query"] = previous

    tab_search, tab_map = st.tabs(["Recherche", "Carte des connaissances"])
    with tab_search:
        query = st.text_input(
            "Revue de projets passés",
            value=st.session_state.get("active_query", ""),
            placeholder="Quels projets passés ont traité le radar FPGA ou la navigation UAV ?",
        )
        if st.button("Rechercher", type="primary") and query.strip():
            st.session_state["queries"].append(query.strip())
            with st.spinner("Recherche dans les projets indexés..."):
                answer_box = st.empty()
                streamed_chunks: list[str] = []

                def on_chunk(chunk: str) -> None:
                    streamed_chunks.append(chunk)
                    answer_box.markdown("".join(streamed_chunks))

                response = search(settings, query.strip(), top_k, on_chunk=on_chunk)
            if response["total_results"] == 0:
                st.info("Aucun résultat trouvé. Essayez des termes techniques plus larges, des acronymes de projet ou des filtres de date.")
            else:
                st.subheader("Réponse")
                if not streamed_chunks:
                    answer_box.markdown(str(response["answer"]))
                else:
                    answer_box.markdown("".join(streamed_chunks) or str(response["answer"]))
                confidence = str(response["confidence"]).title()
                provider = _display_answer_provider(str(response["answer_provider"]))
                st.caption(f"Confiance : {confidence} | Mode de réponse : {provider}")
                st.info(str(response["limitations"]))
                st.subheader("Sources")
                for source in response["sources"]:
                    chunks = ", ".join(str(chunk) for chunk in source["chunks"])
                    st.write(f"- **{source['title']}** (`{source['filename']}`), fragments : {chunks}")
                st.subheader("Preuves")
                for result in response["results"]:
                    render_result(result)
                st.warning(str(response["gap_analysis"]))

    with tab_map:
        with Database(settings.db_path) as database:
            database.init_schema()
            rows = database.fetchall(
                "SELECT keyword, COUNT(*) AS count FROM keywords GROUP BY keyword ORDER BY count DESC LIMIT 20"
            )
        if rows:
            st.bar_chart({row["keyword"]: row["count"] for row in rows})
        else:
            st.info("Aucun mot-clé n'a encore été indexé.")


if __name__ == "__main__":
    main()
