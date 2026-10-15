import importlib.util
import json
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MarketContextUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "update_market_context", ROOT / "scripts" / "update_market_context.py"
        )
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_generated_context_matches_committed_data(self):
        actual = json.loads((ROOT / "data" / "market-context.json").read_text())
        self.assertEqual(self.module.build_context(), actual)

    def test_context_has_audited_theme_transitions(self):
        context = self.module.build_context()
        self.assertGreaterEqual(len(context["themes"]), 3)
        self.assertLessEqual(len(context["themes"]), 5)
        source_ids = {item["id"] for item in context["sources"]}
        dates = []
        for theme in context["themes"]:
            self.assertTrue(theme["current_view"])
            self.assertTrue(theme["japan_impact"])
            self.assertTrue(theme["counter_evidence"])
            self.assertTrue(set(theme["source_ids"]).issubset(source_ids))
            self.assertGreaterEqual(len(theme["timeline"]), 3)
            timeline_dates = [event["date"] for event in theme["timeline"]]
            self.assertEqual(timeline_dates, sorted(timeline_dates))
            for event in theme["timeline"]:
                self.assertTrue(event["title"])
                self.assertTrue(event["fact"])
                self.assertTrue(event["market_impact"])
                self.assertTrue(set(event["source_ids"]).issubset(source_ids))
                dates.append(event["date"])
            for key in ("initial_view", "new_fact", "market_reaction"):
                dates.append(theme[key]["date"])
                self.assertTrue(theme[key]["text"])
        self.assertGreaterEqual(len(set(dates)), 3)
        self.assertEqual(context["period_start"], min(dates))
        self.assertEqual(context["period_end"], max(dates))
        self.assertGreaterEqual(
            (date.fromisoformat(context["period_end"]) - date.fromisoformat(context["period_start"])).days,
            180,
        )

    def test_context_is_tied_to_current_report_and_history(self):
        context = self.module.build_context()
        report = json.loads((ROOT / "data" / "report.json").read_text())
        self.assertEqual(context["report_date"], report["report_date"])
        self.assertEqual(context["freshness"]["status"], "current")
        self.assertGreaterEqual(context["freshness"]["source_report_count"], 2)


if __name__ == "__main__":
    unittest.main()
