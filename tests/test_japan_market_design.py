import ast
import importlib.util
import json
import sys
import types
import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo
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
        self.assertIn('"データ異常・検証保留" if blocked_reason', source)
        self.assertIn('data_phase = "休場" if holiday', source)
        self.assertIn('result["status"] = "判定保留"', source)
        self.assertIn('sector_date == stock_date == expected_market_date', source)
        self.assertIn("aligned_fallback_snapshot", source)
        self.assertIn("取得日不一致のため、整合済みの", source)
        self.assertIn("MARKET_PATH", source)
        self.assertIn("enrich_investor_view", source)

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

    def test_market_view_does_not_use_thirty_four_stock_breadth(self):
        data = json.loads((ROOT / "data" / "japan-market.json").read_text(encoding="utf-8"))
        view = json.dumps(data["market_regime"], ensure_ascii=False)
        self.assertEqual(2, len(data["market_regime"]["scoreboard"]))
        self.assertNotIn("Breadth", view)
        self.assertNotIn("上昇・下落の広がり", view)

    def test_rotation_is_labeled_as_price_action_estimate(self):
        data = json.loads((ROOT / "data" / "japan-market.json").read_text(encoding="utf-8"))
        self.assertEqual("どちらが強い？", data["rotation_read"]["label"])
        self.assertIn("投資主体別", data["rotation_read"]["note"])
        self.assertEqual(["外需と内需"], [item["axis"] for item in data["rotation_read"]["items"]])

    def test_newer_overseas_drivers_are_marked_unpriced(self):
        data = json.loads((ROOT / "data" / "japan-market.json").read_text(encoding="utf-8"))
        for item in data["key_drivers"]:
            if item.get("market_date") and item["market_date"] > data["market_date"]:
                self.assertEqual("日本株現物に未反映", item["pricing_status"])

    def test_v2_selects_drivers_with_transparent_factors_without_fixed_slots(self):
        data = json.loads((ROOT / "data" / "japan-market.json").read_text(encoding="utf-8"))
        drivers = data["key_drivers"]
        self.assertGreaterEqual(len(drivers), 3)
        self.assertLessEqual(len(drivers), 5)
        self.assertTrue(all(item.get("selection_factors") for item in drivers))
        self.assertTrue(all(item.get("change_condition") for item in drivers))
        self.assertTrue(all("impact_score" not in item for item in drivers))
        self.assertTrue(all(item.get("category") for item in drivers))
        source = (ROOT / "scripts" / "update_japan_market.py").read_text(encoding="utf-8")
        self.assertIn("def selection_key(item):", source)

    def test_sector_quality_uses_only_sector_etf_three_axes(self):
        data = json.loads((ROOT / "data" / "japan-market.json").read_text(encoding="utf-8"))
        for item in data["sector_quality"]:
            self.assertEqual({"momentum", "activity", "persistence"}, set(item["axes"]))
            self.assertNotIn("combat_power", item)
            self.assertTrue(all(axis.get("rule") for axis in item["axes"].values()))
            self.assertNotIn("2銘柄", json.dumps(item, ensure_ascii=False))
            self.assertIsInstance(item["relative_today_pct"], (int, float))
            self.assertIn("TOPIX", item["axes"]["momentum"]["label"])

    def test_scenario_review_revises_view_instead_of_scoring_prediction(self):
        data = json.loads((ROOT / "data" / "japan-market.json").read_text(encoding="utf-8"))
        review = data["scenario_review"]
        self.assertEqual("昨日のシナリオ検証 → 今日への修正", review["title"])
        for key in ("previous_condition", "condition_result", "market_reaction", "unexpected_gap", "gap_reason", "revision", "today_watch"):
            self.assertIn(key, review)
        self.assertNotIn("○×", json.dumps(review, ensure_ascii=False))

    def test_holiday_and_data_error_have_distinct_states(self):
        data = json.loads((ROOT / "data" / "japan-market.json").read_text(encoding="utf-8"))
        self.assertIn(data["data_state"]["kind"], {"normal", "holiday", "data_error"})
        report = json.loads((ROOT / "data" / "japan-stocks.json").read_text(encoding="utf-8"))
        if report.get("report_date") != report.get("target_market_date") and "休場" in json.dumps(report, ensure_ascii=False):
            self.assertEqual("holiday", data["data_state"]["kind"])
            self.assertEqual("休場", data["data_phase"])

    def test_jpx_holiday_reason_uses_execution_date(self):
        sys.modules.setdefault("yfinance", types.SimpleNamespace(download=None))
        spec = importlib.util.spec_from_file_location("update_japan_market_holiday_test", ROOT / "scripts" / "update_japan_market.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual("秋分の日", module.jpx_closure_name(date(2026, 9, 23)))
        self.assertIsNone(module.jpx_closure_name(date(2026, 9, 24)))

        snapshot = {"market_date": "2026-09-18", "data_quality": {}, "sector_ranking": []}
        refreshed = module.refresh_closed_day_snapshot(
            snapshot,
            datetime(2026, 9, 23, 12, 34, tzinfo=ZoneInfo("Asia/Tokyo")),
            {},
            {},
        )
        self.assertEqual("holiday", refreshed["data_state"]["kind"])
        self.assertEqual("2026-09-23は秋分の日で休場。2026-09-18の前営業日データを表示", refreshed["data_state"]["message"])

    def test_close_workflow_runs_after_tokyo_close(self):
        source = (ROOT / ".github" / "workflows" / "japan-market-close.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "45 6 * * 1-5"', source)
        self.assertIn("update_japan_market.py", source)


if __name__ == "__main__":
    unittest.main()
