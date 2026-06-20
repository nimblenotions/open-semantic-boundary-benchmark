.PHONY: install generate provenance-targets validate transform eval figures pipeline test lint consolidate-llm-cache materialize-llm consolidate-eval-cache ollama-parallel operative-selection merge-sensitivity additional-analyses bootstrap-cis eval-analytics figures-all repro-smoke

ROOT := $(shell pwd)
export PYTHONPATH := $(ROOT)/src:$(PYTHONPATH)
CONFIG ?= configs/pilot_v0.1.1.yaml

install:
	pip install -e ".[dev]"

generate:
	python -m generate.generate_corpus --config $(CONFIG)

provenance-targets:
	python scripts/generate_provenance_targets.py --config $(CONFIG)

validate:
	python -m generate.validate --config $(CONFIG)

transform:
	python -m transform.run_transforms --config $(CONFIG)

transform-analytics:
	python -m transform.run_analytics_transforms --config $(CONFIG)

bundle-transforms:
	python -m transform.bundle_transforms --config $(CONFIG)

consolidate-llm-cache:
	python scripts/consolidate_llm_cache.py --config $(CONFIG)

materialize-llm:
	python scripts/materialize_llm_cache.py --config $(CONFIG) --consolidate-cache

consolidate-eval-cache:
	python scripts/consolidate_eval_cache.py

TIER ?= 1-linkage

eval:
	python eval/run_obs_study.py --config $(CONFIG) --tier $(TIER)

eval-linkage:
	python eval/run_obs_study.py --config $(CONFIG) --tier linkage

eval-tier1:
	python eval/run_obs_study.py --config $(CONFIG) --tier 1

eval-tier0:
	python eval/run_obs_study.py --config $(CONFIG) --tier 0

eval-analytics:
	python eval/run_analytics_study.py --config $(CONFIG) --tier $(TIER)

eval-analytics-tier0:
	python eval/run_analytics_study.py --config $(CONFIG) --tier 0

eval-analytics-tier1:
	python eval/run_analytics_study.py --config $(CONFIG) --tier 1

cohort-tier1:
	python eval/run_cohort_tier1.py --config $(CONFIG)

additional-analyses:
	python eval/run_additional_analyses.py --config $(CONFIG)

bootstrap-cis:
	python eval/run_bootstrap_cis.py --config $(CONFIG)

figures-all: cohort-tier1 merge-sensitivity figures operative-selection additional-analyses bootstrap-cis

merge-sensitivity:
	python eval/merge_sensitivity.py --config $(CONFIG)

operative-selection:
	python eval/run_operative_selection.py --config $(CONFIG)

figures:
	python eval/run_figures.py --config $(CONFIG)

ollama-parallel:
	python scripts/run_ollama_parallel.py --config $(CONFIG) --max-workers 4 $(ARGS)

retention:
	python eval/run_retention.py --config $(CONFIG) --figure

pipeline: generate transform eval figures
	bash scripts/run_pipeline.sh

test:
	pytest tests/ -q

repro-smoke:
	@echo "Checking baseline artifact parity (no Ollama)..."
	@python scripts/repro_smoke.py

lint:
	ruff check src tests eval
