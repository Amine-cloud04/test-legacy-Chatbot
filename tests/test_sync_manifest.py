"""Tests for sync manifest persistence used by offline review mode."""

from __future__ import annotations

from pathlib import Path

from ingest.sync_manifest import (
    SyncManifest,
    default_manifest_path,
    format_manifest_caption,
    load_manifest,
    write_manifest,
)


def test_write_and_load_manifest(tmp_path: Path) -> None:
    path = tmp_path / "sync_manifest.json"
    manifest = SyncManifest.create(
        source_path=tmp_path / "docs",
        mode="local_folder",
        processed=3,
        skipped=1,
        failed=0,
        projects=2,
        chunks=10,
    )
    write_manifest(path, manifest)
    loaded = load_manifest(path)
    assert loaded is not None
    assert loaded.mode == "local_folder"
    assert loaded.processed == 3
    assert loaded.projects == 2
    assert loaded.source_path.endswith("docs")


def test_load_missing_manifest(tmp_path: Path) -> None:
    assert load_manifest(tmp_path / "missing.json") is None


def test_format_caption_never() -> None:
    assert "jamais" in format_manifest_caption(None)


def test_default_manifest_path(tmp_path: Path) -> None:
    db = tmp_path / "knowledge_base.db"
    assert default_manifest_path(db) == tmp_path / "sync_manifest.json"
