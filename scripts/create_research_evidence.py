#!/usr/bin/env python3
"""Create a deliberately failing daily research-evidence worksheet.

The generated file cannot pass publication until a researcher records evidence,
analysis chains, counter-evidence and all nine final gate decisions.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]


def item(identifier: str, label: str, tier: str) -> dict:
    return {
        "id": identifier,
        "label": label,
        "tier": tier,
        "status": "未調査",
        "evidence": "未入力",
        "attempts": [],
        "impact_if_unavailable": "未入力",
        "publication_use": "not_selected",
    }


def build(report: dict) -> dict:
    now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M JST")
    gates = {
        name: "FAIL"
        for name in (
            "research_coverage", "source_quality", "data_integrity",
            "analysis_logic", "cross_asset_consistency", "japan_transmission",
            "counter_evidence_audit", "previous_day_change", "final_content_audit",
        )
    }
    return {
        "version": "1.0",
        "report_date": report["report_date"],
        "target_market_date": report["target_market_date"],
        "updated_at": now,
        "research_coverage": {
            "status": "FAIL",
            "directions": [
                {"id": key, "status": "FAIL", "evidence": "未入力"}
                for key in (
                    "fixed_universe", "cross_news", "reverse_from_anomalies",
                    "previous_day_change",
                )
            ],
            "items": [
                item("fixed_market_universe", "固定Universe", "Critical"),
                item("policy_and_macro_news", "政策・中央銀行・マクロ", "Critical"),
                item("market_anomaly_reverse_search", "市場異常値からの逆引き", "Required"),
                item("previous_day_view", "前日認識との差分", "Critical"),
                item("company_disclosures", "日本株の個別企業開示", "Critical"),
                item("analyst_rating_changes", "アナリスト評価変更", "Required"),
            ],
        },
        "analysis_quality": {"status": "FAIL", "materials": [], "template_degradation_audit": {}},
        "counter_evidence_audit": {"status": "FAIL", "conclusions": []},
        "cross_asset_consistency": {"status": "FAIL", "assets_checked": [], "relationships": []},
        "previous_day_change": {"status": "FAIL", "prior_view": "", "new_events": [], "changed": [], "unchanged": [], "japan_revision": ""},
        "source_quality": {"status": "FAIL", "checks": []},
        "data_integrity": {"status": "FAIL", "checks": []},
        "quality_gates": gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "report.json")
    parser.add_argument("--output", type=Path, default=ROOT / "work" / "research-evidence.json")
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created failing research worksheet: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
