#!/usr/bin/env python3
"""Machine-enforced research and analysis quality gates."""

from __future__ import annotations

from typing import Any


COVERAGE_STATUSES = {
    "取得済",
    "十分調査したが取得不能",
    "該当材料なし",
    "未調査",
}
TIERS = {"Critical", "Required", "Supplemental"}
DIRECTIONS = {
    "fixed_universe",
    "cross_news",
    "reverse_from_anomalies",
    "previous_day_change",
}
FINAL_GATES = {
    "research_coverage",
    "source_quality",
    "data_integrity",
    "analysis_logic",
    "cross_asset_consistency",
    "japan_transmission",
    "counter_evidence_audit",
    "previous_day_change",
    "final_content_audit",
}
CONFIDENCE = {"confirmed", "supported", "tentative", "unknown"}
PRICING = {"priced", "partially_priced", "unpriced", "unknown"}
TEMPLATE_CHECKS = {
    "today_specific",
    "previous_report_compared",
    "actual_market_reaction_checked",
    "multi_asset_checked",
    "conflicting_materials_compared",
    "transmission_explained",
    "observable_change_conditions",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def validate_research_quality(evidence: dict, report: dict, japan: dict) -> list[str]:
    errors: list[str] = []

    if evidence.get("report_date") != report.get("report_date"):
        errors.append("research-evidence.report_dateがreport.jsonと一致しません")
    if evidence.get("target_market_date") != report.get("target_market_date"):
        errors.append("research-evidence.target_market_dateがreport.jsonと一致しません")
    if evidence.get("report_date") != japan.get("report_date"):
        errors.append("research-evidence.report_dateがjapan-stocks.jsonと一致しません")

    coverage = evidence.get("research_coverage", {})
    if coverage.get("status") != "PASS":
        errors.append("research_coverage.status: PASSが必要です")
    directions = coverage.get("directions", [])
    found_directions = {
        item.get("id") for item in directions if isinstance(item, dict)
    }
    if found_directions != DIRECTIONS:
        errors.append("Research Coverageは4方向すべて必要です")
    for direction in directions if isinstance(directions, list) else []:
        if not isinstance(direction, dict) or direction.get("status") != "PASS" or not _text(direction.get("evidence")):
            errors.append("Research Coverageの4方向は証跡付きPASSが必要です")

    items = coverage.get("items", [])
    if not _list(items):
        errors.append("Research Coverage Matrixが空です")
    rating_found = False
    for index, item in enumerate(items if isinstance(items, list) else []):
        location = f"research_coverage.items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{location}: オブジェクトが必要です")
            continue
        tier = item.get("tier")
        status = item.get("status")
        attempts = item.get("attempts", [])
        if tier not in TIERS:
            errors.append(f"{location}.tier: Critical/Required/Supplementalが必要です")
        if status not in COVERAGE_STATUSES:
            errors.append(f"{location}.status: 調査状態が不正です")
        if status == "未調査":
            errors.append(f"{location}: 未調査は公開不可です")
        if not _text(item.get("evidence")):
            errors.append(f"{location}.evidence: 調査証跡の要約が必要です")
        if status in {"十分調査したが取得不能", "該当材料なし"}:
            required_attempts = 2 if status == "十分調査したが取得不能" else 1
            if not isinstance(attempts, list) or len(attempts) < required_attempts:
                errors.append(f"{location}: {status}には調査試行が{required_attempts}件以上必要です")
        if status == "十分調査したが取得不能":
            if tier == "Critical":
                errors.append(f"{location}: Critical項目の取得不能は公開不可です")
            if not _text(item.get("impact_if_unavailable")):
                errors.append(f"{location}: 取得不能の分析影響評価が必要です")
        for attempt_index, attempt in enumerate(attempts if isinstance(attempts, list) else []):
            if not isinstance(attempt, dict) or not _text(attempt.get("method")) or not _text(attempt.get("result")):
                errors.append(f"{location}.attempts[{attempt_index}]: methodとresultが必要です")
            urls = attempt.get("source_urls", []) if isinstance(attempt, dict) else []
            if not isinstance(urls, list) or not urls or any(not str(url).startswith("https://") for url in urls):
                errors.append(f"{location}.attempts[{attempt_index}]: HTTPSの調査先が必要です")
        if item.get("id") == "analyst_rating_changes":
            rating_found = tier == "Required"
    if not rating_found:
        errors.append("アナリスト評価変更をRequired項目として調査してください")

    analysis = evidence.get("analysis_quality", {})
    if analysis.get("status") != "PASS":
        errors.append("analysis_quality.status: PASSが必要です")
    materials = analysis.get("materials", [])
    if not _list(materials):
        errors.append("Analysis Qualityの重要材料が空です")
    for index, material in enumerate(materials if isinstance(materials, list) else []):
        location = f"analysis_quality.materials[{index}]"
        if not isinstance(material, dict):
            errors.append(f"{location}: オブジェクトが必要です")
            continue
        fact = material.get("fact", {})
        reaction = material.get("observed_market_reaction", {})
        internals = material.get("market_internals", {})
        pricing = material.get("market_pricing", {})
        interpretation = material.get("interpretation", {})
        transmission = material.get("japan_transmission", {})
        required_texts = [
            ("headline", material.get("headline")),
            ("fact.text", fact.get("text")),
            ("observed_market_reaction.text", reaction.get("text")),
            ("market_internals.text", internals.get("text")),
            ("interpretation.text", interpretation.get("text")),
            ("interpretation.evidence", interpretation.get("evidence")),
            ("interpretation.uncertainty", interpretation.get("uncertainty")),
            ("japan_transmission.economic_channel", transmission.get("economic_channel")),
            ("japan_transmission.pricing_in_japan", transmission.get("pricing_in_japan")),
            ("japan_transmission.assessment", transmission.get("assessment")),
            ("conflict_resolution", material.get("conflict_resolution")),
        ]
        for label, value in required_texts:
            if not _text(value):
                errors.append(f"{location}.{label}: 空でない説明が必要です")
        if not _list(fact.get("source_urls")) or any(not str(url).startswith("https://") for url in fact.get("source_urls", [])):
            errors.append(f"{location}.fact.source_urls: HTTPS出典が必要です")
        if not isinstance(reaction.get("assets_checked"), list) or len(reaction["assets_checked"]) < 2:
            errors.append(f"{location}: 実際の市場反応を複数資産で確認してください")
        if pricing.get("status") not in PRICING:
            errors.append(f"{location}.market_pricing.status: 織り込み状態が不正です")
        if interpretation.get("confidence") not in CONFIDENCE:
            errors.append(f"{location}.interpretation.confidence: 確信度が不正です")
        if material.get("chronology_check") != "PASS":
            errors.append(f"{location}: 時系列確認がPASSではありません")
        if not _list(transmission.get("intermediate_reactions")) or not _list(transmission.get("affected_sectors")):
            errors.append(f"{location}: 日本株への途中経路と対象業種が必要です")
        if not _list(material.get("counter_evidence")):
            errors.append(f"{location}: 反証材料の確認が必要です")
        if not _list(material.get("change_conditions")):
            errors.append(f"{location}: 観測可能な見方変更条件が必要です")

    template = analysis.get("template_degradation_audit", {})
    for key in TEMPLATE_CHECKS:
        if template.get(key) is not True:
            errors.append(f"template_degradation_audit.{key}: trueが必要です")
    if not _text(template.get("comparison_note")):
        errors.append("template_degradation_audit.comparison_note: 前日文章との差分証跡が必要です")

    cross = evidence.get("cross_asset_consistency", {})
    if cross.get("status") != "PASS":
        errors.append("cross_asset_consistency.status: PASSが必要です")
    required_assets = {"equities", "rates", "fx", "commodities", "crypto"}
    if set(cross.get("assets_checked", [])) != required_assets:
        errors.append("Cross-Asset監査は株・金利・為替・商品・暗号資産が必要です")
    relationships = cross.get("relationships", [])
    if not _list(relationships):
        errors.append("Cross-Assetの整合・矛盾関係を1件以上記録してください")
    for index, relationship in enumerate(relationships if isinstance(relationships, list) else []):
        if not isinstance(relationship, dict) or not _text(relationship.get("combination")) or not _text(relationship.get("explanation")):
            errors.append(f"cross_asset_consistency.relationships[{index}]: 組み合わせと説明が必要です")
        if relationship.get("unresolved") is True and not _text(relationship.get("uncertainty")):
            errors.append(f"cross_asset_consistency.relationships[{index}]: 未解決なら不確実性を明記してください")

    counter = evidence.get("counter_evidence_audit", {})
    if counter.get("status") != "PASS":
        errors.append("counter_evidence_audit.status: PASSが必要です")
    conclusions = counter.get("conclusions", [])
    if not _list(conclusions):
        errors.append("Counter-Evidence Auditが空です")
    for index, conclusion in enumerate(conclusions if isinstance(conclusions, list) else []):
        if not isinstance(conclusion, dict) or not isinstance(conclusion.get("checks"), list) or len(conclusion["checks"]) < 2 or not _text(conclusion.get("weighing")) or not _text(conclusion.get("uncertainty")):
            errors.append(f"counter_evidence_audit.conclusions[{index}]: 反証確認・比較・不確実性が必要です")

    previous = evidence.get("previous_day_change", {})
    if previous.get("status") != "PASS":
        errors.append("previous_day_change.status: PASSが必要です")
    for key in ("prior_view", "new_events", "changed", "unchanged", "japan_revision"):
        value = previous.get(key)
        valid = _list(value) if key in {"new_events", "changed", "unchanged"} else _text(value)
        if not valid:
            errors.append(f"previous_day_change.{key}: 前日認識との差分が必要です")

    source_quality = evidence.get("source_quality", {})
    if source_quality.get("status") != "PASS" or not _list(source_quality.get("checks")):
        errors.append("Source Qualityの確認証跡とPASSが必要です")
    integrity = evidence.get("data_integrity", {})
    if integrity.get("status") != "PASS" or not _list(integrity.get("checks")):
        errors.append("Data Integrityの確認証跡とPASSが必要です")

    final_gates = evidence.get("quality_gates", {})
    if set(final_gates) != FINAL_GATES:
        errors.append("最終Quality Gateは指定9項目を過不足なく持つ必要があります")
    for gate in FINAL_GATES:
        if final_gates.get(gate) != "PASS":
            errors.append(f"quality_gates.{gate}: PASSでなければ公開不可です")
    return errors
