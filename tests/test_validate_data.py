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
            "market-context", "glossary"
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


if __name__ == "__main__":
    unittest.main()
