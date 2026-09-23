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
        self.assertNotIn('id="japan-equities-section"', world)
        self.assertIn('id="top-materials"', japan)
        self.assertIn('id="story-sections"', japan)

    def test_reader_facing_headings_are_localized(self):
        world = self.read("index.html")
        japan = self.read("japan-stocks.html")
        self.assertIn("朝3分の要点", world)
        self.assertIn("市場概況", world)
        self.assertIn("市場横断分析", world)
        self.assertNotIn(">QUICK VIEW<", japan)
        self.assertIn("朝3分の要点", japan)

    def test_copper_chart_identifies_instrument_and_unit(self):
        world = self.read("index.html")
        self.assertIn("銅先物（COMEX・HG=F）", world)
        self.assertIn("米ドル/ポンド", world)
        self.assertIn("LME現物価格ではありません", world)

    def test_mobile_pages_have_clear_section_navigation(self):
        world = self.read("index.html")
        japan = self.read("japan-stocks.html")
        self.assertIn('data-mm-group', world)
        self.assertIn('class="mobile-section-nav"', japan)
        self.assertIn('data-jp-target="story-most-important"', japan)

    def test_japan_market_enrichment_sections_are_present(self):
        japan = self.read("japan-stocks.html")
        for element_id in (
            "market-ranking-section", "stock-ranking-section", "liquidity-section",
            "scenario-review-section", "regime-section",
            "driver-section", "rotation-section", "sector-quality-section", "monitoring-section"
        ):
            self.assertIn(f'id="{element_id}"', japan)
        self.assertIn("全構成銘柄の順位ではありません", japan)
        self.assertIn("終値×出来高の概算値", japan)
        self.assertIn("どちらが強い？", japan)
        self.assertLess(japan.index('id="regime-section"'), japan.index('id="quick-view"'))
        self.assertIn("実測値と推定評価を分けて表示", japan)
        self.assertIn("昨日までの見方", japan)
        self.assertIn("今日の監視材料", japan)
        self.assertIn("data/glossary.json", japan)
        self.assertIn("市場データ表示には影響しません", japan)

    def test_japan_v2_progressive_disclosure_and_plain_japanese(self):
        japan = self.read("japan-stocks.html")
        self.assertNotIn("数字で強弱を確認", japan)
        self.assertIn('id="market-scoreboard"', japan)
        self.assertIn("材料 → 伝達経路 → 影響業種", japan)
        self.assertIn("比較結果 → 差 → 詳細数値", japan)
        self.assertIn("業種ETF自身の勢い・商い・継続力", japan)
        self.assertNotIn('id="internals-section"', japan)
        self.assertIn('className = \'term-help\'', japan)
        self.assertIn("昨日のシナリオ検証 → 今日への修正", japan)
        self.assertIn("総合戦闘力は算出しません", japan)
        self.assertNotIn("朝シナリオの答え合わせ", japan)

    def test_latest_view_warns_when_market_and_report_dates_differ(self):
        world = self.read("index.html")
        self.assertIn('id="freshness-warning"', world)
        self.assertIn("function updateDataFreshness()", world)
        self.assertIn("新しいレポートは品質確認中", world)
        self.assertIn("AIレポート：${reportLabel}（更新待ち）", world)

    def test_structured_policy_cards_are_not_rendered_as_raw_json(self):
        world = self.read("index.html")
        self.assertIn("return { title, ...content };", world)
        self.assertNotIn("typeof content === 'object' ? JSON.stringify(content)", world)

    def test_current_market_context_is_separate_from_daily_report(self):
        world = self.read("index.html")
        self.assertIn('id="market-context-section"', world)
        self.assertIn("/data/market-context.json", world)
        self.assertIn("日次レポートとは別の週次背景情報", world)
        self.assertNotIn("market-context.json", self.read("japan-stocks.html"))

    def test_market_context_is_mobile_first_and_collapsed_by_topic(self):
        world = self.read("index.html")
        self.assertIn("elementWithClass('details', 'context-details')", world)
        self.assertIn("@media (max-width: 560px)", world)
        self.assertIn("ここまでの流れ", world)
        self.assertIn("暮らしへの影響", world)

    def test_glossary_uses_static_json_and_tap_dialog(self):
        world = self.read("index.html")
        self.assertIn("/data/glossary.json", world)
        self.assertIn('id="glossary-dialog"', world)
        self.assertIn("makeGlossaryButton", world)
        self.assertNotIn("glossaryApi", world)


if __name__ == "__main__":
    unittest.main()
