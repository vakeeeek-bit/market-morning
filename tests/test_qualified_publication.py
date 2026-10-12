from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.publication_policy import assess_market_publication, assess_report_publication
from scripts.research_quality import validate_research_quality
from scripts.unresolved_items import load_items, merge_items


ROOT = Path(__file__).resolve().parents[1]


class QualifiedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / "data/report.json").read_text(encoding="utf-8"))
        self.japan = json.loads((ROOT / "data/japan-stocks.json").read_text(encoding="utf-8"))
        self.evidence = json.loads((ROOT / "data/research-evidence.json").read_text(encoding="utf-8"))
        for material in self.evidence["analysis_quality"]["materials"]:
            material["fact"]["verification_status"] = "PASS"
        stamp = "2026-10-12T15:00:00+09:00"
        item = {
            "id": "analyst-contract-coverage",
            "status": "QUALIFIED",
            "missing": "契約データがなく全証券会社を網羅できない",
            "impact": "確認済み変更だけ掲載し、変更なしとは断定しない",
            "last_checked_at": stamp,
            "next_action": "翌営業日に公開情報と契約可否を再確認",
            "attempts": [{"method": "公開情報を二経路確認", "result": "部分取得", "checked_at": stamp}],
            "affected_components": ["japan_stocks"],
            "excluded_claims": ["全証券会社で変更なし"],
            "excluded_from_publication": True,
        }
        self.evidence["publication_decision"] = {
            "status": "QUALIFIED",
            "decided_at": stamp,
            "summary": "取得不能範囲を除外した注釈付き公開",
            "components": {
                "ai_report": {"status": "QUALIFIED", "updated_at": stamp, "reason": "一部データを除外"},
                "japan_stocks": {"status": "QUALIFIED", "updated_at": stamp, "reason": "レーティング非網羅"},
            },
            "unresolved_items": [item],
            "resolved_item_ids": [],
        }
        self.report["publication_policy"] = {"status": "QUALIFIED", "updated_at": stamp, "note": "不足を注記"}
        self.japan["publication_policy"] = {"status": "QUALIFIED", "updated_at": stamp, "note": "不足を注記"}
        self.evidence["research_coverage"]["status"] = "QUALIFIED"
        self.evidence["quality_gates"]["research_coverage"] = "QUALIFIED"

    def test_analyst_coverage_can_be_qualified_without_claiming_completeness(self):
        self.assertEqual([], validate_research_quality(self.evidence, self.report, self.japan))
        self.assertEqual("QUALIFIED", assess_report_publication(self.evidence, self.report, self.japan).status)

    def test_unverified_policy_assertion_is_blocked(self):
        self.evidence["analysis_quality"]["materials"][0]["fact"]["verification_status"] = "unverified"
        errors = validate_research_quality(self.evidence, self.report, self.japan)
        self.assertTrue(any("実読確認PASS" in error for error in errors))

    def test_missing_index_is_qualified_when_attempts_and_limitations_are_recorded(self):
        market = json.loads((ROOT / "data/market.json").read_text(encoding="utf-8"))
        market["markets"]["russell2000"].update(price=None, market_date=None, status="取得失敗")
        market["data_quality"].update(
            failed_count=1,
            failed_keys=["russell2000"],
            retrieval_attempts=[{"method": "3回再試行", "result": "取得不能"}],
            limitations=["Russell2000を方向判断から除外"],
        )
        self.assertEqual("QUALIFIED", assess_market_publication(market).status)

    def test_missing_transmission_or_counter_evidence_is_blocked(self):
        broken = copy.deepcopy(self.evidence)
        broken["analysis_quality"]["materials"][0]["japan_transmission"]["intermediate_reactions"] = []
        broken["analysis_quality"]["materials"][0]["counter_evidence"] = []
        errors = validate_research_quality(broken, self.report, self.japan)
        self.assertTrue(any("途中経路" in error for error in errors))
        self.assertTrue(any("反証材料" in error for error in errors))

    def test_blocked_item_must_be_excluded_from_report(self):
        item = self.evidence["publication_decision"]["unresolved_items"][0]
        item["status"] = "BLOCK"
        item["excluded_from_publication"] = False
        self.assertEqual("BLOCK", assess_report_publication(self.evidence, self.report, self.japan).status)

    def test_unresolved_item_is_carried_to_next_day_until_resolved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "unresolved-items.json"
            merge_items(path, self.evidence)
            next_day = copy.deepcopy(self.evidence)
            next_day["report_date"] = "2026-10-13"
            next_day["updated_at"] = "2026-10-13T06:00:00+09:00"
            next_day["publication_decision"]["unresolved_items"] = []
            merge_items(path, next_day)
            self.assertEqual("analyst-contract-coverage", load_items(path)[0]["id"])
            next_day["publication_decision"]["resolved_item_ids"] = ["analyst-contract-coverage"]
            merge_items(path, next_day)
            self.assertEqual([], load_items(path))


if __name__ == "__main__":
    unittest.main()
