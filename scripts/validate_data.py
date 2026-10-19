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
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    from research_quality import COVERAGE_STATUSES, validate_research_quality
    from publication_policy import assess_market_publication, assess_report_publication
except ModuleNotFoundError:  # imported as scripts.validate_data in unit tests
    from scripts.research_quality import COVERAGE_STATUSES, validate_research_quality
    from scripts.publication_policy import assess_market_publication, assess_report_publication


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
    "research-evidence",
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


def validate_events(report: dict, result: ValidationResult) -> None:
    events = report.get("events")
    metadata = report.get("events_metadata")
    if not isinstance(events, list) or not isinstance(metadata, dict):
        result.error("report.events/events_metadata: 重要イベントと取得状態が必要です")
        return

    start = parse_iso_date(metadata.get("window_start"), "report.events_metadata.window_start", result)
    end = parse_iso_date(metadata.get("window_end"), "report.events_metadata.window_end", result)
    if start and end and (end - start).days not in range(7, 15):
        result.error("report.events_metadata: 表示期間は7〜14日間にしてください")

    seen: set[str] = set()
    invalid: list[str] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            invalid.append(str(index))
            continue
        event_id = str(event.get("id", "")).strip()
        if not event_id or event_id in seen:
            invalid.append(f"{index}.id")
        seen.add(event_id)
        try:
            starts_at = datetime.fromisoformat(str(event.get("start_at_jst", "")))
            if starts_at.utcoffset() is None:
                raise ValueError
            event_date = starts_at.date()
            if start and event_date < start or end and event_date > end:
                invalid.append(f"{index}.window")
        except ValueError:
            invalid.append(f"{index}.start_at_jst")
        for key in ("event", "jst_time", "forecast", "previous", "focus", "affected_markets", "importance", "source_name", "verified_on"):
            if not str(event.get(key, "")).strip():
                invalid.append(f"{index}.{key}")
        if "JST" not in str(event.get("jst_time", "")):
            invalid.append(f"{index}.jst_time")
        if not str(event.get("source_url", "")).startswith("https://"):
            invalid.append(f"{index}.source_url")

    expected_status = "取得済" if events else "該当材料なし"
    if metadata.get("status") != expected_status:
        invalid.append("metadata.status")
    if invalid:
        result.error("report.events: 期間・JST・出典・空欄の検証に失敗: " + ", ".join(invalid))
    else:
        result.ok(f"公式日程に基づく重要イベント（{len(events)}件、JST・7〜14日窓）")


def validate_relationships(data: dict[str, dict], result: ValidationResult) -> None:
    report = data["report"]
    market = data["market"]
    japan = data["japan-stocks"]

    validate_events(report, result)

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

    move = report.get("market_move_explanation")
    required_move_fields = (
        "title", "move", "trigger", "relative_resilience",
        "japan_impact", "confidence", "invalidation",
    )
    if not isinstance(move, dict):
        result.error("report.market_move_explanation: 大幅変動理由の説明が必要です")
    elif any(not str(move.get(key, "")).strip() for key in required_move_fields):
        result.error("report.market_move_explanation: 値動き・原因・波及・確度・反証条件が不足しています")
    elif not isinstance(move.get("transmission_chain"), list) or len(move["transmission_chain"]) < 3:
        result.error("report.market_move_explanation.transmission_chain: 3段階以上の因果経路が必要です")
    elif not isinstance(move.get("hit_hardest"), list) or not move["hit_hardest"]:
        result.error("report.market_move_explanation.hit_hardest: 影響が大きい市場の説明が必要です")
    elif any(not isinstance(item, dict) or not str(item.get("market", "")).strip() or not str(item.get("reason", "")).strip() for item in move["hit_hardest"]):
        result.error("report.market_move_explanation.hit_hardest: marketとreasonを持つ項目が必要です")
    else:
        result.ok("大幅変動理由（値動き→材料→伝達経路→日本株・反証）")

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

    story_items = [
        item
        for key in ("top_stories", "important_stories", "other_stories")
        for item in japan.get(key, [])
        if isinstance(item, dict)
    ]
    ticker_pattern = re.compile(r"^(?:\d{4}|\d{3}[A-Z])$")
    required_story_text = (
        "company", "ticker", "headline", "category", "fact", "announced_at",
        "timing", "market_pricing_status", "price_reaction", "importance",
        "confidence", "source_url", "analysis", "today_watch",
    )
    for index, item in enumerate(story_items):
        location = f"japan-stocks story[{index}]"
        for key in required_story_text:
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                result.error(f"{location}.{key}: 空でない文字列が必要です")
        ticker = str(item.get("ticker", "")).strip().upper()
        if not ticker_pattern.fullmatch(ticker):
            result.error(
                f"{location}.ticker: 個別上場会社の銘柄コードが必要です（{ticker or '空'}）"
            )
        source_url = str(item.get("source_url", ""))
        if not source_url.startswith("https://"):
            result.error(f"{location}.source_url: HTTPSの一次情報URLが必要です")
        if any(domain in source_url for domain in ("finance.yahoo.", "reuters.com")):
            result.error(f"{location}.source_url: 個別株ニュースは企業IR・TDnet等の一次情報を使用してください")

    review = japan.get("japan_quick_view", {}).get("individual_news_review", {})
    review_status = review.get("status")
    if review_status not in {"reviewed", "partial"}:
        result.error("japan_quick_view.individual_news_review.status: reviewed または partial が必要です")
    elif stories and review_status != "reviewed":
        result.error("個別株ニュースがある場合は reviewed が必要です")
    elif review.get("story_count") != stories:
        result.error("個別株ニュースの監査件数と実数が一致しません")
    elif not str(review.get("scope", "")).strip():
        result.error("個別株ニュースの確認範囲を明示してください")
    else:
        result.ok("個別株ニュースの一次情報・銘柄コード監査")

    expected_preview = [
        {
            "company": item.get("company"),
            "ticker": item.get("ticker"),
            "headline": item.get("headline"),
            "importance": item.get("importance"),
            "market_pricing_status": item.get("market_pricing_status"),
        }
        for item in japan.get("top_stories", [])[:3]
    ]
    if preview.get("top_stories") != expected_preview:
        result.error("report.jsonの個別株プレビューがjapan-stocks.jsonと一致しません")
    else:
        result.ok("個別株ニュースのトップページ連携")

    ratings = japan.get("analyst_rating_changes")
    if not isinstance(ratings, dict):
        result.error("japan-stocks.analyst_rating_changes: 毎日の調査状態が必要です")
    else:
        rating_status = ratings.get("coverage_status")
        if rating_status not in COVERAGE_STATUSES - {"未調査"}:
            result.error("japan-stocks.analyst_rating_changes.coverage_status: 未調査は公開不可です")
        elif rating_status != "取得済" and "変更なし" in str(ratings.get("headline", "")):
            result.error("アナリスト評価を網羅できない日に『変更なし』と断定できません")
        elif not isinstance(ratings.get("items"), list) or not isinstance(ratings.get("source_review"), list):
            result.error("アナリスト評価変更にはitemsとsource_reviewが必要です")
        elif not ratings["source_review"] or any(
            not isinstance(item, dict)
            or not str(item.get("name", "")).strip()
            or not str(item.get("url", "")).startswith("https://")
            or not str(item.get("coverage", "")).strip()
            for item in ratings["source_review"]
        ):
            result.error("アナリスト評価変更の確認元・URL・網羅範囲が必要です")
        else:
            result.ok("アナリスト評価変更の調査状態・非断定表示")

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
        try:
            from publication_observations import copper_is_included
        except ModuleNotFoundError:
            from scripts.publication_observations import copper_is_included
        if not copper_is_included(report):
            required_market_keys = tuple(key for key in required_market_keys if key != "copper")
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
                if isinstance(reason, str) and reason.strip():
                    result.warning(f"{key}: {value}を維持（{reason.strip()}）")
                else:
                    stale.append(f"{key}={value}")
        qualified = report.get("publication_policy", {}).get("status") == "QUALIFIED"
        if missing:
            message = "必須市場データがありません: " + ", ".join(missing)
            if qualified and report.get("data_quality", {}).get("missing"):
                result.warning(message + "（QUALIFIED注釈・結論除外を確認）")
            else:
                result.error(message)
        if stale:
            message = (
                "target_market_dateより古い市場データが残っています: " + ", ".join(stale)
                + "。休場・公表日差など正当な理由がある場合は、日次データ側で明示的な例外設計を追加してください"
            )
            if qualified and report.get("data_quality", {}).get("cautions"):
                result.warning(message + "（QUALIFIED注釈・結論除外を確認）")
            else:
                result.error(message)
        if not missing and not stale:
            result.ok("必須市場データのtarget_market_date整合性")

    curve = market.get("derived", {}).get("us_2s10s", {})
    us2y = market.get("markets", {}).get("us2y", {})
    us10y = market.get("markets", {}).get("us10y", {})
    if curve.get("status") == "計算成功":
        curve_date = curve.get("market_date")
        if not curve_date or curve_date != us2y.get("market_date") or curve_date != us10y.get("market_date"):
            result.error("market.derived.us_2s10s: 2年・10年の同一FRED公表日だけで算出してください")
        elif not all(isinstance(curve.get(key), (int, float)) for key in ("value_bp", "previous_bp", "change_bp")):
            result.error("market.derived.us_2s10s: スプレッド値が不足しています")
        else:
            result.ok(f"米2年・10年金利差（FRED同日 {curve_date}）")
    elif not str(curve.get("note", "")).strip():
        result.error("market.derived.us_2s10s: 算出不能理由が必要です")


def validate_market_context(data: dict[str, dict], result: ValidationResult) -> None:
    context = data["market-context"]
    glossary = data["glossary"]

    start = parse_iso_date(context.get("period_start"), "market-context.period_start", result)
    end = parse_iso_date(context.get("period_end"), "market-context.period_end", result)
    if start and end:
        if start > end:
            result.error("market-context: period_startがperiod_endより後です")
        elif (end - start).days < 180:
            result.error("market-context: 半年程度の市場の流れを保持するため180日以上の期間が必要です")
        else:
            result.ok("今のマーケット対象期間")

    report_date = parse_iso_date(
        context.get("report_date"), "market-context.report_date", result
    )
    freshness = context.get("freshness", {})
    if (
        freshness.get("status") != "current"
        or freshness.get("latest_report_date") != context.get("report_date")
        or not isinstance(freshness.get("source_report_count"), int)
        or freshness.get("source_report_count", 0) < 2
    ):
        result.error("market-context.freshness: 当日レポートと複数履歴への接続が必要です")
    elif report_date and end and (report_date - end).days > 1:
        result.error("market-context: 最新テーマがレポート日より2日以上古いです")
    else:
        result.ok("今のマーケット鮮度（当日レポート・複数履歴）")

    themes = context.get("themes")
    source_ids = {
        item.get("id") for item in context.get("sources", []) if isinstance(item, dict)
    }
    if not isinstance(themes, list) or not 3 <= len(themes) <= 5:
        result.error("market-context.themes: 主要テーマは3〜5件必要です")
    else:
        stage_dates = []
        invalid = []
        for index, item in enumerate(themes):
            if not isinstance(item, dict):
                invalid.append(str(index))
                continue
            for key in ("initial_view", "new_fact", "market_reaction"):
                stage = item.get(key, {})
                parsed = parse_iso_date(
                    stage.get("date"), f"market-context.themes[{index}].{key}.date", result
                )
                if parsed:
                    stage_dates.append(parsed)
                    if start and parsed < start or end and parsed > end:
                        result.error(
                            f"market-context.themes[{index}].{key}.date: 対象期間外です"
                        )
                        invalid.append(f"{index}.{key}:period")
                if not str(stage.get("text", "")).strip():
                    invalid.append(f"{index}.{key}:text")
            timeline = item.get("timeline")
            if not isinstance(timeline, list) or len(timeline) < 3:
                invalid.append(f"{index}.timeline")
            else:
                timeline_dates = []
                for event_index, event in enumerate(timeline):
                    if not isinstance(event, dict):
                        invalid.append(f"{index}.timeline[{event_index}]")
                        continue
                    parsed = parse_iso_date(
                        event.get("date"),
                        f"market-context.themes[{index}].timeline[{event_index}].date",
                        result,
                    )
                    if parsed:
                        timeline_dates.append(parsed)
                        if start and parsed < start or end and parsed > end:
                            invalid.append(f"{index}.timeline[{event_index}]:period")
                    for key in ("title", "fact", "market_impact"):
                        if not str(event.get(key, "")).strip():
                            invalid.append(f"{index}.timeline[{event_index}].{key}")
                    if not event.get("source_ids") or any(
                        source_id not in source_ids for source_id in event.get("source_ids", [])
                    ):
                        invalid.append(f"{index}.timeline[{event_index}].source_ids")
                if timeline_dates != sorted(timeline_dates):
                    invalid.append(f"{index}.timeline:chronology")
            for key in ("theme", "current_view", "japan_impact", "counter_evidence"):
                if not str(item.get(key, "")).strip():
                    invalid.append(f"{index}.{key}")
            if not item.get("source_ids") or any(
                source_id not in source_ids for source_id in item.get("source_ids", [])
            ):
                invalid.append(f"{index}.source_ids")
        if invalid:
            result.error("market-context.themes: 認識変化・反証・出典の不足: " + ", ".join(invalid))
        elif len(set(stage_dates)) < 3:
            result.error("market-context.themes: 3日以上の変化が必要です")
        else:
            result.ok("今のマーケット主要テーマ（認識→事実→反応→現在・反証）")

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
    report = data["report"]
    alignment = japan_market.get("data_quality", {}).get("date_alignment", {})
    expected_target = report.get("target_market_date")
    if alignment.get("report_target_market_date") != expected_target:
        result.error(
            "japan-market.data_quality.date_alignment.report_target_market_date: "
            "report.jsonのtarget_market_dateと一致させてください"
        )
    elif alignment.get("aligned") and any(
        alignment.get(key) != alignment.get("expected_market_date")
        for key in ("sector_market_date", "stock_market_date")
    ):
        result.error(
            "japan-market.data_quality.date_alignment: "
            "整合済みの業種・銘柄データは日本株の取得対象日と一致させてください"
        )
    else:
        result.ok("日本株品質メタデータとレポート対象日の一致")
    market_view = japan_market.get("market_regime", {})
    serialized_view = json.dumps(market_view, ensure_ascii=False)
    if any(term in serialized_view for term in ("Breadth", "上昇・下落の広がり", "主要監視34銘柄の内訳")):
        result.error("japan-market.market_regime: 34銘柄を市場全体の広がり評価に使用しないでください")
    elif len(market_view.get("scoreboard", [])) != 2:
        result.error("japan-market.market_regime: 冒頭は日経平均とTOPIXの2指標に限定してください")
    else:
        result.ok("今日の市場観は主要2指数に限定（34銘柄Breadthなし）")

    dimensions = market_view.get("dimensions", [])
    expected_axes = {"大型株/小型株", "グロース/バリュー（代理）", "景気敏感/ディフェンシブ", "半導体/市場全体", "金融/市場全体"}
    if len(dimensions) != 5 or {item.get("axis") for item in dimensions if isinstance(item, dict)} != expected_axes:
        result.error("japan-market.market_regime.dimensions: 5軸の詳細評価が必要です")
    elif any(not str(item.get("status", "")).strip() or not str(item.get("reason", "")).strip() for item in dimensions):
        result.error("japan-market.market_regime.dimensions: 各軸に評価と根拠が必要です")
    else:
        result.ok("市場レジームの詳細5軸")

    rotation = japan_market.get("rotation_read", {})
    if rotation.get("label") != "どちらが強い？":
        result.error("japan-market.rotation_read: 一般読者に分かる名称が必要です")
    elif "投資主体別" not in str(rotation.get("note", "")):
        result.error("japan-market.rotation_read: 投資主体別売買ではない旨が必要です")
    else:
        result.ok("比較結果と推定範囲の明示")

    japan_date = parse_iso_date(japan_market.get("market_date"), "japan-market.market_date", result)
    for index, driver in enumerate(japan_market.get("key_drivers", [])):
        driver_date = driver.get("market_date") if isinstance(driver, dict) else None
        parsed = parse_iso_date(driver_date, f"japan-market.key_drivers[{index}].market_date", result) if driver_date else None
        if parsed and japan_date and parsed > japan_date and driver.get("pricing_status") != "日本株現物に未反映":
            result.error(f"japan-market.key_drivers[{index}]: 日本株市場日より新しい材料は未反映と明示してください")
    drivers = japan_market.get("key_drivers", [])
    names = {item.get("driver") for item in drivers if isinstance(item, dict)}
    if 3 <= len(drivers) <= 5 and not ({"銅", "金"} <= names) and all("selection_factors" in item and "change_condition" in item for item in drivers):
        result.ok("日本株主要材料は波及範囲・重要度・値動き・織り込みを明示して3〜5件選定")
    else:
        result.error("japan-market.key_drivers: 影響度順で最大4件とし、銅・金を同時に固定表示しないでください")

    qualities = japan_market.get("sector_quality", [])
    if qualities and all(set((item.get("axes") or {}).keys()) == {"momentum", "activity", "persistence"} and isinstance(item.get("relative_today_pct"), (int, float)) for item in qualities):
        result.ok("セクター3軸評価（TOPIX比・出来高・5日比較）")
    else:
        result.error("japan-market.sector_quality: 監視2銘柄ベースの広がりを除き、業種ETFの3軸だけで評価してください")

    review = japan_market.get("scenario_review", {})
    review_fields = {"previous_condition", "condition_result", "market_reaction", "unexpected_gap", "gap_reason", "revision"}
    if "○×" in str(review) or review.get("title") != "昨日のシナリオ検証 → 今日への修正" or not review_fields <= set(review):
        result.error("japan-market.scenario_review: 予想採点ではなく今日への修正として表示してください")
    else:
        result.ok("昨日のシナリオ検証から今日への修正")
    if not isinstance(review.get("checks"), list) or not review["checks"]:
        result.error("japan-market.scenario_review.checks: 検証待ちを含め、確認点を空欄にしないでください")

    state = japan_market.get("data_state", {})
    if state.get("kind") not in {"normal", "holiday", "data_error"}:
        result.error("japan-market.data_state: 休場とデータ異常を区別してください")
    else:
        result.ok("休場・通常日・データ異常の区別")

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


def run(root: Path = ROOT, scope: str = "report") -> ValidationResult:
    result = ValidationResult()
    if scope == "news":
        try:
            from validate_news import validate, validate_collection
        except ModuleNotFoundError:
            from scripts.validate_news import validate, validate_collection
        try:
            news = load_json(root / "data/news.json")
            validate_schema(news, load_json(root / "schemas/news.schema.json"), "news", result)
            for message in validate(news):
                result.error(message)
            for message in validate_collection(root):
                result.error(message)
            for path in sorted((root / "data/history").glob("*/news.json")):
                validate_schema(load_json(path), load_json(root / "schemas/news.schema.json"), str(path.relative_to(root)), result)
        except (OSError, ValueError) as error:
            result.error(f"news: {error}")
        if not result.errors:
            result.ok("確認済みニュースのみ検証。市場・レポートの公開判定は変更しない")
        return result
    data: dict[str, dict] = {}
    names = ("market", "status") if scope in {"market", "market-publication"} else DATA_NAMES
    for name in names:
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

    if scope in {"market", "market-publication"} and "market" in data:
        # A new price snapshot must not depend on yesterday's narrative report.
        # Missing observations remain explicit; never mark an empty update successful.
        markets = data["market"].get("markets", {})
        assessment = assess_market_publication(data["market"])
        for message in assessment.errors:
            result.error(message)
        for message in assessment.warnings:
            result.warning(message)
        if assessment.status != "BLOCK":
            result.ok(f"市場取得の独立公開判定（{assessment.status}）")
    elif all(name in data for name in DATA_NAMES):
        validate_relationships(data, result)
        validate_market_context(data, result)
        validate_japan_investor_view(data, result)
        quality_errors = validate_research_quality(
            data["research-evidence"], data["report"], data["japan-stocks"]
        )
        if quality_errors:
            for message in quality_errors:
                result.error(message)
        else:
            result.ok("Research & Analysis Quality Gate（最終9項目）")
    if scope in {"publish", "publish-report"}:
        try:
            from publication_observations import validate_observations, copper_is_included
        except ModuleNotFoundError:
            from scripts.publication_observations import validate_observations, copper_is_included
        observation_errors = validate_observations(
            data.get('market', {}),
            include_copper=copper_is_included(data.get('report', {})),
        )
        qualified = data.get("report", {}).get("publication_policy", {}).get("status") == "QUALIFIED"
        for message in observation_errors:
            if qualified and data.get("report", {}).get("data_quality", {}).get("missing"):
                result.warning(message + "（公開対象の結論から除外）")
            else:
                result.error(message)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
        for name in ("report", "japan-stocks", "research-evidence"):
            if data.get(name, {}).get("report_date") != today:
                result.error(f"{name}: 本日版ではありません（公開ゲート）")
        assessment = assess_report_publication(
            data.get("research-evidence", {}),
            data.get("report", {}),
            data.get("japan-stocks", {}),
        )
        for message in assessment.errors:
            result.error(message)
        for message in assessment.warnings:
            result.warning(message)
        if assessment.status != "BLOCK":
            result.ok(f"総合レポート公開判定（{assessment.status}）")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--scope",
        choices=("report", "market", "market-publication", "news", "publish", "publish-report"),
        default="report",
    )
    args = parser.parse_args()
    result = run(args.root.resolve(), args.scope)
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
