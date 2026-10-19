#!/usr/bin/env python3
"""Publish a rolling, verified macro-event window into report.json.

The source catalogue contains only dates checked against official calendars.
This job filters it every morning, so expired entries cannot remain visible.
Forecasts and previous values are never inferred.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "economic-events.json"
REPORT_PATH = ROOT / "data" / "report.json"
JST = ZoneInfo("Asia/Tokyo")
REQUIRED_FIELDS = {
    "id", "event", "start_at_jst", "jst_time", "forecast", "previous",
    "focus", "affected_markets", "importance", "source_url", "source_name",
    "verified_on",
}


def parse_jst(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"timezone付き日時が必要です: {value}")
    return parsed.astimezone(JST)


def select_events(catalog: dict, now: datetime) -> list[dict]:
    window_days = int(catalog.get("window_days", 14))
    end = now + timedelta(days=window_days)
    selected = []
    seen = set()
    for raw in catalog.get("events", []):
        missing = REQUIRED_FIELDS - set(raw)
        if missing:
            raise ValueError(f"イベント{raw.get('id', 'unknown')}の必須項目不足: {sorted(missing)}")
        if raw["id"] in seen:
            raise ValueError(f"イベントID重複: {raw['id']}")
        seen.add(raw["id"])
        start = parse_jst(raw["start_at_jst"])
        end_at = parse_jst(raw.get("end_at_jst", raw["start_at_jst"]))
        if end_at < now or start > end:
            continue
        item = dict(raw)
        item["forecast"] = item.get("forecast") or "未確認"
        item["previous"] = item.get("previous") or "未確認"
        selected.append(item)
    return sorted(selected, key=lambda item: parse_jst(item["start_at_jst"]))


def update_report(report: dict, catalog: dict, now: datetime) -> dict:
    events = select_events(catalog, now)
    report["events"] = events
    report["events_metadata"] = {
        "status": "取得済" if events else "該当材料なし",
        "updated_at": now.isoformat(timespec="seconds"),
        "window_start": now.date().isoformat(),
        "window_end": (now + timedelta(days=int(catalog.get("window_days", 14)))).date().isoformat(),
        "timezone": "Asia/Tokyo",
        "source_policy": "公式日程で確認済みのイベントのみ。予想・前回値は未確認を推測しない",
        "coverage_note": catalog.get("coverage_note", ""),
        "catalog_version": catalog.get("version", "unknown"),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", help="テスト用ISO日時（JSTへ変換）")
    parser.add_argument("--check", action="store_true", help="書き込まず検証")
    args = parser.parse_args()
    now = parse_jst(args.now) if args.now else datetime.now(JST)
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    updated = update_report(report, catalog, now)
    if args.check:
        print(f"Upcoming events: PASS ({len(updated['events'])}件)")
        return
    REPORT_PATH.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"今後{catalog.get('window_days', 14)}日間の重要イベントを{len(updated['events'])}件更新しました")


if __name__ == "__main__":
    main()
