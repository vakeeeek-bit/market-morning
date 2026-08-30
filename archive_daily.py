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


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"{path} の最上位はJSONオブジェクトである必要があります")
    return value


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
            report = json.loads(report_bytes.decode("utf-8-sig"))
            market = json.loads(market_bytes.decode("utf-8-sig"))
            if not isinstance(report, dict) or not isinstance(market, dict):
                continue
            validate_report(report)
            date_key = extract_date(report)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue

        destination = HISTORY_DIR / date_key
        report_history = destination / "report.json"
        market_history = destination / "market.json"
        if report_history.exists() and market_history.exists():
            continue
        destination.mkdir(parents=True, exist_ok=True)
        report_history.write_bytes(report_bytes)
        market_history.write_bytes(market_bytes)
        restored += 1
    print(f"Backfilled {restored} historical day(s) from Git")


def main() -> None:
    if not REPORT_PATH.exists() or not MARKET_PATH.exists():
        raise FileNotFoundError("data/report.json と data/market.json の両方が必要です")

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    backfill_from_git()

    report = load_json(REPORT_PATH)
    load_json(MARKET_PATH)
    validate_report(report)
    date_key = extract_date(report)

    destination = HISTORY_DIR / date_key
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPORT_PATH, destination / "report.json")
    shutil.copy2(MARKET_PATH, destination / "market.json")

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
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Archived {date_key}: report.json + market.json")


if __name__ == "__main__":
    main()
