"""Generate raw + ground_truth JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from generate.corpus import generate_corpus
from sbb.config import load_config, repo_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Open SBB-Obs corpus")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--skip-validate", action="store_true")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    root = repo_root()
    manifest = generate_corpus(cfg, root)
    print(json.dumps(manifest, indent=2))

    if not args.skip_validate:
        from generate.validate import validate_corpus

        ok, report = validate_corpus(cfg, root)
        print(json.dumps(report, indent=2), file=sys.stderr)
        if not ok:
            print("validate_corpus: FAILED", file=sys.stderr)
            return 1
        print("validate_corpus: OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
