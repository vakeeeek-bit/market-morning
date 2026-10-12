#!/usr/bin/env python3
"""Carry unresolved research items into the next daily worksheet."""

from __future__ import annotations

import json
from pathlib import Path


def load_items(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return value.get("items", []) if isinstance(value, dict) else []


def merge_items(path: Path, evidence: dict) -> dict:
    previous = {item.get("id"): item for item in load_items(path) if isinstance(item, dict)}
    resolved = set(evidence.get("publication_decision", {}).get("resolved_item_ids", []))
    current = evidence.get("publication_decision", {}).get("unresolved_items", [])
    merged = {key: value for key, value in previous.items() if key not in resolved}
    for item in current if isinstance(current, list) else []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        old = previous.get(item["id"], {})
        updated = dict(item)
        updated.setdefault("first_seen_at", old.get("first_seen_at", evidence.get("updated_at")))
        updated["last_checked_at"] = item.get("last_checked_at", evidence.get("updated_at"))
        merged[item["id"]] = updated
    payload = {
        "updated_at": evidence.get("updated_at"),
        "source_report_date": evidence.get("report_date"),
        "items": sorted(merged.values(), key=lambda item: str(item.get("id"))),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
