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
from search.hybrid_engine import HybridEngine
from search.ranker import Ranker
from search.vector_engine import VECTOR_AVAILABLE


def search(settings: Settings, query: str, top_k: int) -> dict[str, object]:
    """Run parsing, search, reranking, and response building."""

    with Database(settings.db_path) as database:
        database.init_schema()
        parsed = QueryProcessor(settings).parse(query)
        results = HybridEngine(settings, database).search(query, top_k)
        ranked = Ranker(settings).rerank(query, results)
        return ResponseBuilder(settings, database).build(query, ranked, parsed.keywords)


def render_result(result: dict[str, object]) -> None:
    """Render one expandable evidence card."""

    title = str(result["title"])
    with st.expander(f"Evidence #{result['rank']} - {title}", expanded=int(result["rank"]) == 1):
        st.caption(f"{result['source_ref']} | Modified: {result['date_modified'] or 'unknown'}")
        st.progress(float(result["relevance_score"]))
        st.markdown(str(result["summary"]))
        st.write("Keywords")
        st.write(" ".join(f"`{kw}`" for kw in result["keywords"]))
        st.write("Technologies")
        technologies = result["technologies"] or ["none detected"]
        st.write(" ".join(f"`{tech}`" for tech in technologies))
        st.code(str(result["matching_excerpt"])[:2000])
        with st.expander("Full Retrieved Evidence"):
            st.write(str(result["matching_excerpt"]))


def main() -> None:
    """Render the Streamlit application."""

    st.set_page_config(page_title="Safran R&D Knowledge Assistant", layout="wide")
    settings = Settings.from_env()
    st.session_state.setdefault("queries", [])

    with st.sidebar:
        st.header("Safran R&D Knowledge Assistant")
        if st.button("Ingest Local Documents"):
            with st.spinner("Ingesting local documents..."):
                with Database(settings.db_path) as database:
                    database.init_schema()
                    summary = IngestPipeline(settings, database).run("local")
                st.success(f"{summary.processed} processed, {summary.skipped} skipped, {summary.failed} failed")
        with Database(settings.db_path) as database:
            database.init_schema()
            stats = database.stats()
        st.metric("Projects", stats["projects"])
        st.metric("Chunks", stats["chunks"])
        st.caption(f"Last ingestion: {stats['last_ingestion'] or 'never'}")
        if settings.local_llm_path and settings.local_llm_path.exists():
            st.success(f"Local LLM enabled: {settings.local_llm_backend}")
        else:
            st.info("Local LLM disabled; using extractive grounded answers.")
        top_k = st.slider("Results", 1, 20, settings.top_k)
        settings.use_vector_search = st.toggle("Vector search", value=settings.use_vector_search and VECTOR_AVAILABLE, disabled=not VECTOR_AVAILABLE)
        st.subheader("Recent Queries")
        for previous in st.session_state["queries"][-5:][::-1]:
            if st.button(previous, key=f"query-{previous}"):
                st.session_state["active_query"] = previous

    tab_search, tab_map = st.tabs(["Search", "Knowledge Map"])
    with tab_search:
        query = st.text_input("Search", value=st.session_state.get("active_query", ""), placeholder="Find previous radar FPGA or UAV navigation projects")
        if st.button("Search", type="primary") and query.strip():
            st.session_state["queries"].append(query.strip())
            with st.spinner("Searching indexed projects..."):
                response = search(settings, query.strip(), top_k)
            if response["total_results"] == 0:
                st.info("No results found. Try broader technology names, project acronyms, or date filters.")
            else:
                st.subheader("Answer")
                st.markdown(str(response["answer"]))
                confidence = str(response["confidence"]).title()
                st.caption(f"Confidence: {confidence} | Answer mode: {response['answer_provider']}")
                st.info(str(response["limitations"]))
                st.subheader("Sources")
                for source in response["sources"]:
                    chunks = ", ".join(str(chunk) for chunk in source["chunks"])
                    st.write(f"- **{source['title']}** (`{source['filename']}`), chunks: {chunks}")
                st.subheader("Evidence")
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
            st.info("No keywords indexed yet.")


if __name__ == "__main__":
    main()
