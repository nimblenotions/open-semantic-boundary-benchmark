# CIKM 2026 camera-ready — change inventory & OSS repro handoff

> **Not a reader path.** Maintainer archaeology from the camera-ready export. Paper readers should start at the [root README](../README.md) and [`releases/cikm-2026/`](../releases/cikm-2026/).

**Created:** 2026-08-23  
**Scope:** Sun **2026-08-17** → Sheridan submit + author registration (paper **4405**)  
**Research repo:** `gauravbaruah/sem-bound-sim-bench` (`feature/cikm-sheridan-package` at handoff)  
**Public repro target:** https://github.com/nimblenotions/open-semantic-boundary-benchmark/tree/cikm-2026  
**Tag (planned):** `cikm-2026` on `nimblenotions/open-semantic-boundary-benchmark`

Use this document to drive the Open SBB export: what changed, what is canonical vs historical, and what must ship on the public tag so CIKM numbers and figures reproduce.

---

## Executive summary

The last week (~143 commits, 4k+ lines in `eval/` + `src/`) was dominated by **experiment protocol repairs** and **paper retargeting**, not a science rewrite. Headline qualitative claims held; confidence increased because linkage and Ta-5 scoring now match the paper’s stated protocol.

**Canonical protocol** is declared in `configs/cikm_v0.1.yaml` → `paper_protocol` (locked **2026-08-19**):

- **Linkage:** train-only TF-IDF `char_wb` (not transductive train+test fit)
- **Risk surface:** purpose-specific \(R(z_{c,T})\) (not shared observability-only \(R\))
- **Ta-5 cohort:** Track C `assessor_symmetric` (not mixed Track A)

**Frozen rule:** `outputs/pilot_v2/**` is **historical** — do not overwrite. Canonical CIKM outputs live under `outputs/pilot_v2_camera_ready/` and `outputs/post_acceptance_experiments/`.

---

## Branch map (what landed where)

| Branch | Role | Tip (approx.) |
|--------|------|----------------|
| `feature/cikm-camera-ready` | Pre–Aug 17 freeze baseline | `d083edd` — ED/Results freeze start |
| `feature/post-acceptance-experiments` | **All experiment repairs** | TF-IDF, Track C, purpose-specific linkage |
| `feature/cikm-camera-ready-text-pass` → `feature/cikm-sheridan-ready-pass` | Paper retarget to repaired protocol | Figs 2–4, Table 3, §3–§5 |
| `feature/cikm-final-manual-pass` | Final prose + Sheridan prep | GenAI, captions |
| `feature/cikm-sheridan-package` | Upload bundle + submitted | `544224c` (registration + Sheridan confirm) |
| `feature/ta5-feature-path-ablation-diagnostic` | Ta-5 path diagnostic (not paper-primary) | merged into manual pass |

**Source of truth for “what CIKM reports”:** `configs/cikm_v0.1.yaml` → `paper_protocol`.

---

## 1. Bugs / protocol errors found

### A. Transductive TF-IDF linkage (fixed)

- **Bug:** `tfidf_fit_scope=train_test` — vectorizer fit on **train + test** exports (transductive leakage).
- **Fix:** `train_only` — fit on train exports only, then transform train/test.
- **Impact on headlines:** **None at reported \(R_{\max}\)** — same operative winners, same \(R(z)\) rank order, no boundary crossings (`outputs/pilot_v2_tfidf_train_only/tfidf_fit_sensitivity_report.md`).
- **Headline story unchanged:** e.g. `red_tokenize` still near-zero token / high persona.
- **Artifacts:**
  - `outputs/pilot_v2` = historical (transductive)
  - `outputs/pilot_v2_camera_ready` = canonical CIKM linkage
  - audit copy: `outputs/pilot_v2_tfidf_train_only`

### B. Ta-5 “mixed Track A” cohort pipeline (fixed → Track C)

- **Bug:** \(T_a\)-5 used **mixed** Tier-1/Qwen test-side scoring inconsistent with “assessor on released export” framing.
- **Fix:** **Track C** = `assessor_symmetric` — RF cohort classifier on **analytics export fields only** (train-side Qwen caches; rescored without Ollama).
- **Impact:** **Only \(T_a\)-5 at \(R_{\max}=0.45\)** changes winner: `redact_bracket` (0.39) → `redact_surrogate` (~0.26). Other tasks / thresholds largely unchanged.
- **Artifacts:** `outputs/post_acceptance_experiments/ta5_cohort_audit/` + `track_c_scores.json` + `snapshot_track_c/`

### C. Shared observability \(R\) vs purpose-specific \(R\) (audited, adopted for paper)

- **Issue:** Utility used purpose-conditioned exports \(z_{c,T}\) but linkage sometimes used **shared observability** \(R(z_{c,T_o})\).
- **Audit:** `outputs/post_acceptance_experiments/purpose_specific_linkage/REPORT.md`
- **Decision (paper):** **Purpose-specific** \(R(z_{c,T})\) is primary; at focal **0.45 winners agree** with shared-obs protocol; divergence at 0.50/0.55 strengthens purpose-dependence (paper text updated accordingly).
- **Not a “bug” in old numbers** — explicit protocol choice, now locked.

---

## 2. Experiment code added/changed (~4,369 lines in `src/` + `eval/`)

| Area | Files | What |
|------|-------|------|
| TF-IDF protocol | `src/eval/adversary_trial4.py`, `configs/cikm_v0.1.yaml`, tests | `tfidf_fit_scope`, train-only default, metadata in linkage runs |
| Camera-ready promote | `eval/promote_camera_ready_tfidf_train_only.py` | Rebuild linkage + copy utility from frozen `pilot_v2` → `pilot_v2_camera_ready` |
| TF-IDF sensitivity | `eval/run_tfidf_fit_sensitivity.py` | A vs B comparison without overwriting `pilot_v2` |
| Ta-5 cohort audit | `eval/run_ta5_cohort_audit.py`, `src/eval/analytics_cohort.py` | Track C scoring, caches, snapshot |
| Ta-5 direct ceiling | `eval/run_ta5_direct_field_ceiling.py` | Diagnostic (ceiling / field-path) |
| Purpose-specific linkage | `eval/run_purpose_specific_linkage_audit.py` | Full audit + operative grid |
| Figure renders | `eval/render_analytics_linkage_decomposition.py`, `eval/render_ta5_track_c_snapshot.py`, `src/eval/advisor_figures.py` | Paper Figs 2–4 source PDFs |
| Protocol registry | `src/eval/paper_protocol.py`, `tests/test_paper_protocol.py` | Single config block for repro |

---

## 3. Charts / figures (what the submitted PDF uses)

| Paper asset | Source (research repo) | Protocol |
|-------------|------------------------|----------|
| **Fig. 2** linkage decomposition | `outputs/post_acceptance_experiments/purpose_specific_linkage/analytics_linkage_decomposition/figures/linkage_decomposition_observability_surface.pdf` | Purpose-specific obs surface; train-only TF-IDF |
| **Fig. 3** utility matrix | `outputs/post_acceptance_experiments/ta5_cohort_audit/snapshot_track_c/figures/utility_matrix_heatmap.pdf` | Track C Ta-5 column |
| **Fig. 4** regret matrix | `outputs/post_acceptance_experiments/ta5_cohort_audit/snapshot_track_c/figures/cross_purpose_regret_matrix.pdf` | Purpose-specific linkage at 0.45 |
| **Table 3** | Track C operative grid (`snapshot_track_c/table3_operative_grid.md`) | Ta-5 surrogate at 0.45 (not frozen Track A bracket) |
| Thumbnail (optional DL) | `paper/cikm-2026-short-paper-v3/sheridan-package/cikm2026-4405-thumbnail.jpg` | Crop of Fig. 2 |

**Sheridan staged PDFs** (flat paths in zip): `sheridan-package/cikm2026-4405-source/linkage_decomposition.pdf`, `utility_matrix_heatmap.pdf`, `cross_purpose_regret_matrix.pdf`.

**Chart polish:** lattice “conditions” not “arms”; Fig. 4 colorbar “own-winner vs reused”; axis labels for Ta-5 cohort; page layout (float parking).

---

## 4. Paper text (high level — not OSS-critical)

- Notation: \(z_{c,T}\), purpose-specific operative selection, oracle semantic exports.
- §4–§6 rewritten to match repaired experiments (not MiniLM; TF-IDF `char_wb`; Track C Ta-5).
- Repro footnote → public GitHub tree URL on tag `cikm-2026`.
- ~80+ prose/caption commits on Sheridan branch (no science rewrites post-freeze).

**Submitted paper:** `paper/cikm-2026-short-paper-v3/sheridan-package/cikm2026-4405-camera-ready.pdf` (Sheridan **4405**, registered + uploaded 2026-08-21).

---

## 5. Confidence summary (headlines vs repairs)

| Claim in paper | Still true after repairs? |
|----------------|---------------------------|
| Purpose-conditioned winners differ by task / \(R_{\max}\) | Yes — strengthened at some thresholds |
| Token suppression ≠ persona linkage (`red_tokenize`) | Yes |
| Cross-purpose reuse regret (Fig. 4) | Yes — rebuilt on purpose-specific surfaces |
| Same winner at **\(R_{\max}=0.45\)** for most tasks | Yes |
| **\(T_a\)-5 at 0.45** | **Changed** (surrogate not bracket) — paper updated |
| TF-IDF train-only vs transductive | Rankings/winners stable at reported thresholds |

---

## 6. Output tree: historical vs canonical

| Path | Role | OSS tag |
|------|------|---------|
| `outputs/pilot_v2/` | Pre-repair frozen pilot (transductive TF-IDF, mixed Ta-5, shared obs \(R\)) | Optional `frozen_historical/` with README — **not** canonical |
| `outputs/pilot_v2_tfidf_train_only/` | TF-IDF A vs B sensitivity audit | Optional audit bundle |
| `outputs/pilot_v2_camera_ready/` | Train-only linkage + copied utility; `CAMERA_READY_PROTOCOL.{json,md}` | **Ship** (or equivalent promoted metrics) |
| `outputs/post_acceptance_experiments/purpose_specific_linkage/` | Purpose-specific linkage audit + Fig. 2 sources | **Ship** subset referenced by protocol |
| `outputs/post_acceptance_experiments/ta5_cohort_audit/` | Track C scores, snapshot figures, Table 3 grid | **Ship** subset referenced by protocol |

`paper_protocol.frozen_historical` in `configs/cikm_v0.1.yaml` documents the old settings explicitly (`tfidf_fit: transductive_train_and_test`, `risk_surface: shared_observability`, `ta5: mixed_track_a`).

---

## 7. What the public `cikm-2026` tag must contain

**Repository:** https://github.com/nimblenotions/open-semantic-boundary-benchmark  
**Tree URL:** https://github.com/nimblenotions/open-semantic-boundary-benchmark/tree/cikm-2026

### Code (minimum)

- [ ] Eval + `src/eval/` at commits that produced paper numbers (from `feature/post-acceptance-experiments` lineage merged into export branch)
- [ ] `configs/cikm_v0.1.yaml` with full `paper_protocol` block
- [ ] Runners: `eval/promote_camera_ready_tfidf_train_only.py`, `eval/run_purpose_specific_linkage_audit.py`, `eval/run_ta5_cohort_audit.py`, figure render scripts
- [ ] `src/eval/paper_protocol.py` + `tests/test_paper_protocol.py`
- [ ] `Makefile` targets for repro smoke / full replay (document exact commands in README)

### Data & metrics (minimum)

- [ ] Committed transforms / splits / schemas needed to rerun (or documented download with checksums)
- [ ] `outputs/pilot_v2_camera_ready/` metrics + three paper figure PDFs (or script that regenerates them bit-for-bit)
- [ ] `outputs/post_acceptance_experiments/` paths listed in `paper_protocol` (`purpose_specific_linkage`, `ta5_cohort_audit/track_c_scores.json`, `snapshot_track_c/`)
- [ ] `CAMERA_READY_PROTOCOL.json` + `.md` asserting Table 3 / figure parity

### Docs (minimum)

- [ ] README: clone → install → one-command repro → expected checksums / winner table at \(R_{\max}=0.45\)
- [ ] This file (or OSS copy `docs/CIKM-2026-RELEASE-NOTES.md`) explaining historical vs canonical outputs
- [ ] Link to CIKM paper DOI `10.1145/3799682.3840076`

### Scrub before push

- [ ] No agent handoffs, `comment.cut`, private notes, or research-only strategy docs
- [ ] No credentials, local laptop paths in manifests (rewrite to repo-relative paths)
- [ ] `.gitignore` dev artifacts; no duplicate `cikm2026-4405-source 2/` style folders

### Do **not** ship as canonical

- `outputs/pilot_v2` as the default repro target (transductive TF-IDF, mixed Ta-5) — label as `frozen_historical` only if retained for audit

### Suggested annotated tag

```bash
git tag -a cikm-2026 -m "CIKM 2026 SBB pilot (train-only TF-IDF linkage, purpose-specific R, Track C Ta-5)."
git push origin cikm-2026
```

---

## 8. Verification checklist (before tagging public repo)

1. Fresh clone of `open-semantic-boundary-benchmark` @ `cikm-2026`
2. Run documented repro command(s)
3. Assert `CAMERA_READY_PROTOCOL` checks pass (Table 3 @ 0.45, `red_tokenize` token/persona, no transductive default)
4. Regenerate or diff the three paper figure PDFs against Sheridan `cikm2026-4405-camera-ready.pdf` pages 3–5
5. Confirm footnote URL resolves: `.../tree/cikm-2026`
6. Run `pytest tests/test_paper_protocol.py` (and full test suite if feasible)

---

## 9. Related research-repo docs

| Doc | Purpose |
|-----|---------|
| [`docs/OPEN-SBB-CIKM-2026-STRUCTURE-HANDOFF.md`](OPEN-SBB-CIKM-2026-STRUCTURE-HANDOFF.md) | **Next:** brainstorm public repo directory layout for tag `cikm-2026` |
| [`paper/cikm-2026-short-paper-v3/CAMERA-READY-STEPS.md`](../paper/cikm-2026-short-paper-v3/CAMERA-READY-STEPS.md) | Sheridan + OSS release checklist (update tag name to `cikm-2026` when footnote is updated) |
| [`paper/cikm-2026-short-paper-v3/SHERIDAN-PACKAGE-HANDOFF.md`](../paper/cikm-2026-short-paper-v3/SHERIDAN-PACKAGE-HANDOFF.md) | Submitted PDF + source zip |
| [`outputs/pilot_v2_camera_ready/CAMERA_READY_PROTOCOL.md`](../outputs/pilot_v2_camera_ready/CAMERA_READY_PROTOCOL.md) | Machine-checked protocol statement |
| [`outputs/post_acceptance_experiments/purpose_specific_linkage/REPORT.md`](../outputs/post_acceptance_experiments/purpose_specific_linkage/REPORT.md) | Purpose-specific \(R\) audit |
| [`docs/TRAVEL-HANDOFF.md`](TRAVEL-HANDOFF.md) | Two-repo remotes (`research` vs `open-sbb`) |
| [`docs/handoff-open-sbb-r1a.md`](handoff-open-sbb-r1a.md) | Broader OSS release gates (R1a/R1b) |

---

## 10. Next actions (maintainer)

1. Export clean slice from `sem-bound-sim-bench` → `nimblenotions/open-semantic-boundary-benchmark` branch `cikm-2026`
2. Align paper footnote in `main.tex` to `.../tree/cikm-2026` if it still says `cikm-2026-camera-ready`
3. Push annotated tag `cikm-2026`; verify tree URL
4. Optional later: Zenodo `opensbb-v0.1.3` — does not block CIKM DL if GitHub remains canonical

---

*Inventory compiled from git history 2026-08-17 → 2026-08-23 on `gauravbaruah/sem-bound-sim-bench`. Update this file when the OSS export lands.*
