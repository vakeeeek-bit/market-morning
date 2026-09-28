from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CompanyNewsArchiveTests(unittest.TestCase):
    def test_recent_reports_use_company_disclosures_not_sector_proxies(self):
        ticker_pattern = re.compile(r"^(?:\d{4}|\d{3}[A-Z])$")
        for report_date in ("2026-09-25", "2026-09-26", "2026-09-27", "2026-09-28"):
            folder = ROOT / "data" / "history" / report_date
            japan = json.loads((folder / "japan-stocks.json").read_text(encoding="utf-8"))
            report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
            stories = [
                item
                for key in ("top_stories", "important_stories", "other_stories")
                for item in japan[key]
            ]
            self.assertGreater(len(stories), 0, report_date)
            self.assertEqual(len(stories), japan["japan_quick_view"]["individual_news_review"]["story_count"])
            self.assertEqual(len(stories), report["japan_equities_preview"]["total_story_count"])
            for item in stories:
                self.assertRegex(item["ticker"], ticker_pattern, f"{report_date}: {item['company']}")
                self.assertTrue(item["source_url"].startswith("https://www.release.tdnet.info/"))

    def test_dates_without_saved_reports_are_not_fabricated(self):
        for report_date in ("2026-09-22", "2026-09-23", "2026-09-24"):
            folder = ROOT / "data" / "history" / report_date
            self.assertFalse((folder / "report.json").exists())
            self.assertFalse((folder / "japan-stocks.json").exists())


if __name__ == "__main__":
    unittest.main()
