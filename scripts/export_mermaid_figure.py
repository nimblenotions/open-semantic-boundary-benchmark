#!/usr/bin/env python3
"""Export a .mmd diagram to PNG, SVG, and PDF."""

from __future__ import annotations

import argparse
import base64
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "semantic-boundary-export/1.0"


def _strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("%%"):
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def _encode_mermaid_ink(source: str) -> str:
    return base64.urlsafe_b64encode(source.encode("utf-8")).decode().rstrip("=")


def _export_mermaid_ink(source: str, fmt: str) -> bytes:
    encoded = _encode_mermaid_ink(source)
    url = f"https://mermaid.ink/{fmt}/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _export_kroki(source: str, fmt: str) -> bytes:
    url = f"https://kroki.io/mermaid/{fmt}"
    req = urllib.request.Request(
        url,
        data=source.encode("utf-8"),
        headers={"Content-Type": "text/plain", "User-Agent": USER_AGENT},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _export_mmdc(input_path: Path, dest: Path, fmt: str) -> bool:
    mmdc = shutil.which("mmdc")
    if not mmdc:
        return False
    cmd = [mmdc, "-i", str(input_path), "-o", str(dest), "-b", "white"]
    if fmt == "png":
        cmd.extend(["-w", "1200"])
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return False
    return dest.is_file()


def export_diagram(input_path: Path, output_stem: Path) -> None:
    source = _strip_comments(input_path.read_text(encoding="utf-8"))
    output_stem.parent.mkdir(parents=True, exist_ok=True)

    backends = (
        ("mermaid.ink", lambda fmt: _export_mermaid_ink(source, fmt)),
        ("kroki", lambda fmt: _export_kroki(source, fmt)),
    )

    for fmt in ("png", "svg", "pdf"):
        dest = output_stem.with_suffix(f".{fmt}")
        if _export_mmdc(input_path, dest, fmt):
            print(f"Wrote {dest} (mmdc)")
            continue

        last_error: Exception | None = None
        for name, exporter in backends:
            try:
                dest.write_bytes(exporter(fmt))
                print(f"Wrote {dest} ({name})")
                break
            except (urllib.error.URLError, urllib.error.HTTPError) as exc:
                last_error = exc
        else:
            raise SystemExit(
                f"Failed to export {fmt}: {last_error}. "
                "Check network or install @mermaid-js/mermaid-cli (mmdc)."
            ) from last_error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Mermaid .mmd to PNG/SVG/PDF")
    parser.add_argument("input", type=Path)
    parser.add_argument("output_stem", type=Path, nargs="?")
    args = parser.parse_args(argv)
    stem = args.output_stem or args.input.with_suffix("")
    export_diagram(args.input, stem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
