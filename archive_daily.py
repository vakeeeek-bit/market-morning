#!/usr/bin/env python3
"""Archive the current Market Morning JSON files by report date.

Expected repository layout:
  data/report.json
  data/market.json
  data/history/YYYY-MM-DD/report.json
  data/history/YYYY-MM-DD/market.json
  data/history/index.json
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
REPORT_PATH = DATA_DIR / "report.json"
MARKET_PATH = DATA_DIR / "market.json"
HISTORY_DIR = DATA_DIR / "history"
INDEX_PATH = HISTORY_DIR / "index.json"


def reject_non_standard_number(value: str) -> None:
    raise ValueError(f"JSONで使用できない数値です: {value}")


def validate_finite_numbers(value: object, location: str = "root") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{location} にNaNまたはInfinityがあります")
    if isinstance(value, dict):
        for key, child in value.items():
            validate_finite_numbers(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_finite_numbers(child, f"{location}[{index}]")


def parse_json_text(text: str, source: str) -> dict:
    try:
        value = json.loads(text, parse_constant=reject_non_standard_number)
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{source} は有効なJSONではありません: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{source} の最上位はJSONオブジェクトである必要があります")
    validate_finite_numbers(value)
    return value


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return parse_json_text(file.read(), str(path))


def extract_date(report: dict) -> str:
    candidates = [
        report.get("report_date"),
        report.get("date"),
        report.get("updated_at"),
    ]
    for candidate in candidates:
        match = re.search(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})", str(candidate or ""))
        if match:
            return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    raise ValueError("report_date または updated_at から日付を取得できません")


def validate_report(report: dict) -> None:
    required = ["executive_summary", "market_overview", "news", "scenarios", "data_quality"]
    missing = [key for key in required if key not in report]
    if missing:
        raise ValueError("report.json 必須項目不足: " + ", ".join(missing))


def extract_market_update_date(market: dict) -> str | None:
    value = market.get("updated_at")
    match = re.search(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})", str(value or ""))
    if not match:
        return None
    return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"


def git_file(commit: str, path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def backfill_from_git() -> None:
    """Restore older report/market pairs still present in Git history."""
    if not (ROOT / ".git").exists():
        return
    result = subprocess.run(
        ["git", "log", "--format=%H", "--", "data/report.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return

    restored = 0
    for commit in reversed(result.stdout.splitlines()):
        report_bytes = git_file(commit, "data/report.json")
        market_bytes = git_file(commit, "data/market.json")
        if not report_bytes or not market_bytes:
            continue
        try:
            report = parse_json_text(report_bytes.decode("utf-8-sig"), "Git履歴のreport.json")
            market = parse_json_text(market_bytes.decode("utf-8-sig"), "Git履歴のmarket.json")
            validate_report(report)
            date_key = extract_date(report)
            market_date = extract_market_update_date(market)
            if market_date and market_date != date_key:
                continue
        except (UnicodeDecodeError, ValueError):
            continue

        destination = HISTORY_DIR / date_key
        report_history = destination / "report.json"
        market_history = destination / "market.json"
        if report_history.exists() and market_history.exists():
            continue
        destination.mkdir(parents=True, exist_ok=True)
        report_temp = destination / "report.json.tmp"
        market_temp = destination / "market.json.tmp"
        report_temp.write_bytes(report_bytes)
        market_temp.write_bytes(market_bytes)
        report_temp.replace(report_history)
        market_temp.replace(market_history)
        restored += 1
    print(f"Backfilled {restored} historical day(s) from Git")


def main() -> None:
    if not REPORT_PATH.exists() or not MARKET_PATH.exists():
        raise FileNotFoundError("data/report.json と data/market.json の両方が必要です")

    report = load_json(REPORT_PATH)
    market = load_json(MARKET_PATH)
    validate_report(report)
    date_key = extract_date(report)
    market_date = extract_market_update_date(market)

    if market_date and market_date != date_key:
        print(
            "保存待ち: report.jsonの日付 "
            f"{date_key} と market.jsonの更新日 {market_date} が一致していません"
        )
        return

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    backfill_from_git()

    destination = HISTORY_DIR / date_key
    destination.mkdir(parents=True, exist_ok=True)
    report_temp = destination / "report.json.tmp"
    market_temp = destination / "market.json.tmp"
    shutil.copy2(REPORT_PATH, report_temp)
    shutil.copy2(MARKET_PATH, market_temp)
    report_temp.replace(destination / "report.json")
    market_temp.replace(destination / "market.json")

    dates = sorted(
        path.name
        for path in HISTORY_DIR.iterdir()
        if path.is_dir()
        and re.fullmatch(r"20\d{2}-\d{2}-\d{2}", path.name)
        and (path / "report.json").exists()
        and (path / "market.json").exists()
    )

    index = {
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "latest": dates[-1] if dates else None,
        "dates": dates,
    }
    index_temp = HISTORY_DIR / "index.json.tmp"
    index_temp.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    index_temp.replace(INDEX_PATH)
    print(f"Archived {date_key}: report.json + market.json")


if __name__ == "__main__":
    main()
