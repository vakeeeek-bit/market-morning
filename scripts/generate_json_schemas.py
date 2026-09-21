#!/usr/bin/env python3
"""Generate the v1 JSON Schemas from the current canonical data files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCHEMA_DIR = ROOT / "schemas"

FILES = {
    "report": DATA_DIR / "report.json",
    "market": DATA_DIR / "market.json",
    "japan-stocks": DATA_DIR / "japan-stocks.json",
    "status": DATA_DIR / "status.json",
    "market-context": DATA_DIR / "market-context.json",
    "glossary": DATA_DIR / "glossary.json",
}

TOP_LEVEL_REQUIRED = {
    "report": [
        "report_date",
        "target_market_date",
        "updated_at",
        "report_type",
        "quick_view",
        "executive_summary",
        "news",
        "scenarios",
        "market_overview",
        "data_quality",
        "final_conclusion",
    ],
    "market": ["updated_at", "timezone", "markets", "data_quality"],
    "japan-stocks": [
        "report_date",
        "target_market_date",
        "updated_at",
        "report_type",
        "japan_quick_view",
        "top_stories",
        "important_stories",
        "other_stories",
        "data_quality",
    ],
    "status": ["status", "updated_at", "message"],
    "market-context": [
        "updated_at",
        "period_start",
        "period_end",
        "headline",
        "summary",
        "timeline",
        "current_drivers",
        "japan_connection",
        "daily_life_impacts",
        "scenario_change_conditions",
        "sources",
    ],
    "glossary": ["updated_at", "terms"],
}


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise TypeError(type(value))


def merge_schemas(left: dict, right: dict) -> dict:
    left_types = left.get("type", [])
    right_types = right.get("type", [])
    if isinstance(left_types, str):
        left_types = [left_types]
    if isinstance(right_types, str):
        right_types = [right_types]
    types = list(dict.fromkeys([*left_types, *right_types]))
    result: dict[str, Any] = {"type": types[0] if len(types) == 1 else types}

    if "object" in types:
        properties = dict(left.get("properties", {}))
        for key, value in right.get("properties", {}).items():
            properties[key] = merge_schemas(properties[key], value) if key in properties else value
        result["properties"] = properties
        result["additionalProperties"] = True

    if "array" in types:
        left_items = left.get("items")
        right_items = right.get("items")
        if left_items and right_items:
            result["items"] = merge_schemas(left_items, right_items)
        else:
            result["items"] = left_items or right_items or {}
    return result


def infer_schema(value: Any) -> dict:
    kind = value_type(value)
    if kind == "object":
        return {
            "type": "object",
            "properties": {key: infer_schema(child) for key, child in value.items()},
            "additionalProperties": True,
        }
    if kind == "array":
        if not value:
            return {"type": "array", "items": {}}
        items = infer_schema(value[0])
        for child in value[1:]:
            items = merge_schemas(items, infer_schema(child))
        return {"type": "array", "items": items}
    return {"type": kind}


def add_known_formats(schema: dict, key: str | None = None) -> None:
    schema_type = schema.get("type")
    types = [schema_type] if isinstance(schema_type, str) else schema_type or []
    if "string" in types and key in {
        "report_date",
        "target_market_date",
        "market_date",
        "previous_market_date",
        "date",
    }:
        schema["pattern"] = r"^20\d{2}-\d{2}-\d{2}$"
    for child_key, child in schema.get("properties", {}).items():
        add_known_formats(child, child_key)
    if isinstance(schema.get("items"), dict):
        add_known_formats(schema["items"])


def build_schema(name: str, data: dict) -> dict:
    schema = infer_schema(data)
    schema.update(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"https://market-morning-gules.vercel.app/schemas/{name}.schema.json",
            "title": f"Market Morning {name} v1",
            "description": "Current v1 contract. Unknown keys are allowed for forward compatibility.",
        }
    )
    schema["required"] = TOP_LEVEL_REQUIRED[name]
    add_known_formats(schema)
    return schema


def main() -> None:
    SCHEMA_DIR.mkdir(exist_ok=True)
    for name, path in FILES.items():
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        schema = build_schema(name, data)
        output = SCHEMA_DIR / f"{name}.schema.json"
        output.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Generated {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
