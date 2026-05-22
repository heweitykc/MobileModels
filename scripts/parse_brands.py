#!/usr/bin/env python3
"""Parse MobileModels brand markdown files into JSON for programmatic use.

Reads every ``brands/*.md`` file in the repository and produces two JSON files:

* ``data/mobile_models.json``       structured by brand > category > product > models
* ``data/mobile_models_flat.json``  flat list, one entry per model code (好查询)

Usage::

    python scripts/parse_brands.py                 # default paths
    python scripts/parse_brands.py --indent 0      # 输出压缩 JSON
    python scripts/parse_brands.py --brands-dir custom/brands --out-dir custom/out
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# --------------------------------------------------------------------------- #
# Regex patterns
# --------------------------------------------------------------------------- #

# Product header, with optional internal model id and optional codename, e.g.
#   **360 手机 N4:**
#   **HUAWEI Mate 9 (`Manhattan`):**
#   **[`N82AP`] iPhone 3G (`iPhone1,2`):**
# Allows zero-width characters and full-width colon.
_PRODUCT_HEADER_RE = re.compile(
    r"^\*\*\s*"
    r"(?:\[\s*`([^`]+)`\s*\]\s*)?"           # optional [`internal id`]
    r"(.*?)"                                  # product name (non-greedy)
    r"(?:\s*\(\s*`([^`]+)`\s*\))?"           # optional (`codename`)
    r"\s*[:\uFF1A]?"                         # optional colon (half / full width)
    r"[\s\u200b\u200c\u200d\ufeff]*"        # optional zero-width / spaces
    r"\*\*\s*$"
)

# Model line, e.g.
#   `1503-M02`: 360 手机 N4 移动版
#   `NOH-AN00` `NOH-AN01`: HUAWEI Mate 40 Pro 5G
_MODEL_LINE_RE = re.compile(
    r"^((?:`[^`]+`\s*)+)\s*[:\uFF1A]\s*(.+?)\s*$"
)

_BACKTICK_RE = re.compile(r"`([^`]+)`")


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #


@dataclass
class Model:
    codes: list[str]
    description: str


@dataclass
class Product:
    name: str
    internal_name: Optional[str] = None
    codename: Optional[str] = None
    models: list[Model] = field(default_factory=list)


@dataclass
class Category:
    name: str
    products: list[Product] = field(default_factory=list)


@dataclass
class Brand:
    file: str
    title: str
    meta: dict = field(default_factory=dict)
    categories: list[Category] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


def parse_brand_file(path: Path) -> Brand:
    """Parse a single ``brands/<name>.md`` file."""

    brand = Brand(file=path.stem, title="")
    current_category: Optional[Category] = None
    current_product: Optional[Product] = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("# "):
            brand.title = line[2:].strip()
            continue

        if line.startswith("## "):
            current_category = Category(name=line[3:].strip())
            brand.categories.append(current_category)
            current_product = None
            continue

        # Meta lines appear above the first `##` heading.
        if line.startswith("- ") and current_category is None:
            content = line[2:].strip()
            if ":" in content:
                key, _, value = content.partition(":")
                brand.meta[key.strip()] = value.strip()
            else:
                brand.meta.setdefault("_notes", []).append(content)
            continue

        product_match = _PRODUCT_HEADER_RE.match(line)
        if product_match:
            internal, name, codename = product_match.groups()
            if current_category is None:
                # Some files (e.g. coolpad.md) skip the `##` heading entirely.
                current_category = Category(name="_default")
                brand.categories.append(current_category)
            current_product = Product(
                name=(name or "").strip(),
                internal_name=internal.strip() if internal else None,
                codename=codename.strip() if codename else None,
            )
            current_category.products.append(current_product)
            continue

        model_match = _MODEL_LINE_RE.match(line)
        if model_match and current_product is not None:
            codes_part, description = model_match.groups()
            codes = _BACKTICK_RE.findall(codes_part)
            current_product.models.append(
                Model(codes=codes, description=description.strip())
            )
            continue

        # Anything else (blockquotes, stray prose, etc.) is intentionally ignored.

    return brand


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #


def build_flat_index(brands: list[Brand]) -> list[dict]:
    """Flatten brands into one entry per ``(code, model)`` pair."""

    flat: list[dict] = []
    for brand in brands:
        for category in brand.categories:
            for product in category.products:
                for model in product.models:
                    for code in model.codes:
                        flat.append(
                            {
                                "code": code,
                                "description": model.description,
                                "product_name": product.name,
                                "product_codename": product.codename,
                                "product_internal_name": product.internal_name,
                                "category": category.name,
                                "brand_file": brand.file,
                                "brand_title": brand.title,
                            }
                        )
    return flat


def compute_stats(brands: list[Brand]) -> dict:
    cat_count = sum(len(b.categories) for b in brands)
    prod_count = sum(len(c.products) for b in brands for c in b.categories)
    model_count = sum(
        len(p.models) for b in brands for c in b.categories for p in c.products
    )
    code_count = sum(
        len(m.codes)
        for b in brands
        for c in b.categories
        for p in c.products
        for m in p.models
    )
    return {
        "brands": len(brands),
        "categories": cat_count,
        "products": prod_count,
        "models": model_count,
        "codes": code_count,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Optional[list[str]] = None) -> int:
    repo_root = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--brands-dir",
        type=Path,
        default=repo_root / "brands",
        help="Path to brands/ directory (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=repo_root / "data",
        help="Output directory for JSON files (default: %(default)s)",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation; use 0 for compact output (default: 2)",
    )
    args = parser.parse_args(argv)

    if not args.brands_dir.is_dir():
        print(f"ERROR: brands directory not found: {args.brands_dir}", file=sys.stderr)
        return 1

    md_files = sorted(args.brands_dir.glob("*.md"))
    if not md_files:
        print(f"ERROR: no .md files found in {args.brands_dir}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)

    brands: list[Brand] = []
    for path in md_files:
        try:
            brands.append(parse_brand_file(path))
        except Exception as exc:  # pragma: no cover - defensive
            print(f"WARN: failed to parse {path.name}: {exc}", file=sys.stderr)

    stats = compute_stats(brands)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    structured_payload = {
        "generated_at": timestamp,
        "source": "https://github.com/KHwang9883/MobileModels",
        "stats": stats,
        "brands": [asdict(b) for b in brands],
    }

    flat_index = build_flat_index(brands)
    flat_payload = {
        "generated_at": timestamp,
        "source": structured_payload["source"],
        "stats": {"entries": len(flat_index)},
        "entries": flat_index,
    }

    indent = args.indent if args.indent > 0 else None
    main_path = args.out_dir / "mobile_models.json"
    flat_path = args.out_dir / "mobile_models_flat.json"

    main_path.write_text(
        json.dumps(structured_payload, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )
    flat_path.write_text(
        json.dumps(flat_payload, ensure_ascii=False, indent=indent),
        encoding="utf-8",
    )

    print(
        "Parsed {brands} brands, {categories} categories, "
        "{products} products, {models} model lines, "
        "{codes} codes.".format(**stats)
    )
    print(f"Wrote: {main_path}")
    print(f"Wrote: {flat_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
