"""Linkage adversary: persona match, attribute inference, longitudinal linkage.

Filename ``adversary_trial4`` is historical. Combined R is the unweighted
mean of persona top-1, attribute macro-F1, and longitudinal AUC. Token recovery
is scored separately.

Default ``tfidf_fit_scope`` is ``train_only`` (published protocol).
``train_test`` is the superseded transductive fit, retained for audit only.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score

from eval.adversary import token_recovery_rate
from eval.embeddings import DEFAULT_MODEL, Embedder, SentenceTransformerEmbedder
from eval.export_text import export_text_for_embedding

DEFAULT_SIMILARITY_THRESHOLD = 0.3
MAX_LINKAGE_PAIRS = 4000
TFIDF_FIT_TRAIN_TEST = "train_test"
TFIDF_FIT_TRAIN_ONLY = "train_only"
DEFAULT_TFIDF_FIT_SCOPE = TFIDF_FIT_TRAIN_ONLY
TFIDF_ANALYZER = "char_wb"
TFIDF_NGRAM_RANGE = (1, 3)
TFIDF_MAX_FEATURES = 5000


class _FittedTfidfEmbedder:
    """Char n-gram TF-IDF dense vectors (frozen SBB linkage probe)."""

    def __init__(
        self,
        *,
        max_features: int = TFIDF_MAX_FEATURES,
        ngram_range: tuple[int, int] = TFIDF_NGRAM_RANGE,
        analyzer: str = TFIDF_ANALYZER,
    ) -> None:
        self._vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            analyzer=analyzer,
            min_df=1,
        )
        self.model_name = "tfidf_char_wb"
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.analyzer = analyzer

    def fit(self, texts: list[str]) -> None:
        self._vectorizer.fit(texts)

    @property
    def vocab_size(self) -> int:
        vocab = getattr(self._vectorizer, "vocabulary_", None)
        return len(vocab) if vocab is not None else 0

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = self._vectorizer.transform(texts)
        dense = matrix.toarray().astype(np.float64)
        for i in range(len(dense)):
            norm = np.linalg.norm(dense[i])
            if norm > 0:
                dense[i] /= norm
        return dense


def tfidf_fit_scope_from_config(cfg: dict[str, Any] | None) -> str:
    """Read eval.trial4.tfidf_fit_scope; default is camera-ready train-only fitting."""
    if not cfg:
        return DEFAULT_TFIDF_FIT_SCOPE
    trial4 = (cfg.get("eval") or {}).get("trial4") or {}
    scope = str(trial4.get("tfidf_fit_scope", DEFAULT_TFIDF_FIT_SCOPE)).strip()
    return scope or DEFAULT_TFIDF_FIT_SCOPE


def tfidf_fit_texts(
    train_texts: list[str],
    test_texts: list[str],
    tfidf_fit_scope: str = DEFAULT_TFIDF_FIT_SCOPE,
) -> list[str]:
    """Select documents used to fit the frozen TF-IDF vectorizer."""
    scope = (tfidf_fit_scope or DEFAULT_TFIDF_FIT_SCOPE).strip()
    if scope == TFIDF_FIT_TRAIN_ONLY:
        return list(train_texts)
    if scope == TFIDF_FIT_TRAIN_TEST:
        return list(train_texts) + list(test_texts)
    raise ValueError(
        f"tfidf_fit_scope must be {TFIDF_FIT_TRAIN_TEST!r} or "
        f"{TFIDF_FIT_TRAIN_ONLY!r}, got {tfidf_fit_scope!r}"
    )


def fit_trial4_tfidf_embedder(
    train_texts: list[str],
    test_texts: list[str],
    *,
    tfidf_fit_scope: str = DEFAULT_TFIDF_FIT_SCOPE,
) -> tuple[_FittedTfidfEmbedder, dict[str, Any]]:
    """Fit the frozen char_wb TF-IDF probe and return embedder plus fit metadata."""
    fit_texts = tfidf_fit_texts(train_texts, test_texts, tfidf_fit_scope)
    embedder = _FittedTfidfEmbedder()
    embedder.fit(fit_texts)
    meta = {
        "tfidf_fit_scope": tfidf_fit_scope,
        "tfidf_n_fit_docs": len(fit_texts),
        "tfidf_vocab_size": embedder.vocab_size,
        "tfidf_analyzer": TFIDF_ANALYZER,
        "tfidf_ngram_range": list(TFIDF_NGRAM_RANGE),
        "tfidf_max_features": TFIDF_MAX_FEATURES,
    }
    return embedder, meta


def resolve_embedder(
    embedder: Embedder | None,
    *,
    fit_texts: list[str] | None = None,
) -> Embedder:
    """Return embedder: caller-supplied, MiniLM, or TF-IDF fallback."""
    if embedder is not None:
        return embedder
    try:
        return SentenceTransformerEmbedder(DEFAULT_MODEL)
    except ImportError:
        tfidf = _FittedTfidfEmbedder()
        if fit_texts:
            tfidf.fit(fit_texts)
        return tfidf


def _export_texts(rows: list[dict[str, Any]]) -> list[str]:
    return [export_text_for_embedding(row["export"]) for row in rows]


def train_only_tfidf_embedder(
    train_rows: list[dict[str, Any]],
    *,
    max_features: int = TFIDF_MAX_FEATURES,
    ngram_range: tuple[int, int] = TFIDF_NGRAM_RANGE,
    analyzer: str = TFIDF_ANALYZER,
) -> _FittedTfidfEmbedder:
    """Fit Trial4 TF-IDF on training export strings only (paper protocol)."""
    embedder = _FittedTfidfEmbedder(
        max_features=max_features,
        ngram_range=ngram_range,
        analyzer=analyzer,
    )
    embedder.fit(_export_texts(train_rows))
    return embedder


def _mean_pool(vectors: np.ndarray) -> np.ndarray:
    if len(vectors) == 0:
        return np.zeros(vectors.shape[1] if vectors.ndim == 2 else 1, dtype=np.float64)
    mean = np.mean(vectors, axis=0)
    norm = np.linalg.norm(mean)
    return mean / norm if norm > 0 else mean


def _cosine_rows(query: np.ndarray, profiles: np.ndarray) -> np.ndarray:
    """Cosine similarity between one query vector and each profile row."""
    q_norm = np.linalg.norm(query)
    if q_norm == 0:
        return np.zeros(len(profiles), dtype=np.float64)
    p_norms = np.linalg.norm(profiles, axis=1)
    dots = profiles @ query
    denom = p_norms * q_norm
    with np.errstate(divide="ignore", invalid="ignore"):
        sims = np.where(denom > 0, dots / denom, 0.0)
    return sims


def _build_persona_profiles(
    rows: list[dict[str, Any]],
    embeddings: np.ndarray,
) -> tuple[list[str], np.ndarray]:
    persona_ids = sorted({r["persona_id"] for r in rows})
    profiles: list[np.ndarray] = []
    for pid in persona_ids:
        idx = [i for i, r in enumerate(rows) if r["persona_id"] == pid]
        profiles.append(_mean_pool(embeddings[idx]))
    return persona_ids, np.vstack(profiles)


def _persona_inference(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    embeddings_train: np.ndarray,
    embeddings_test: np.ndarray,
    *,
    similarity_threshold: float,
) -> dict[str, float | str]:
    """Persona match: train-pool when personas overlap, else test LOO (persona holdout split)."""
    if not test_rows:
        return {
            "persona_top1": 0.0,
            "persona_top5": 0.0,
            "candidate_set_size_mean": 0.0,
            "random_baseline_top1": 0.0,
            "n_test_personas": 0,
            "persona_inference_mode": "none",
        }

    train_persona_ids = {r["persona_id"] for r in train_rows}
    test_persona_ids = sorted({r["persona_id"] for r in test_rows})
    random_baseline = 1.0 / len(test_persona_ids) if test_persona_ids else 0.0
    overlap = train_persona_ids & set(test_persona_ids)

    if overlap:
        return _persona_inference_train_pool(
            train_rows,
            test_rows,
            embeddings_train,
            embeddings_test,
            similarity_threshold=similarity_threshold,
            random_baseline=random_baseline,
            n_test_personas=len(test_persona_ids),
            mode="train_pool_overlap",
        )

    return _persona_inference_test_loo(
        test_rows,
        embeddings_test,
        similarity_threshold=similarity_threshold,
        random_baseline=random_baseline,
        n_test_personas=len(test_persona_ids),
    )


def _persona_inference_train_pool(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    embeddings_train: np.ndarray,
    embeddings_test: np.ndarray,
    *,
    similarity_threshold: float,
    random_baseline: float,
    n_test_personas: int,
    mode: str,
) -> dict[str, float | str]:
    train_personas, train_profiles = _build_persona_profiles(train_rows, embeddings_train)
    eval_rows = [r for r in test_rows if r["persona_id"] in set(train_personas)]
    if not eval_rows or not train_personas:
        return {
            "persona_top1": 0.0,
            "persona_top5": 0.0,
            "candidate_set_size_mean": 0.0,
            "random_baseline_top1": random_baseline,
            "n_test_personas": n_test_personas,
            "persona_inference_mode": mode,
        }

    top1_hits = 0
    top5_hits = 0
    candidate_sizes: list[float] = []
    test_index = {r["event_id"]: i for i, r in enumerate(test_rows)}

    for row in eval_rows:
        i = test_index[row["event_id"]]
        sims = _cosine_rows(embeddings_test[i], train_profiles)
        ranked_idx = np.argsort(-sims)
        pred_top1 = train_personas[int(ranked_idx[0])]
        top5_personas = {train_personas[int(j)] for j in ranked_idx[:5]}
        if pred_top1 == row["persona_id"]:
            top1_hits += 1
        if row["persona_id"] in top5_personas:
            top5_hits += 1
        candidate_sizes.append(float(np.sum(sims >= similarity_threshold)))

    n = len(eval_rows)
    return {
        "persona_top1": top1_hits / n,
        "persona_top5": top5_hits / n,
        "candidate_set_size_mean": float(np.mean(candidate_sizes)),
        "random_baseline_top1": random_baseline,
        "n_test_personas": n_test_personas,
        "persona_inference_mode": mode,
    }


def _persona_inference_test_loo(
    test_rows: list[dict[str, Any]],
    embeddings_test: np.ndarray,
    *,
    similarity_threshold: float,
    random_baseline: float,
    n_test_personas: int,
) -> dict[str, float | str]:
    """Leave-one-out match among test personas (disjoint persona holdout split)."""
    by_persona: dict[str, list[int]] = {}
    for i, row in enumerate(test_rows):
        by_persona.setdefault(row["persona_id"], []).append(i)

    top1_hits = 0
    top5_hits = 0
    candidate_sizes: list[float] = []
    total = 0

    for pid, indices in by_persona.items():
        profile_personas: list[str] = []
        profile_vecs: list[np.ndarray] = []
        for opid, oidx in by_persona.items():
            profile_personas.append(opid)
            if opid == pid and len(indices) > 1:
                # LOO: persona profile excludes held-out event(s) per iteration below
                profile_vecs.append(_mean_pool(embeddings_test[oidx]))
            else:
                profile_vecs.append(_mean_pool(embeddings_test[oidx]))

        if len(indices) == 1:
            hold_idx = indices[0]
            other_profiles = []
            other_personas = []
            for opid, oidx in by_persona.items():
                if opid == pid:
                    continue
                other_profiles.append(_mean_pool(embeddings_test[oidx]))
                other_personas.append(opid)
            if not other_profiles:
                continue
            sims = _cosine_rows(embeddings_test[hold_idx], np.vstack(other_profiles))
            ranked_idx = np.argsort(-sims)
            pred = other_personas[int(ranked_idx[0])]
            top5 = {other_personas[int(j)] for j in ranked_idx[:min(5, len(other_personas))]}
            if pred == pid:
                top1_hits += 1
            if pid in top5:
                top5_hits += 1
            candidate_sizes.append(float(np.sum(sims >= similarity_threshold)))
            total += 1
            continue

        for hold_idx in indices:
            others = [k for k in indices if k != hold_idx]
            loo_profiles = []
            for opid, oidx in by_persona.items():
                pool = others if opid == pid else oidx
                loo_profiles.append(_mean_pool(embeddings_test[pool]))
            loo_matrix = np.vstack(loo_profiles)
            sims = _cosine_rows(embeddings_test[hold_idx], loo_matrix)
            ranked_idx = np.argsort(-sims)
            pred = profile_personas[int(ranked_idx[0])]
            top5 = {profile_personas[int(j)] for j in ranked_idx[:5]}
            if pred == pid:
                top1_hits += 1
            if pid in top5:
                top5_hits += 1
            candidate_sizes.append(float(np.sum(sims >= similarity_threshold)))
            total += 1

    n = total or 1
    return {
        "persona_top1": top1_hits / n,
        "persona_top5": top5_hits / n,
        "candidate_set_size_mean": float(np.mean(candidate_sizes)) if candidate_sizes else 0.0,
        "random_baseline_top1": random_baseline,
        "n_test_personas": n_test_personas,
        "persona_inference_mode": "test_loo_disjoint",
    }


def _attribute_label(row: dict[str, Any], attr: str, persona_table: dict[str, dict]) -> str:
    label = row["label"]
    if attr == "quasi_id_rarity":
        persona = persona_table.get(row["persona_id"], {})
        return str(persona.get("quasi_id_rarity", "unknown"))
    if attr == "symptom_categories":
        cats = label.get("symptom_categories") or []
        if not cats:
            return "none"
        return str(sorted(cats)[0])
    return str(label.get(attr, "unknown"))


def _fit_predict_embedding_classifier(
    train_x: np.ndarray,
    train_y: list[str],
    test_x: np.ndarray,
    *,
    seed: int,
) -> list[str]:
    classes = sorted(set(train_y))
    if len(classes) < 2:
        clf = DummyClassifier(strategy="most_frequent")
        clf.fit(train_x, train_y)
        return list(clf.predict(test_x))

    clf = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=seed,
    )
    clf.fit(train_x, train_y)
    return list(clf.predict(test_x))


def _attribute_inference(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    embeddings_train: np.ndarray,
    embeddings_test: np.ndarray,
    persona_table: dict[str, dict[str, Any]],
    *,
    seed: int,
) -> dict[str, float]:
    attributes = [
        "medication_class",
        "occupation_sector",
        "symptom_categories",
        "quasi_id_rarity",
    ]
    if not test_rows:
        return {f"{a}_macro_f1": 0.0 for a in attributes} | {
            "attribute_combined_macro_f1": 0.0,
            "time_bucket_macro_f1": 0.0,
        }

    f1_scores: list[float] = []
    results: dict[str, float] = {}
    for attr in attributes:
        train_y = [_attribute_label(r, attr, persona_table) for r in train_rows]
        test_y = [_attribute_label(r, attr, persona_table) for r in test_rows]
        pred = _fit_predict_embedding_classifier(
            embeddings_train, train_y, embeddings_test, seed=seed
        )
        score = float(f1_score(test_y, pred, average="macro", zero_division=0))
        results[f"{attr}_macro_f1"] = score
        f1_scores.append(score)

    # Temporal leakage: predict time_bucket from export embedding
    train_tb = [str(r["label"].get("time_bucket", "unknown")) for r in train_rows]
    test_tb = [str(r["label"].get("time_bucket", "unknown")) for r in test_rows]
    pred_tb = _fit_predict_embedding_classifier(
        embeddings_train, train_tb, embeddings_test, seed=seed
    )
    tb_f1 = float(f1_score(test_tb, pred_tb, average="macro", zero_division=0))
    results["time_bucket_macro_f1"] = tb_f1

    results["attribute_combined_macro_f1"] = (
        float(np.mean(f1_scores)) if f1_scores else 0.0
    )
    return results


def _longitudinal_loo_top1(
    test_rows: list[dict[str, Any]],
    embeddings_test: np.ndarray,
) -> float:
    """Leave-one-event-out sequence match among test personas (longitudinal linkage)."""
    by_persona: dict[str, list[int]] = {}
    for i, row in enumerate(test_rows):
        by_persona.setdefault(row["persona_id"], []).append(i)

    hits = 0
    total = 0
    for pid, indices in by_persona.items():
        if len(indices) < 2:
            continue
        other_profiles = []
        other_ids = []
        for opid, oidx in by_persona.items():
            if opid == pid:
                continue
            other_profiles.append(_mean_pool(embeddings_test[oidx]))
            other_ids.append(opid)
        if not other_profiles:
            continue
        other_matrix = np.vstack(other_profiles)
        for hold_idx in indices:
            others = [k for k in indices if k != hold_idx]
            seq_profile = _mean_pool(embeddings_test[others])
            all_profiles = np.vstack([seq_profile.reshape(1, -1), other_matrix])
            all_ids = [pid, *other_ids]
            sims = _cosine_rows(embeddings_test[hold_idx], all_profiles)
            pred = all_ids[int(np.argmax(sims))]
            if pred == pid:
                hits += 1
            total += 1
    return hits / total if total else 0.0


def _longitudinal_linkage_auc(
    test_rows: list[dict[str, Any]],
    embeddings_test: np.ndarray,
    *,
    seed: int,
    max_pairs: int = MAX_LINKAGE_PAIRS,
) -> dict[str, float]:
    """Pairwise same-persona vs different-persona discrimination via cosine similarity."""
    if len(test_rows) < 2:
        return {"longitudinal_linkage_auc": 0.5, "n_linkage_pairs": 0}

    by_persona: dict[str, list[int]] = {}
    for i, row in enumerate(test_rows):
        by_persona.setdefault(row["persona_id"], []).append(i)

    rng = np.random.default_rng(seed)
    positive_pairs: list[tuple[int, int]] = []
    for indices in by_persona.values():
        if len(indices) < 2:
            continue
        for _ in range(min(len(indices) * 2, 50)):
            a, b = rng.choice(indices, size=2, replace=False)
            positive_pairs.append((int(a), int(b)))

    negative_pairs: list[tuple[int, int]] = []
    all_indices = list(range(len(test_rows)))
    target_neg = max(len(positive_pairs), 1)
    attempts = 0
    while len(negative_pairs) < target_neg and attempts < target_neg * 20:
        attempts += 1
        i, j = rng.choice(all_indices, size=2, replace=False)
        if test_rows[int(i)]["persona_id"] != test_rows[int(j)]["persona_id"]:
            negative_pairs.append((int(i), int(j)))

    pairs = positive_pairs + negative_pairs
    if len(pairs) > max_pairs:
        rng.shuffle(pairs)
        pairs = pairs[:max_pairs]

    if not pairs:
        return {"longitudinal_linkage_auc": 0.5, "n_linkage_pairs": 0}

    labels: list[int] = []
    scores: list[float] = []
    for i, j in pairs:
        same = test_rows[i]["persona_id"] == test_rows[j]["persona_id"]
        labels.append(1 if same else 0)
        scores.append(float(_cosine_rows(embeddings_test[i], embeddings_test[j : j + 1])[0]))

    auc = 0.5
    if len(set(labels)) >= 2:
        auc = float(roc_auc_score(labels, scores))

    return {
        "longitudinal_linkage_auc": auc,
        "n_linkage_pairs": len(pairs),
    }


def combined_linkage_score(metrics: dict[str, float]) -> float:
    """Pareto x-axis: mean of persona top-1, combined attribute F1, linkage AUC."""
    parts = [
        metrics.get("persona_top1", 0.0),
        metrics.get("attribute_combined_macro_f1", 0.0),
        metrics.get("longitudinal_linkage_auc", 0.5),
    ]
    return float(np.mean(parts))


def evaluate_trial4_adversary(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    raw_by_id: dict[str, dict[str, Any]],
    persona_table: dict[str, dict[str, Any]],
    *,
    embedder: Embedder | None = None,
    seed: int = 42,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    tfidf_fit_scope: str = DEFAULT_TFIDF_FIT_SCOPE,
) -> dict[str, float | str | int]:
    """Run Trial4 adversary suite on frozen exports.

    Camera-ready protocol: character n-gram TF-IDF (``char_wb``, 1–3, 5000
    features) fitted on that condition's **training** export strings only
    (``tfidf_fit_scope="train_only"``), then applied unchanged to held-out
    exports. ``tfidf_fit_scope="train_test"`` is the superseded transductive
    fit (train+test); keep it only for audit comparison. Caller-supplied
    ``embedder`` (e.g. unit-test mocks) skips TF-IDF fitting.
    """
    empty: dict[str, float | str | int] = {
        "persona_top1": 0.0,
        "persona_top5": 0.0,
        "candidate_set_size_mean": 0.0,
        "random_baseline_top1": 0.0,
        "n_test_personas": 0,
        "medication_class_macro_f1": 0.0,
        "occupation_sector_macro_f1": 0.0,
        "symptom_categories_macro_f1": 0.0,
        "quasi_id_rarity_macro_f1": 0.0,
        "time_bucket_macro_f1": 0.0,
        "attribute_combined_macro_f1": 0.0,
        "longitudinal_linkage_auc": 0.5,
        "longitudinal_loo_top1": 0.0,
        "n_linkage_pairs": 0,
        "combined_linkage_score": 0.0,
        "token_recovery_rate": 0.0,
        "n_test": 0,
        "n_train": len(train_rows),
        "embedder": "none",
        "similarity_threshold": similarity_threshold,
        "tfidf_fit_scope": tfidf_fit_scope,
        "combined_linkage_formula": (
            "mean(persona_top1, attribute_combined_macro_f1, longitudinal_linkage_auc)"
        ),
    }
    if not test_rows:
        return empty

    train_texts = _export_texts(train_rows)
    test_texts = _export_texts(test_rows)
    tfidf_meta: dict[str, Any] = {"tfidf_fit_scope": tfidf_fit_scope}
    if embedder is not None:
        resolved = embedder
    else:
        # Frozen paper protocol is TF-IDF char_wb, not MiniLM.
        resolved, tfidf_meta = fit_trial4_tfidf_embedder(
            train_texts,
            test_texts,
            tfidf_fit_scope=tfidf_fit_scope,
        )
    embedder_name = getattr(resolved, "model_name", type(resolved).__name__)
    embeddings_train = resolved.embed(train_texts)
    embeddings_test = resolved.embed(test_texts)

    persona_metrics = _persona_inference(
        train_rows,
        test_rows,
        embeddings_train,
        embeddings_test,
        similarity_threshold=similarity_threshold,
    )
    attr_metrics = _attribute_inference(
        train_rows,
        test_rows,
        embeddings_train,
        embeddings_test,
        persona_table,
        seed=seed,
    )
    linkage_metrics = _longitudinal_linkage_auc(
        test_rows, embeddings_test, seed=seed
    )
    loo_top1 = _longitudinal_loo_top1(test_rows, embeddings_test)

    result: dict[str, float | str | int] = {
        **persona_metrics,
        **attr_metrics,
        **linkage_metrics,
        "longitudinal_loo_top1": loo_top1,
        "token_recovery_rate": float(token_recovery_rate(test_rows, raw_by_id)),
        "n_test": len(test_rows),
        "n_train": len(train_rows),
        "embedder": embedder_name,
        "similarity_threshold": similarity_threshold,
        "combined_linkage_formula": (
            "mean(persona_top1, attribute_combined_macro_f1, longitudinal_linkage_auc)"
        ),
        **tfidf_meta,
    }
    result["combined_linkage_score"] = combined_linkage_score(
        {k: float(v) for k, v in result.items() if isinstance(v, (int, float))}
    )
    return result
