import ast
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class JapanMarketDesignTests(unittest.TestCase):
    def test_universe_uses_seventeen_sector_etfs_and_two_stocks_each(self):
        data = json.loads((ROOT / "data" / "japan-universe.json").read_text(encoding="utf-8"))
        self.assertEqual(17, len(data["sectors"]))
        self.assertTrue(all(len(sector["stocks"]) == 2 for sector in data["sectors"]))
        self.assertEqual(34, sum(len(sector["stocks"]) for sector in data["sectors"]))

    def test_updater_uses_one_batched_download(self):
        source = (ROOT / "scripts" / "update_japan_market.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "download"]
        self.assertEqual(1, len(calls))
        self.assertIn('period="35d"', source)
        self.assertIn("meets_quality_gate", source)
        self.assertIn("既存データを維持します", source)
        self.assertIn('"大引け後" if review_ready else "取引中暫定"', source)
        self.assertIn('result["status"] = "大引け待ち"', source)
        self.assertIn('data_phase = "日付不一致・判定保留"', source)
        self.assertIn('result["status"] = "判定保留"', source)
        self.assertIn('sector_date == stock_date == expected_market_date', source)
        self.assertIn("aligned_fallback_snapshot", source)
        self.assertIn("取得日不一致のため、整合済みの", source)

    def test_published_data_does_not_claim_review_when_dates_differ(self):
        data = json.loads((ROOT / "data" / "japan-market.json").read_text(encoding="utf-8"))
        alignment = data.get("data_quality", {}).get("date_alignment")
        if alignment and not alignment.get("aligned"):
            self.assertNotEqual("判定可能", data.get("scenario_review", {}).get("status"))

    def test_aligned_history_can_be_used_as_fallback(self):
        sys.modules.setdefault("yfinance", types.SimpleNamespace(download=None))
        spec = importlib.util.spec_from_file_location("update_japan_market_test", ROOT / "scripts" / "update_japan_market.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        snapshot = json.loads((ROOT / "data" / "history" / "2026-09-15" / "japan-market.json").read_text(encoding="utf-8"))
        fallback = module.aligned_fallback_snapshot(snapshot, "2026-09-15")
        self.assertIsNotNone(fallback)
        self.assertTrue(fallback["data_quality"]["date_alignment"]["aligned"])

    def test_close_workflow_runs_after_tokyo_close(self):
        source = (ROOT / ".github" / "workflows" / "japan-market-close.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "45 6 * * 1-5"', source)
        self.assertIn("update_japan_market.py", source)


if __name__ == "__main__":
    unittest.main()
