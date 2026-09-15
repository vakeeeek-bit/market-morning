import ast
import json
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
        self.assertIn('data_phase = "大引け後" if review_ready else "取引中暫定"', source)
        self.assertIn('result["status"] = "大引け待ち"', source)

    def test_close_workflow_runs_after_tokyo_close(self):
        source = (ROOT / ".github" / "workflows" / "japan-market-close.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "45 6 * * 1-5"', source)
        self.assertIn("update_japan_market.py", source)


if __name__ == "__main__":
    unittest.main()
