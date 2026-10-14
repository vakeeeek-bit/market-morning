#!/usr/bin/env python3
"""Validate and publish independent Market Morning components.

A blocked AI report must not stop a verified market or news refresh. Each
publication unit is staged and validated against the current site separately;
only PASS/QUALIFIED units are copied into data/.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from validate_data import run


ROOT = Path(__file__).resolve().parents[1]
UNIT_FILES = {
    "report": {
        "required": ("report.json", "japan-stocks.json", "research-evidence.json"),
        "optional": ("market.json", "japan-market.json", "status.json"),
        "scope": "publish-report",
    },
    "market": {
        "required": ("market.json", "status.json"),
        "optional": ("japan-market.json",),
        "scope": "market-publication",
    },
    "news": {
        "required": ("news.json",),
        "optional": (),
        "scope": "news",
    },
}


@dataclass
class UnitResult:
    status: str
    files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _selected_files(source: Path, unit: str) -> list[str]:
    config = UNIT_FILES[unit]
    missing = [name for name in config["required"] if not (source / name).is_file()]
    if missing:
        raise ValueError(f"{unit}公開候補に必須ファイルがありません: {', '.join(missing)}")
    return [
        name for name in (*config["required"], *config["optional"])
        if (source / name).is_file()
    ]


def _stage_and_validate(source: Path, root: Path, unit: str):
    selected = _selected_files(source, unit)
    with tempfile.TemporaryDirectory(prefix=f"market-morning-{unit}-") as temp:
        staged_root = Path(temp)
        shutil.copytree(root / "schemas", staged_root / "schemas")
        shutil.copytree(root / "data", staged_root / "data")
        for name in selected:
            shutil.copy2(source / name, staged_root / "data" / name)
        result = run(staged_root, scope=UNIT_FILES[unit]["scope"])
    return selected, result


def _atomic_copy(source: Path, root: Path, names: list[str]) -> list[Path]:
    targets: list[Path] = []
    for name in names:
        target = root / "data" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
        try:
            shutil.copy2(source / name, temporary_path)
            os.replace(temporary_path, target)
        finally:
            temporary_path.unlink(missing_ok=True)
        targets.append(target)
    return targets


def _sync_unresolved(root: Path) -> None:
    from unresolved_items import merge_items
    import json

    evidence = json.loads((root / "data" / "research-evidence.json").read_text(encoding="utf-8"))
    merge_items(root / "data" / "unresolved-items.json", evidence)


def _refresh_market_context(root: Path) -> None:
    """Refresh context after report/news publication without coupling market updates."""
    from update_market_context import build_context

    if root != ROOT:
        return
    value = build_context()
    (root / "data" / "market-context.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def prepare_units(
    source: Path,
    root: Path = ROOT,
    components: tuple[str, ...] = ("report",),
    check_only: bool = False,
) -> dict[str, UnitResult]:
    source = source.resolve()
    root = root.resolve()
    outcomes: dict[str, UnitResult] = {}
    for unit in components:
        if unit not in UNIT_FILES:
            raise ValueError(f"未知の公開単位です: {unit}")
        temporary_source = None
        effective_source = source
        try:
            if unit == "news":
                from validate_news import sanitized_feed

                value = json.loads((source / "news.json").read_text(encoding="utf-8"))
                sanitized, feed_errors = sanitized_feed(value)
                if feed_errors:
                    raise ValueError("; ".join(feed_errors))
                temporary_source = tempfile.TemporaryDirectory(prefix="market-morning-safe-news-")
                effective_source = Path(temporary_source.name)
                (effective_source / "news.json").write_text(
                    json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            selected, validation = _stage_and_validate(effective_source, root, unit)
        except (OSError, ValueError) as error:
            outcomes[unit] = UnitResult(status="BLOCK", errors=[str(error)])
            if temporary_source:
                temporary_source.cleanup()
            continue
        if validation.errors:
            outcomes[unit] = UnitResult(
                status="BLOCK",
                errors=list(validation.errors),
                warnings=list(validation.warnings),
            )
            if temporary_source:
                temporary_source.cleanup()
            continue
        status = "QUALIFIED" if validation.warnings else "PASS"
        files = [root / "data" / name for name in selected]
        if not check_only:
            files = _atomic_copy(effective_source, root, selected)
            if unit == "report":
                _sync_unresolved(root)
        outcomes[unit] = UnitResult(
            status=status,
            files=files,
            warnings=list(validation.warnings),
        )
        if temporary_source:
            temporary_source.cleanup()
    if not check_only and any(
        unit in outcomes and outcomes[unit].status != "BLOCK"
        for unit in ("report", "news")
    ):
        try:
            _refresh_market_context(root)
        except (OSError, ValueError, KeyError) as error:
            # Context is a derived reader aid. Its failure must not roll back an
            # independently safe report/news publication; CI and the UI's stale
            # state make the omission visible for repair.
            print(f"WARNING: market-context更新失敗: {error}", file=sys.stderr)
    return outcomes


def prepare(source: Path, root: Path = ROOT, check_only: bool = False) -> list[Path]:
    """Backward-compatible strict report-bundle entrypoint used by tests/tools."""
    outcome = prepare_units(source, root, ("report",), check_only)["report"]
    if outcome.status == "BLOCK":
        details = "\n".join(f"- {message}" for message in outcome.errors)
        raise ValueError(f"公開候補の検証に失敗しました:\n{details}")
    return outcome.files


def _auto_components(source: Path) -> tuple[str, ...]:
    found = []
    for unit, config in UNIT_FILES.items():
        if all((source / name).is_file() for name in config["required"]):
            found.append(unit)
    return tuple(found)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="総合レポート・市場・確認済みニュースを公開単位ごとに検証して配置します"
    )
    parser.add_argument("source", type=Path, help="公開候補JSONを置いたディレクトリ")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--components", default="auto", help="report,market,news または auto")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    components = _auto_components(args.source) if args.components == "auto" else tuple(
        item.strip() for item in args.components.split(",") if item.strip()
    )
    if not components:
        print("ERROR: 公開可能な候補単位がありません", file=sys.stderr)
        return 1
    outcomes = prepare_units(args.source, args.root, components, args.check_only)
    admitted = 0
    for unit, outcome in outcomes.items():
        print(f"{unit}: {outcome.status}")
        for warning in outcome.warnings:
            print(f"WARNING: {warning}")
        for error in outcome.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if outcome.status != "BLOCK":
            admitted += 1
            action = "検証完了" if args.check_only else "配置完了"
            print(f"{action}: {', '.join(path.name for path in outcome.files)}")
    return 0 if admitted else 1


if __name__ == "__main__":
    sys.exit(main())
