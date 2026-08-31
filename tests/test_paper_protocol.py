"""Camera-ready paper_protocol keys and train-only TF-IDF helper."""

from __future__ import annotations

from eval.adversary_trial4 import train_only_tfidf_embedder
from eval.paper_protocol import paper_protocol, tfidf_params
from sbb.config import load_config, repo_root


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
