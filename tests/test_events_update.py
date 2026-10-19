import json
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.update_events import select_events, update_report


ROOT = Path(__file__).resolve().parents[1]


class EventUpdateTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / "data" / "economic-events.json").read_text(encoding="utf-8"))
        self.now = datetime(2026, 10, 19, 12, 34, tzinfo=ZoneInfo("Asia/Tokyo"))

    def test_selects_verified_events_only_inside_fourteen_day_window(self):
        events = select_events(self.catalog, self.now)
        self.assertEqual(6, len(events))
        self.assertTrue(all(item["source_url"].startswith("https://") for item in events))
        self.assertTrue(all("JST" in item["jst_time"] for item in events))
        self.assertNotIn("ism-manufacturing-2026-10", {item["id"] for item in events})

    def test_expired_events_are_removed_and_future_catalog_entries_enter_window(self):
        events = select_events(
            self.catalog,
            datetime(2026, 10, 31, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
        )
        ids = {item["id"] for item in events}
        self.assertNotIn("boj-mpm-2026-10", ids)
        self.assertIn("ism-manufacturing-2026-10", ids)
        self.assertIn("us-employment-2026-10", ids)

    def test_missing_values_remain_explicit_not_guessed(self):
        report = update_report({}, self.catalog, self.now)
        self.assertTrue(all(item["forecast"] for item in report["events"]))
        self.assertTrue(any(item["forecast"] == "未確認" for item in report["events"]))
        self.assertEqual("取得済", report["events_metadata"]["status"])


if __name__ == "__main__":
    unittest.main()
