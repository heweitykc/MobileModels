#!/usr/bin/env python3
"""Export ``data/mobile_models_flat.json`` to PHP + JSON dictionary files.

Outputs:

* ``data/mobile_models.php`` — PHP array ``[ 'CODE' => 'Product Name', ... ]``
* ``data/mobile_models_dict.json`` — Same content as a JSON object

Duplicate codes keep the first occurrence (matches the order in the source
JSON, i.e. the alphabetical brand-file order produced by ``parse_brands.py``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def php_single_quote(s: str) -> str:
    """Escape a string for use inside PHP single-quoted literals."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def build_php(items: list[tuple[str, str]], source_name: str) -> str:
    lines = [
        "<?php",
        "",
        "/**",
        " * Mobile phone model code -> product name lookup table.",
        " *",
        f" * Auto-generated from {source_name}; do not edit by hand.",
        f" * Total entries: {len(items)}.",
        " *",
        " * Usage:",
        " *     $models = require __DIR__ . '/mobile_models.php';",
        " *     echo $models['NOH-AN00']; // HUAWEI Mate 40 Pro",
        " */",
        "",
        "return [",
    ]
    for code, name in items:
        lines.append(
            f"    '{php_single_quote(code)}' => '{php_single_quote(name)}',"
        )
    lines.append("];")
    lines.append("")
    return "\n".join(lines)


def build_json(items: list[tuple[str, str]]) -> str:
    # Use an ordered dict so the output order matches the PHP file.
    payload = dict(items)
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / "data"
    default_in = data_dir / "mobile_models_flat.json"
    default_php = data_dir / "mobile_models.php"
    default_json = data_dir / "mobile_models_dict.json"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=default_in,
        help="Input flat JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--php",
        type=Path,
        default=default_php,
        help="Output PHP file (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        default=default_json,
        help="Output JSON dictionary file (default: %(default)s)",
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help="Sort output by code (default: keep first-seen order)",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    entries = payload.get("entries", [])

    seen: dict[str, str] = {}
    for entry in entries:
        code = entry.get("code")
        name = entry.get("product_name")
        if code is None or name is None:
            continue
        if code in seen:
            continue
        seen[code] = name

    items = sorted(seen.items()) if args.sort else list(seen.items())

    args.php.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.php.write_text(build_php(items, args.input.name), encoding="utf-8")
    args.json_path.write_text(build_json(items), encoding="utf-8")

    print(f"Wrote {len(items)} unique codes:")
    print(f"  PHP : {args.php}")
    print(f"  JSON: {args.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
