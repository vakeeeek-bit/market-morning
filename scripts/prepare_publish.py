#!/usr/bin/env python3
"""Validate a report bundle and publish it to data/ as one local operation."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from validate_data import run


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = ("report.json", "japan-stocks.json")
OPTIONAL_FILES = ("market.json", "status.json")


def prepare(source: Path, root: Path = ROOT, check_only: bool = False) -> list[Path]:
    source = source.resolve()
    root = root.resolve()
    missing = [name for name in REQUIRED_FILES if not (source / name).is_file()]
    if missing:
        raise ValueError(f"公開候補に必須ファイルがありません: {', '.join(missing)}")

    selected = [name for name in (*REQUIRED_FILES, *OPTIONAL_FILES) if (source / name).is_file()]
    with tempfile.TemporaryDirectory(prefix="market-morning-publish-") as temp:
        staged_root = Path(temp)
        shutil.copytree(root / "schemas", staged_root / "schemas")
        shutil.copytree(root / "data", staged_root / "data")
        for name in selected:
            shutil.copy2(source / name, staged_root / "data" / name)

        result = run(staged_root)
        for message in result.warnings:
            print(f"WARNING: {message}")
        if result.errors:
            details = "\n".join(f"- {message}" for message in result.errors)
            raise ValueError(f"公開候補の検証に失敗しました:\n{details}")

    targets = [root / "data" / name for name in selected]
    if check_only:
        return targets

    for name, target in zip(selected, targets):
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
        try:
            shutil.copy2(source / name, temporary_path)
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="report.jsonとjapan-stocks.jsonを組み合わせ検証してdata/へ配置します"
    )
    parser.add_argument("source", type=Path, help="公開候補JSONを置いたディレクトリ")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        targets = prepare(args.source, args.root, args.check_only)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    action = "検証完了" if args.check_only else "配置完了"
    print(f"{action}: {', '.join(path.name for path in targets)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
