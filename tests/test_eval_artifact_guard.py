"""Guards against accidental writes into committed CIKM artifacts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from eval.artifact_guard import is_committed_artifact_path, refuse_committed_write
from sbb.config import repo_root


def _load_runner(name: str):
    path = repo_root() / "eval" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_committed_prefixes_do_not_match_historical_side_dirs(tmp_path: Path) -> None:
    root = repo_root()
    assert is_committed_artifact_path(root, root / "outputs" / "pilot_v2" / "analytics_metrics.json")
    assert is_committed_artifact_path(root, root / "outputs" / "pilot_v2_camera_ready")
    assert is_committed_artifact_path(root, root / "releases" / "cikm-2026" / "checksums.sha256")
    assert not is_committed_artifact_path(
        root, root / "outputs" / "pilot_v2_tfidf_train_only" / "metrics.json"
    )
    assert not is_committed_artifact_path(root, tmp_path / "analytics_metrics.json")
    assert refuse_committed_write(
        root, root / "outputs" / "pilot_v2" / "metrics.json", force=False
    )
    assert refuse_committed_write(
        root, root / "outputs" / "pilot_v2" / "metrics.json", force=True
    ) is None


def test_run_cohort_tier1_refuses_committed_default() -> None:
    mod = _load_runner("run_cohort_tier1.py")
    assert mod.main([]) == 2


def test_run_cohort_tier1_missing_noncommitted_output_is_not_a_force_block(
    tmp_path: Path,
) -> None:
    mod = _load_runner("run_cohort_tier1.py")
    missing = tmp_path / "analytics_metrics.json"
    assert mod.main(["--output", str(missing)]) == 1


def test_promote_camera_ready_refuses_committed_default() -> None:
    mod = _load_runner("promote_camera_ready_tfidf_train_only.py")
    assert mod.main([]) == 2


def test_run_obs_study_linkage_refuses_transductive_pilot_v2() -> None:
    """Historical study runner must not overwrite committed transductive Trial4 scores."""
    mod = _load_runner("run_obs_study.py")
    assert mod.main(["--tier", "linkage"]) == 2
