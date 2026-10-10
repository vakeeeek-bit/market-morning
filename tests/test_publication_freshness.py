import json
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.sync_publication import sync
from scripts.validate_data import run

ROOT = Path(__file__).resolve().parents[1]

class PublicationFreshnessTests(unittest.TestCase):
    def test_old_analysis_is_not_admitted_by_publish_gate(self):
        self.assertTrue(run(ROOT, 'publish').errors)
        self.assertFalse(run(ROOT, 'report').errors)

    def test_market_news_only_days_are_indexed_without_fake_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / 'data', root / 'data')
            entries = sync(root)
            row = next(e for e in entries if e['date'] == '2026-10-09')
            self.assertTrue(row['has_news'])
            self.assertTrue(row['has_japan_market'])
            self.assertFalse(row['has_report'])
            feed = json.loads((root / 'data/news.json').read_text())
            self.assertEqual(feed, json.loads((root / 'data/history' / feed['report_date'] / 'news.json').read_text()))

    def test_previous_session_is_not_assumed_to_be_holiday(self):
        page = (ROOT / 'index.html').read_text()
        self.assertNotIn('isClosedCashMarketReport = targetMarketDate && targetMarketDate < reportDate', page)

    def test_both_pages_explain_component_dates(self):
        for name in ('index.html', 'japan-stocks.html'):
            self.assertIn('/assets/publication-health.js', (ROOT / name).read_text())
