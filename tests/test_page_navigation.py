import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PageNavigationTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_both_pages_have_world_and_japan_navigation(self):
        for page in ("index.html", "japan-stocks.html"):
            source = self.read(page)
            self.assertIn('aria-label="レポート画面の切り替え"', source)
            self.assertIn("🌐 世界市場", source)
            self.assertIn("🇯🇵 日本株", source)

    def test_exactly_one_active_page_per_document(self):
        for page in ("index.html", "japan-stocks.html"):
            source = self.read(page)
            active_links = re.findall(
                r'<a\b[^>]*aria-current="page"[^>]*>', source, re.IGNORECASE
            )
            self.assertEqual(len(active_links), 1)

    def test_japan_page_has_history_navigation(self):
        source = self.read("japan-stocks.html")
        for element_id in ("prev-day", "history-date", "next-day", "latest-day"):
            self.assertIn(f'id="{element_id}"', source)
        self.assertIn("has_japan_stocks", source)

    def test_selected_date_is_carried_between_pages(self):
        world = self.read("index.html")
        japan = self.read("japan-stocks.html")
        self.assertIn("japan-page-link", world)
        self.assertIn("world-page-link", japan)
        self.assertIn("encodeURIComponent(selectedHistoryDate)", world)
        self.assertIn("encodeURIComponent(selectedHistoryDate)", japan)

    def test_japan_detail_is_not_duplicated_on_world_page(self):
        world = self.read("index.html")
        japan = self.read("japan-stocks.html")
        self.assertNotIn('id="japan-equities-preview"', world)
        self.assertIn('id="top-materials"', japan)
        self.assertIn('id="story-sections"', japan)

    def test_latest_view_warns_when_market_and_report_dates_differ(self):
        world = self.read("index.html")
        self.assertIn('id="freshness-warning"', world)
        self.assertIn("function updateDataFreshness()", world)
        self.assertIn("新しいレポートは品質確認中", world)
        self.assertIn("AIレポート：${reportLabel}（更新待ち）", world)


if __name__ == "__main__":
    unittest.main()
