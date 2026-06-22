.PHONY: install generate provenance-targets validate transform eval figures pipeline test lint consolidate-llm-cache materialize-llm consolidate-eval-cache ollama-parallel operative-selection merge-sensitivity additional-analyses bootstrap-cis eval-analytics figures-all repro-smoke byo-smoke

ROOT := $(shell pwd)
export PYTHONPATH := $(ROOT)/src:$(PYTHONPATH)
CONFIG ?= configs/pilot_v0.1.1.yaml

# Prefer repo .venv when present (no shell activation required); fall back to PATH (CI).
VENV_PYTHON := $(wildcard .venv/bin/python)
PYTHON := $(if $(VENV_PYTHON),$(dir $(VENV_PYTHON))python,python)
PYTEST := $(if $(VENV_PYTHON),$(dir $(VENV_PYTHON))pytest,pytest)
PIP := $(if $(VENV_PYTHON),$(dir $(VENV_PYTHON))pip,pip)
RUFF := $(if $(wildcard .venv/bin/ruff),.venv/bin/ruff,ruff)

install:
	$(PIP) install -e ".[dev]"

generate:
	$(PYTHON) -m generate.generate_corpus --config $(CONFIG)

provenance-targets:
	$(PYTHON) scripts/generate_provenance_targets.py --config $(CONFIG)

validate:
	$(PYTHON) -m generate.validate --config $(CONFIG)

transform:
	$(PYTHON) -m transform.run_transforms --config $(CONFIG)

transform-analytics:
	$(PYTHON) -m transform.run_analytics_transforms --config $(CONFIG)

bundle-transforms:
	$(PYTHON) -m transform.bundle_transforms --config $(CONFIG)

consolidate-llm-cache:
	$(PYTHON) scripts/consolidate_llm_cache.py --config $(CONFIG)

materialize-llm:
	$(PYTHON) scripts/materialize_llm_cache.py --config $(CONFIG) --consolidate-cache

consolidate-eval-cache:
	$(PYTHON) scripts/consolidate_eval_cache.py

TIER ?= 1-linkage

eval:
	$(PYTHON) eval/run_obs_study.py --config $(CONFIG) --tier $(TIER)

eval-linkage:
	$(PYTHON) eval/run_obs_study.py --config $(CONFIG) --tier linkage

eval-tier1:
	$(PYTHON) eval/run_obs_study.py --config $(CONFIG) --tier 1

eval-tier0:
	$(PYTHON) eval/run_obs_study.py --config $(CONFIG) --tier 0

eval-analytics:
	$(PYTHON) eval/run_analytics_study.py --config $(CONFIG) --tier $(TIER)

eval-analytics-tier0:
	$(PYTHON) eval/run_analytics_study.py --config $(CONFIG) --tier 0

eval-analytics-tier1:
	$(PYTHON) eval/run_analytics_study.py --config $(CONFIG) --tier 1

cohort-tier1:
	$(PYTHON) eval/run_cohort_tier1.py --config $(CONFIG)

additional-analyses:
	$(PYTHON) eval/run_additional_analyses.py --config $(CONFIG)

bootstrap-cis:
	$(PYTHON) eval/run_bootstrap_cis.py --config $(CONFIG)

figures-all: cohort-tier1 merge-sensitivity figures operative-selection additional-analyses bootstrap-cis

merge-sensitivity:
	$(PYTHON) eval/merge_sensitivity.py --config $(CONFIG)

operative-selection:
	$(PYTHON) eval/run_operative_selection.py --config $(CONFIG)

figures:
	$(PYTHON) eval/run_figures.py --config $(CONFIG)

ollama-parallel:
	$(PYTHON) scripts/run_ollama_parallel.py --config $(CONFIG) --max-workers 4 $(ARGS)

retention:
	$(PYTHON) eval/run_retention.py --config $(CONFIG) --figure

pipeline: generate transform eval figures
	bash scripts/run_pipeline.sh

test:
	$(PYTEST) tests/ -q

repro-smoke:
	@echo "Checking baseline artifact parity (no Ollama)..."
	@$(PYTHON) scripts/repro_smoke.py

byo-smoke:
	@echo "Checking BYO sample export plumbing..."
	@$(PYTEST) tests/test_byo_exports.py -q

lint:
	$(RUFF) check src tests eval
