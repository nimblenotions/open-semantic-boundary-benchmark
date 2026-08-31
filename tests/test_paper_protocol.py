"""CIKM 2026 protocol keys, frozen cite-surface checks, and train-only TF-IDF helper."""

from __future__ import annotations

from eval.adversary_trial4 import train_only_tfidf_embedder
from eval.paper_protocol import paper_protocol, tfidf_params
from sbb.config import load_config, repo_root

TABLE3_AT_045 = {
    "T_o-1": "bracket (0.67)",
    "T_a-1": "surrogate (0.45)",
    "T_a-2": "coarse (1.00)",
    "T_a-3": "coarse (1.00)",
    "T_a-5": "surrogate (0.26)",
}
PUBLISHED_GRID = (
    repo_root()
    / "outputs"
    / "post_acceptance_experiments"
    / "ta5_cohort_audit"
    / "snapshot_track_c"
    / "table3_operative_grid.md"
)


def _makefile_recipe(text: str, target: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{target}:"))
    body: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("\t"):
            body.append(line)
            continue
        if not line.strip():
            continue
        break
    return "\n".join(body)


def test_paper_protocol_yaml_locks_camera_ready_choices() -> None:
    cfg = load_config()
    proto = paper_protocol(cfg)
    assert proto["linkage"]["fit"] == "train_only"
    assert proto["linkage"]["risk_surface"] == "purpose_specific"
    assert proto["ta5_cohort"]["primary"] == "track_c_assessor_symmetric"
    params = tfidf_params(cfg)
    assert params["analyzer"] == "char_wb"
    assert params["ngram_range"] == (1, 3)
    assert params["max_features"] == 5000
    root = repo_root()
    assert (root / proto["ta5_cohort"]["scores"]).is_file()
    assert (root / proto["purpose_specific_linkage"]["outputs"] / "REPORT.md").is_file()


def test_train_only_tfidf_does_not_expand_vocab_on_held_out() -> None:
    train_rows = [
        {
            "export": {
                "condition_id": "raw",
                "z": {"journal_text": "alpha alpha alpha", "assistant_text": "ok"},
            }
        }
    ]
    embedder = train_only_tfidf_embedder(
        train_rows,
        max_features=5000,
        ngram_range=(1, 3),
        analyzer="char_wb",
    )
    n_vocab = len(embedder._vectorizer.get_feature_names_out())
    vecs = embedder.embed(["zzzz unique held-out token qqqq"])
    assert vecs.shape[0] == 1
    assert len(embedder._vectorizer.get_feature_names_out()) == n_vocab


def test_repro_cikm_2026_does_not_invoke_eval_runners() -> None:
    root = repo_root()
    recipe = _makefile_recipe(
        (root / "Makefile").read_text(encoding="utf-8"),
        "repro-cikm-2026",
    )
    assert "eval/run_" not in recipe
    assert "scripts/repro_cikm_2026.py" in recipe
    assert "tests/test_paper_protocol.py" in recipe
    repro = (root / "scripts" / "repro_cikm_2026.py").read_text(encoding="utf-8")
    assert "eval/run_" not in repro


def test_published_table3_focal_and_purpose_specific_ta1() -> None:
    md = PUBLISHED_GRID.read_text(encoding="utf-8")
    assert "## Published CIKM 2026 operative grid" in md
    assert (
        "| 0.45 | bracket (0.67) | surrogate (0.45) | coarse (1.00) | "
        "coarse (1.00) | surrogate (0.26) |"
    ) in md
    assert (
        "| 0.50 | medium (1.00) | raw (0.55) | coarse (1.00) | "
        "coarse (1.00) | surrogate (0.26) |"
    ) in md
    assert (
        "| 0.55 | medium (1.00) | raw (0.55) | coarse (1.00) | "
        "coarse (1.00) | surrogate (0.26) |"
    ) in md
    cite = (
        repo_root() / "releases" / "cikm-2026" / "experimental_protocol.md"
    ).read_text(encoding="utf-8")
    for cell in TABLE3_AT_045.values():
        assert cell in cite


def test_red_tokenize_near_zero_recovery_high_persona() -> None:
    import json

    camera = json.loads(
        (
            repo_root()
            / "outputs"
            / "pilot_v2_camera_ready"
            / "CAMERA_READY_PROTOCOL.json"
        ).read_text(encoding="utf-8")
    )
    tok = camera["verification"]["red_tokenize"]
    assert float(tok["token_recovery_rate"]) < 0.01
    assert float(tok["persona_top1"]) >= 0.80
    assert tok["near_zero_token_high_persona"] is True


def test_release_figure_checksums() -> None:
    import hashlib

    root = repo_root()
    mapping: dict[str, str] = {}
    for raw in (root / "releases" / "cikm-2026" / "checksums.sha256").read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        mapping[rel.strip()] = digest.lower()
    expected = [
        "releases/cikm-2026/figures/linkage_decomposition.pdf",
        "releases/cikm-2026/figures/utility_matrix_heatmap.pdf",
        "releases/cikm-2026/figures/cross_purpose_regret_matrix.pdf",
    ]
    for rel in expected:
        h = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        assert h == mapping[rel]
