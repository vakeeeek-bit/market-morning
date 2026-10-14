#!/usr/bin/env python3
"""Build reader-facing theme transitions from audited reports and news history."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HISTORY = DATA / "history"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def recent_history(report_day: date, days: int = 14) -> tuple[list[dict], dict[str, dict]]:
    reports: list[dict] = []
    articles: dict[str, dict] = {}
    cutoff = report_day - timedelta(days=days)
    for folder in sorted(HISTORY.iterdir() if HISTORY.exists() else []):
        if not folder.is_dir():
            continue
        try:
            folder_day = date.fromisoformat(folder.name)
        except ValueError:
            continue
        if not cutoff <= folder_day <= report_day:
            continue
        report_path = folder / "report.json"
        news_path = folder / "news.json"
        if report_path.exists():
            reports.append(load_json(report_path))
        if news_path.exists():
            for item in load_json(news_path).get("articles", []):
                if item.get("id"):
                    articles[item["id"]] = item
    return reports, articles


def build_context() -> dict:
    report = load_json(DATA / "report.json")
    news = load_json(DATA / "news.json")
    report_day = date.fromisoformat(report["report_date"])
    history_reports, articles = recent_history(report_day)
    for item in news.get("articles", []):
        if item.get("id"):
            articles[item["id"]] = item
    for source_id, item in report.get("market_context_sources", {}).items():
        articles[source_id] = item

    themes = report.get("market_context_themes")
    if not isinstance(themes, list) or not 3 <= len(themes) <= 5:
        raise ValueError("report.market_context_themes requires 3-5 audited themes")
    if len(history_reports) < 2:
        raise ValueError("market context requires at least two recent report snapshots")

    rendered_themes = []
    used_sources: dict[str, dict] = {}
    all_dates: list[date] = []
    for index, theme in enumerate(themes):
        source_ids = theme.get("source_ids", [])
        if not source_ids:
            raise ValueError(f"market_context_themes[{index}] has no source_ids")
        missing = [source_id for source_id in source_ids if source_id not in articles]
        if missing:
            raise ValueError(f"market_context_themes[{index}] unknown sources: {', '.join(missing)}")

        for key in ("initial_view", "new_fact", "market_reaction"):
            stage = theme.get(key)
            if not isinstance(stage, dict) or not stage.get("date") or not stage.get("text"):
                raise ValueError(f"market_context_themes[{index}].{key} is incomplete")
            all_dates.append(date.fromisoformat(stage["date"]))
        for key in ("theme", "current_view", "japan_impact", "counter_evidence"):
            if not str(theme.get(key, "")).strip():
                raise ValueError(f"market_context_themes[{index}].{key} is empty")

        rendered_themes.append({
            "theme": theme["theme"],
            "initial_view": theme["initial_view"],
            "new_fact": theme["new_fact"],
            "market_reaction": theme["market_reaction"],
            "current_view": theme["current_view"],
            "japan_impact": theme["japan_impact"],
            "counter_evidence": theme["counter_evidence"],
            "source_ids": source_ids,
        })
        for source_id in source_ids:
            used_sources[source_id] = articles[source_id]

    period_start = min(all_dates).isoformat()
    period_end = max(all_dates).isoformat()
    if (report_day - date.fromisoformat(period_end)).days > 1:
        raise ValueError("market context is stale relative to the current report")

    sources = [
        {
            "id": source_id,
            "title": item["title"],
            "publisher": item["publisher"],
            "published_at": item["published_date"],
            "url": item["source_url"],
        }
        for source_id, item in used_sources.items()
    ]
    monitoring = report.get("monitoring_points", [])
    return {
        "version": 2,
        "updated_at": report["updated_at"],
        "report_date": report["report_date"],
        "period_start": period_start,
        "period_end": period_end,
        "freshness": {
            "status": "current",
            "latest_report_date": report["report_date"],
            "source_report_count": len({
                *(item.get("report_date") for item in history_reports if item.get("report_date")),
                report["report_date"],
            }),
            "note": "当日レポートと直近の履歴・確認済みニュースから更新",
        },
        "headline": "市場の見方がどう変わったかを4つのテーマで確認",
        "summary": "主要テーマごとに、当初の認識、新しい事実、実際の市場反応、現在の認識を分けています。確認できない変化は作らず、反証も併記します。",
        "themes": rendered_themes,
        "scenario_change_conditions": [
            {"condition": item.get("target", "確認条件"), "meaning": item.get("view_change_condition", "")}
            for item in monitoring[:5]
            if item.get("view_change_condition")
        ],
        "sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = DATA / "market-context.json"
    rendered = json.dumps(build_context(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if path.read_text(encoding="utf-8") != rendered:
            print("data/market-context.json is stale; run scripts/update_market_context.py")
            return 1
        print("data/market-context.json is current")
        return 0
    path.write_text(rendered, encoding="utf-8")
    print("updated data/market-context.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
