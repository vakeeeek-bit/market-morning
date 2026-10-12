#!/usr/bin/env python3
"""Publication-unit admission for PASS / QUALIFIED / BLOCK.

The policy is intentionally separate from JSON-schema validation.  A document
may be structurally valid and still be unsafe to publish.  Conversely, a
researched document with explicitly excluded observations may be safe as a
QUALIFIED publication without pretending that every source was available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DECISIONS = {"PASS", "QUALIFIED", "BLOCK"}
QUALIFIABLE_GATES = {
    "research_coverage",
    "data_integrity",
    "cross_asset_consistency",
}
STRICT_GATES = {
    "source_quality",
    "analysis_logic",
    "japan_transmission",
    "counter_evidence_audit",
    "previous_day_change",
    "final_content_audit",
}


@dataclass
class PublicationAssessment:
    status: str = "PASS"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def block(self, message: str) -> None:
        self.status = "BLOCK"
        self.errors.append(message)

    def qualify(self, message: str) -> None:
        if self.status != "BLOCK":
            self.status = "QUALIFIED"
        self.warnings.append(message)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def validate_unresolved_item(item: Any, index: int, assessment: PublicationAssessment) -> None:
    location = f"publication_decision.unresolved_items[{index}]"
    if not isinstance(item, dict):
        assessment.block(f"{location}: オブジェクトが必要です")
        return
    for key in ("id", "missing", "impact", "last_checked_at", "next_action"):
        if not _text(item.get(key)):
            assessment.block(f"{location}.{key}: 空でない記録が必要です")
    if item.get("status") not in {"QUALIFIED", "BLOCK"}:
        assessment.block(f"{location}.status: QUALIFIED/BLOCKが必要です")
    attempts = item.get("attempts")
    if not isinstance(attempts, list) or len(attempts) < 1:
        assessment.block(f"{location}.attempts: 実際の調査試行が必要です")
    else:
        for attempt_index, attempt in enumerate(attempts):
            if not isinstance(attempt, dict):
                assessment.block(f"{location}.attempts[{attempt_index}]: オブジェクトが必要です")
                continue
            if not _text(attempt.get("method")) or not _text(attempt.get("result")):
                assessment.block(f"{location}.attempts[{attempt_index}]: method/resultが必要です")
            if not _text(attempt.get("checked_at")):
                assessment.block(f"{location}.attempts[{attempt_index}].checked_at: 確認時刻が必要です")
    if not isinstance(item.get("affected_components"), list):
        assessment.block(f"{location}.affected_components: 影響範囲が必要です")
    if not isinstance(item.get("excluded_claims"), list):
        assessment.block(f"{location}.excluded_claims: 除外した断定の記録が必要です")


def assess_report_publication(evidence: dict, report: dict, japan: dict) -> PublicationAssessment:
    """Assess whether the AI report bundle can be published.

    BLOCK content is never admitted.  A bundle can be QUALIFIED only after the
    blocked material has been excluded and all strict analytical gates pass.
    """
    assessment = PublicationAssessment()
    decision = evidence.get("publication_decision")
    policies = [report.get("publication_policy"), japan.get("publication_policy")]

    if not isinstance(decision, dict):
        # Legacy all-PASS bundles remain valid; new qualified bundles must carry
        # the explicit decision record.
        gates = evidence.get("quality_gates", {})
        if gates and all(value == "PASS" for value in gates.values()):
            return assessment
        assessment.block("research-evidence.publication_decision: 公開判定記録が必要です")
        return assessment

    declared = decision.get("status")
    if declared not in DECISIONS:
        assessment.block("publication_decision.status: PASS/QUALIFIED/BLOCKが必要です")
        return assessment
    if declared == "BLOCK":
        assessment.block("publication_decision.status: BLOCKの総合レポートは公開不可です")

    if not _text(decision.get("decided_at")) or not _text(decision.get("summary")):
        assessment.block("publication_decision: decided_atとsummaryが必要です")

    components = decision.get("components")
    if not isinstance(components, dict):
        assessment.block("publication_decision.components: 公開単位別判定が必要です")
    else:
        for name in ("ai_report", "japan_stocks"):
            component = components.get(name)
            if not isinstance(component, dict) or component.get("status") not in DECISIONS:
                assessment.block(f"publication_decision.components.{name}: 公開判定が必要です")
                continue
            if component.get("status") == "BLOCK":
                assessment.block(f"publication_decision.components.{name}: BLOCKは公開できません")
            if not _text(component.get("updated_at")) or not _text(component.get("reason")):
                assessment.block(f"publication_decision.components.{name}: updated_at/reasonが必要です")

    gates = evidence.get("quality_gates", {})
    for gate in STRICT_GATES:
        if gates.get(gate) != "PASS":
            assessment.block(f"quality_gates.{gate}: 分析の必須ゲートはPASSが必要です")
    for gate in QUALIFIABLE_GATES:
        value = gates.get(gate)
        if value == "QUALIFIED":
            assessment.qualify(f"quality_gates.{gate}: 注釈付き公開")
        elif value != "PASS":
            assessment.block(f"quality_gates.{gate}: PASS/QUALIFIEDが必要です")

    unresolved = decision.get("unresolved_items", [])
    if not isinstance(unresolved, list):
        assessment.block("publication_decision.unresolved_items: 配列が必要です")
        unresolved = []
    for index, item in enumerate(unresolved):
        validate_unresolved_item(item, index, assessment)
        if isinstance(item, dict) and item.get("status") == "BLOCK":
            affected = set(item.get("affected_components", []))
            if affected & {"ai_report", "japan_stocks"} and not item.get("excluded_from_publication"):
                assessment.block(
                    f"publication_decision.unresolved_items[{index}]: BLOCK箇所は公開対象からの除外が必要です"
                )

    if declared == "QUALIFIED":
        if not unresolved:
            assessment.block("QUALIFIED公開には未解決項目の具体的記録が必要です")
        else:
            assessment.qualify("総合レポートは不足・除外範囲を明示したQUALIFIED公開です")

    for index, policy in enumerate(policies):
        name = "report" if index == 0 else "japan-stocks"
        if not isinstance(policy, dict):
            assessment.block(f"{name}.publication_policy: 公開判定が必要です")
            continue
        if policy.get("status") != declared:
            assessment.block(f"{name}.publication_policy.status: 調査証跡の判定と一致しません")
        if not _text(policy.get("updated_at")) or not _text(policy.get("note")):
            assessment.block(f"{name}.publication_policy: updated_at/noteが必要です")

    if declared == "PASS" and assessment.status == "QUALIFIED":
        assessment.block("公開判定をPASSとしながらQUALIFIEDゲートが残っています")
    if declared == "QUALIFIED" and assessment.status == "PASS":
        assessment.qualify("公開判定はQUALIFIEDです")
    return assessment


def assess_market_publication(market: dict) -> PublicationAssessment:
    """Allow a bounded partial market refresh while blocking misleading data."""
    assessment = PublicationAssessment()
    rows = market.get("markets", {})
    core = ("sp500", "nasdaq", "nasdaq100", "dow", "russell2000", "sox", "vix")
    available = []
    missing = []
    for key in core:
        row = rows.get(key, {})
        if isinstance(row.get("price"), (int, float)) and _text(row.get("market_date")):
            available.append(key)
            if row.get("status") != "取得成功":
                assessment.qualify(f"{key}: 前回確認値を基準日付きで維持")
        else:
            missing.append(key)
    broad_available = any(key in available for key in ("sp500", "nasdaq", "dow"))
    if len(available) < 5 or not broad_available:
        assessment.block("主要米国指数の確認済み観測が不足し、安全な市場更新を構成できません")
    elif missing:
        assessment.qualify("一部指数を取得不能として注釈付きで更新: " + ", ".join(missing))

    quality = market.get("data_quality", {})
    if missing or quality.get("failed_count", 0):
        attempts = quality.get("retrieval_attempts")
        if not isinstance(attempts, list) or not attempts:
            assessment.block("市場欠測には再試行・代替取得の記録が必要です")
        if not _list(quality.get("limitations")):
            assessment.block("市場欠測には影響・表示上の制約が必要です")
    return assessment
