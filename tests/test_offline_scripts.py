"""Tests for offline setup and readiness checks."""

from __future__ import annotations

import sys
from pathlib import Path


def test_setup_offline_creates_env_review(tmp_path: Path, monkeypatch) -> None:
    """setup_offline copies .env.review.example when missing."""

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    from scripts import setup_offline as mod

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["setup_offline.py"])
    (tmp_path / ".env.review.example").write_text("SAFRAN_MODE=review\n", encoding="utf-8")
    mod.main()
    assert (tmp_path / ".env.review").is_file()
    assert (tmp_path / "data").is_dir()

    (tmp_path / ".env.review").write_text("KEEP=1\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["setup_offline.py"])
    mod.main()
    assert "KEEP=1" in (tmp_path / ".env.review").read_text(encoding="utf-8")


def test_check_ready_fails_without_db(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from scripts import check_ready as mod

    monkeypatch.setattr(mod, "ROOT", tmp_path)
    env = tmp_path / ".env.review"
    env.write_text(
        "\n".join(
            [
                "SAFRAN_MODE=review",
                f"DB_PATH={tmp_path / 'missing.db'}",
                f"INDEX_PATH={tmp_path / 'missing.pkl'}",
                f"SYNC_MANIFEST_PATH={tmp_path / 'sync_manifest.json'}",
                "LOCAL_LLM_SERVICE_URL=",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["check_ready.py", "--env-file", str(env)])
    try:
        mod.main()
        raised = False
    except SystemExit as exc:
        raised = True
        assert exc.code == 1
    assert raised
