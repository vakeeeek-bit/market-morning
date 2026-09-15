#!/usr/bin/env python3
"""Validate Market Morning data before and after publication."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCHEMA_DIR = ROOT / "schemas"
DATA_NAMES = ("report", "market", "japan-stocks", "japan-market", "status")


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def ok(self, message: str) -> None:
        self.checks.append(message)


def reject_non_standard_number(value: str) -> None:
    raise ValueError(f"JSONで使用できない数値です: {value}")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file, parse_constant=reject_non_standard_number)


def is_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def validate_schema(value: Any, schema: dict, location: str, result: ValidationResult) -> None:
    expected = schema.get("type")
    expected_types = expected if isinstance(expected, list) else [expected] if expected else []
    if expected_types and not any(is_type(value, item) for item in expected_types):
        result.error(f"{location}: 型が不正です（期待: {expected_types}）")
        return

    if isinstance(value, str) and schema.get("pattern"):
        if not re.fullmatch(schema["pattern"], value):
            result.error(f"{location}: 形式が不正です（{value}）")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                result.error(f"{location}.{key}: 必須項目がありません")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                validate_schema(child, properties[key], f"{location}.{key}", result)

    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, child in enumerate(value):
            validate_schema(child, schema["items"], f"{location}[{index}]", result)


def parse_iso_date(value: Any, label: str, result: ValidationResult) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        result.error(f"{label}: 日付を読み取れません（{value}）")
        return None


def validate_relationships(data: dict[str, dict], result: ValidationResult) -> None:
    report = data["report"]
    market = data["market"]
    japan = data["japan-stocks"]

    top_news = report.get("quick_view", {}).get("top_news")
    if not isinstance(top_news, list) or len(top_news) != 3:
        result.error("report.quick_view.top_news: オブジェクト形式で3件必要です")
    elif not all(
        isinstance(item, dict) and isinstance(item.get("title"), str) and item["title"].strip()
        for item in top_news
    ):
        result.error("report.quick_view.top_news: 各項目に空でないtitleが必要です")
    else:
        result.ok("QUICK VIEW重要ニュースTOP3")

    preview = report.get("japan_equities_preview", {})
    report_top5 = preview.get("top_materials")
    japan_top5 = japan.get("japan_quick_view", {}).get("top_materials")
    if not isinstance(report_top5, list) or len(report_top5) != 5:
        result.error("report.japan_equities_preview.top_materials: 5件必要です")
    elif report_top5 != japan_top5:
        result.error("日本株重要材料TOP5がreport.jsonとjapan-stocks.jsonで一致しません")
    else:
        result.ok("日本株重要材料TOP5の完全一致")

    stories = sum(
        len(japan.get(key, []))
        for key in ("top_stories", "important_stories", "other_stories")
    )
    declared = preview.get("total_story_count")
    if declared != stories:
        result.error(f"日本株詳細件数が一致しません（表示: {declared}、実数: {stories}）")
    else:
        result.ok(f"日本株詳細件数（{stories}件）")

    if report.get("report_date") != japan.get("report_date"):
        result.error("report.jsonとjapan-stocks.jsonのreport_dateが一致しません")
    elif report.get("target_market_date") != japan.get("target_market_date"):
        result.error("report.jsonとjapan-stocks.jsonのtarget_market_dateが一致しません")
    else:
        result.ok("レポートと日本株詳細の日付一致")

    report_date = parse_iso_date(report.get("report_date"), "report.report_date", result)
    market_date = parse_iso_date(market.get("updated_at"), "market.updated_at", result)
    if report_date and market_date:
        difference = (market_date - report_date).days
        if difference != 0:
            direction = "市場データが新しい" if difference > 0 else "レポートが新しい"
            result.warning(
                f"report.jsonとmarket.jsonの基準日が{abs(difference)}日ずれています"
                f"（{direction}）"
            )
        else:
            result.ok("レポート日と市場データ更新日の一致")


def write_summary(result: ValidationResult) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    status = "PASS" if not result.errors else "FAIL"
    lines = [f"## Market Morning Data Validation: {status}", ""]
    lines += [f"- ✅ {message}" for message in result.checks]
    lines += [f"- ⚠️ {message}" for message in result.warnings]
    lines += [f"- ❌ {message}" for message in result.errors]
    Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(root: Path = ROOT) -> ValidationResult:
    result = ValidationResult()
    data: dict[str, dict] = {}
    for name in DATA_NAMES:
        data_path = root / "data" / f"{name}.json"
        schema_path = root / "schemas" / f"{name}.schema.json"
        try:
            value = load_json(data_path)
            schema = load_json(schema_path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            result.error(f"{name}: JSON読込エラー（{error}）")
            continue
        if not isinstance(value, dict) or not isinstance(schema, dict):
            result.error(f"{name}: 最上位はオブジェクトである必要があります")
            continue
        validate_schema(value, schema, name, result)
        data[name] = value
        result.ok(f"{name}.jsonのスキーマ検証")

    if all(name in data for name in DATA_NAMES):
        validate_relationships(data, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = run(args.root.resolve())
    for message in result.checks:
        print(f"OK: {message}")
    for message in result.warnings:
        print(f"::warning::{message}")
    for message in result.errors:
        print(f"::error::{message}")
    write_summary(result)
    print(
        f"Validation finished: {len(result.errors)} error(s), "
        f"{len(result.warnings)} warning(s)"
    )
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
