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
DATA_NAMES = (
    "report",
    "market",
    "japan-stocks",
    "japan-market",
    "status",
    "market-context",
    "glossary",
)


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


    target = parse_iso_date(report.get("target_market_date"), "report.target_market_date", result)
    if target:
        required_market_keys = (
            "sp500", "nasdaq", "nasdaq100", "dow", "russell2000", "sox",
            "nikkei225", "topix", "dxy", "usdjpy", "eurusd", "us10y", "us2y",
            "vix", "gold", "silver", "copper", "wti", "brent", "btc", "eth",
        )
        stale = []
        missing = []
        for key in required_market_keys:
            item = market.get("markets", {}).get(key)
            if not isinstance(item, dict):
                missing.append(key)
                continue
            value = item.get("market_date")
            parsed = parse_iso_date(value, f"market.markets.{key}.market_date", result)
            if parsed and parsed < target:
                reason = item.get("stale_reason")
                status = str(item.get("status", ""))
                if isinstance(reason, str) and reason.strip() and status != "取得成功":
                    result.warning(f"{key}: {value}を維持（{reason.strip()}）")
                else:
                    stale.append(f"{key}={value}")
        if missing:
            result.error("必須市場データがありません: " + ", ".join(missing))
        if stale:
            result.error(
                "target_market_dateより古い市場データが残っています: " + ", ".join(stale)
                + "。休場・公表日差など正当な理由がある場合は、日次データ側で明示的な例外設計を追加してください"
            )
        if not missing and not stale:
            result.ok("必須市場データのtarget_market_date整合性")


def validate_market_context(data: dict[str, dict], result: ValidationResult) -> None:
    context = data["market-context"]
    glossary = data["glossary"]

    start = parse_iso_date(context.get("period_start"), "market-context.period_start", result)
    end = parse_iso_date(context.get("period_end"), "market-context.period_end", result)
    if start and end:
        if start > end:
            result.error("market-context: period_startがperiod_endより後です")
        elif (end - start).days < 60:
            result.error("market-context: 対象期間は原則2か月以上必要です")
        else:
            result.ok("今のマーケット対象期間")

    timeline = context.get("timeline")
    if not isinstance(timeline, list) or not 3 <= len(timeline) <= 6:
        result.error("market-context.timeline: 重要転換点は3〜6件必要です")
    else:
        dates = []
        for index, item in enumerate(timeline):
            item_date = parse_iso_date(
                item.get("date") if isinstance(item, dict) else None,
                f"market-context.timeline[{index}].date",
                result,
            )
            if item_date:
                dates.append(item_date)
                if start and item_date < start or end and item_date > end:
                    result.error(
                        f"market-context.timeline[{index}]: 対象期間外の日付です"
                    )
        if dates and dates != sorted(dates):
            result.error("market-context.timeline: 日付順に並んでいません")
        elif len(dates) == len(timeline):
            result.ok("今のマーケット時系列（3〜6件・日付順）")

    evidence_types = {"直接影響", "間接影響", "可能性"}
    life_impacts = context.get("daily_life_impacts")
    if not isinstance(life_impacts, list) or not life_impacts:
        result.error("market-context.daily_life_impacts: 1件以上必要です")
    else:
        invalid = [
            str(item.get("evidence_type"))
            for item in life_impacts
            if not isinstance(item, dict) or item.get("evidence_type") not in evidence_types
        ]
        if invalid:
            result.error("market-context.daily_life_impacts: 影響区分が不正です")
        else:
            result.ok("暮らしへの影響区分（直接・間接・可能性）")

    sources = context.get("sources")
    if not isinstance(sources, list) or len(sources) < 3:
        result.error("market-context.sources: 3件以上必要です")
    elif any(
        not isinstance(item, dict)
        or not str(item.get("url", "")).startswith("https://")
        or not str(item.get("title", "")).strip()
        for item in sources
    ):
        result.error("market-context.sources: titleとhttps URLが必要です")
    else:
        result.ok("今のマーケット出典")

    terms = glossary.get("terms")
    if not isinstance(terms, list) or len(terms) < 20:
        result.error("glossary.terms: 初期辞書は20語以上必要です")
    else:
        names = [str(item.get("term", "")).strip() for item in terms if isinstance(item, dict)]
        if len(names) != len(terms) or any(not name for name in names):
            result.error("glossary.terms: 空の用語があります")
        elif len(names) != len(set(names)):
            result.error("glossary.terms: 用語が重複しています")
        else:
            result.ok(f"初心者向け用語辞書（{len(terms)}語）")


def validate_japan_investor_view(data: dict[str, dict], result: ValidationResult) -> None:
    japan_market = data["japan-market"]
    dimensions = japan_market.get("market_regime", {}).get("dimensions", [])
    by_axis = {item.get("axis"): item for item in dimensions if isinstance(item, dict)}
    for axis in ("Growth / Value", "大型株 / 小型株", "半導体"):
        item = by_axis.get(axis)
        if not item or item.get("status") != "unavailable":
            result.error(f"japan-market.market_regime: {axis}は現行データでは判定対象外であることを明示してください")
    if by_axis.get("市場Breadth", {}).get("status") != "observed":
        result.error("japan-market.market_regime: 市場Breadthは実測として区別してください")
    else:
        result.ok("日本株レジームの実測・推定・判定対象外の区別")

    rotation = japan_market.get("rotation_read", {})
    if rotation.get("label") != "値動きから見たローテーション（推定）":
        result.error("japan-market.rotation_read: 実フローと誤認しない名称が必要です")
    elif "投資主体別" not in str(rotation.get("note", "")):
        result.error("japan-market.rotation_read: 投資主体別売買ではない旨が必要です")
    else:
        result.ok("ローテーション推定の明示")

    japan_date = parse_iso_date(japan_market.get("market_date"), "japan-market.market_date", result)
    for index, driver in enumerate(japan_market.get("key_drivers", [])):
        driver_date = driver.get("market_date") if isinstance(driver, dict) else None
        parsed = parse_iso_date(driver_date, f"japan-market.key_drivers[{index}].market_date", result) if driver_date else None
        if parsed and japan_date and parsed > japan_date and driver.get("pricing_status") != "日本株現物に未反映":
            result.error(f"japan-market.key_drivers[{index}]: 日本株市場日より新しい材料は未反映と明示してください")
    if len(japan_market.get("key_drivers", [])) == 5:
        result.ok("日本株主要ドライバー5系列")
    else:
        result.error("japan-market.key_drivers: USD/JPY・米金利・SOX・Copper・原油の5系列が必要です")

    if japan_market.get("methodology", {}).get("implemented_tier") != 1:
        result.error("japan-market.methodology: 今回の実装は既存データのみのTier 1に限定してください")
    else:
        result.ok("追加AI/API負荷なし（Tier 1）")



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
        validate_market_context(data, result)
        validate_japan_investor_view(data, result)
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
