from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_data import ROOT, run


class ValidateDataTest(unittest.TestCase):
    def make_root(self, mutate=None) -> Path:
        temporary = Path(tempfile.mkdtemp())
        (temporary / "data").mkdir()
        (temporary / "schemas").mkdir()
        for name in (
            "report", "market", "japan-stocks", "japan-market", "status",
            "market-context", "glossary", "research-evidence"
        ):
            data = json.loads((ROOT / "data" / f"{name}.json").read_text())
            if mutate:
                data = mutate(name, copy.deepcopy(data))
            (temporary / "data" / f"{name}.json").write_text(json.dumps(data))
            schema = ROOT / "schemas" / f"{name}.schema.json"
            (temporary / "schemas" / schema.name).write_bytes(schema.read_bytes())
        return temporary

    def test_current_data_has_no_errors(self):
        result = run(ROOT)
        self.assertEqual([], result.errors)

    def test_top5_mismatch_is_error(self):
        def mutate(name, data):
            if name == "japan-stocks":
                data["japan_quick_view"]["top_materials"][0] = "不一致"
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("TOP5" in message for message in result.errors))

    def test_missing_required_key_is_error(self):
        def mutate(name, data):
            if name == "report":
                del data["quick_view"]
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("必須項目" in message for message in result.errors))

    def test_market_context_timeline_outside_period_is_error(self):
        def mutate(name, data):
            if name == "market-context":
                data["timeline"][0]["date"] = "2025-01-01"
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("対象期間外" in message for message in result.errors))

    def test_invalid_life_impact_type_is_error(self):
        def mutate(name, data):
            if name == "market-context":
                data["daily_life_impacts"][0]["evidence_type"] = "断定"
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("影響区分" in message for message in result.errors))

    def test_duplicate_glossary_term_is_error(self):
        def mutate(name, data):
            if name == "glossary":
                data["terms"][1]["term"] = data["terms"][0]["term"]
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("重複" in message for message in result.errors))

    def test_sector_or_macro_label_cannot_pass_as_company_news(self):
        def mutate(name, data):
            if name == "japan-stocks":
                data["top_stories"][0]["company"] = "半導体・高PER株"
                data["top_stories"][0]["ticker"] = "-"
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("銘柄コード" in message for message in result.errors))

    def test_secondary_market_article_cannot_replace_primary_company_source(self):
        def mutate(name, data):
            if name == "japan-stocks":
                data["top_stories"][0]["source_url"] = "https://www.reuters.com/example"
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("一次情報" in message for message in result.errors))

    def test_company_news_preview_must_match_detail(self):
        def mutate(name, data):
            if name == "report":
                data["japan_equities_preview"]["top_stories"][0]["headline"] = "不一致"
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("プレビュー" in message for message in result.errors))

    def test_actual_omission_is_blocked_by_research_gate(self):
        """Regression: the old flow passed despite skipping individual-stock research."""
        def mutate(name, data):
            if name == "research-evidence":
                item = next(row for row in data["research_coverage"]["items"] if row["id"] == "company_disclosures")
                item["status"] = "未調査"
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("未調査は公開不可" in message for message in result.errors))

    def test_analysis_gate_rejects_sox_only_semiconductor_claim(self):
        """Regression: SOX alone cannot establish a broad Japan semiconductor tailwind."""
        def mutate(name, data):
            if name == "research-evidence":
                material = data["analysis_quality"]["materials"][0]
                material["observed_market_reaction"]["assets_checked"] = ["SOX"]
                material["japan_transmission"]["intermediate_reactions"] = []
                material["counter_evidence"] = []
                material["chronology_check"] = "FAIL"
                data["quality_gates"]["analysis_logic"] = "FAIL"
            return data

        result = run(self.make_root(mutate))
        joined = "\n".join(result.errors)
        self.assertIn("途中経路", joined)
        self.assertIn("反証材料", joined)
        self.assertIn("時系列", joined)
        self.assertIn("analysis_logic", joined)

    def test_required_unavailable_needs_two_attempts_and_impact(self):
        def mutate(name, data):
            if name == "research-evidence":
                item = next(row for row in data["research_coverage"]["items"] if row["id"] == "analyst_rating_changes")
                item["attempts"] = item["attempts"][:1]
                item["impact_if_unavailable"] = ""
            return data

        result = run(self.make_root(mutate))
        joined = "\n".join(result.errors)
        self.assertIn("調査試行が2件以上", joined)
        self.assertIn("分析影響評価", joined)

    def test_counter_evidence_cannot_be_empty(self):
        def mutate(name, data):
            if name == "research-evidence":
                data["counter_evidence_audit"]["conclusions"] = []
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("Counter-Evidence Auditが空" in message for message in result.errors))

    def test_unavailable_analyst_coverage_cannot_claim_no_changes(self):
        def mutate(name, data):
            if name == "japan-stocks":
                data["analyst_rating_changes"]["headline"] = "本日の変更なし"
            return data

        result = run(self.make_root(mutate))
        self.assertTrue(any("『変更なし』と断定" in message for message in result.errors))


if __name__ == "__main__":
    unittest.main()
