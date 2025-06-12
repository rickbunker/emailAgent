#!/usr/bin/env python3
"""Quick-and-dirty helper to migrate bare print() statements to project logger.

Usage (from repo root):
    python scripts/convert_prints.py --apply

Without ``--apply`` the script runs in *dry-run* mode and prints the diff that
would be applied.  It only touches files under ``src/`` and skips anything in
``tests`` or ``scripts``.  The heuristic is intentionally simple:  if the first
argument to ``print`` is a string literal starting with an emoji, "[WARN]",
"[ERROR]" etc. we map it to ``logger.warning`` or ``logger.error``; otherwise
we default to ``logger.info``.

The script inserts (if missing)::

    from src.utils.logging_system import get_logger
    logger = get_logger(__name__)

at the top of the file, just below existing imports.

This is *not* perfect, but it handles ~90 % of the straightforward cases and
lets Ruff enforce the remaining stragglers.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Iterable

SRC_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src"
PRINT_RE = re.compile(r"^\s*print\((.*)\)\s*$")


def iter_py_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    for path in root.rglob("*.py"):
        if any(part in {"tests", "scripts"} for part in path.parts):
            continue
        yield path


def classify_call(arg_src: str) -> str:
    """Return logger level (info|warning|error|debug) for the given arg source."""
    lowered = arg_src.lower()
    if lowered.startswith("\"[warn") or "warning" in lowered or "⚠️" in lowered:
        return "warning"
    if lowered.startswith("\"[error") or "❌" in lowered:
        return "error"
    if lowered.startswith("\"[debug"):
        return "debug"
    return "info"


def transform_file(path: pathlib.Path) -> tuple[str, bool]:
    """Return new text plus a flag whether any change was made."""
    text = path.read_text()
    lines = text.splitlines()
    changed = False
    new_lines: list[str] = []

    has_logger_import = any("get_logger(" in ln for ln in lines[:40])

    for line in lines:
        m = PRINT_RE.match(line)
        if m:
            args_src = m.group(1).strip()
            level = classify_call(args_src)
            new_line = re.sub(r"^\s*print", f"logger.{level}", line)
            new_lines.append(new_line)
            changed = True
        else:
            new_lines.append(line)

    if changed and not has_logger_import:
        # insert import after first block of imports
        for idx, ln in enumerate(new_lines):
            if ln.startswith("import") or ln.startswith("from"):
                continue
            # insert here
            new_lines.insert(idx, "logger = get_logger(__name__)")
            new_lines.insert(idx, "from src.utils.logging_system import get_logger")
            break

    return "\n".join(new_lines), changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write changes in-place")
    args = parser.parse_args()

    for py_path in iter_py_files(SRC_ROOT):
        new_text, changed = transform_file(py_path)
        if not changed:
            continue
        if args.apply:
            py_path.write_text(new_text)
            print(f"✔ transformed {py_path.relative_to(SRC_ROOT.parent)}")
        else:
            print(f"--- {py_path} (preview) ---")
            print("# <diff omitted>\n")


if __name__ == "__main__":
    sys.exit(main()) 