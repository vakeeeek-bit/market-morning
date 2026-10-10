"""Persist news snapshots and rebuild availability indexes without inventing reports."""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from archive_daily import history_entry

ROOT = Path(__file__).resolve().parents[1]

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

def sync(root=ROOT):
    data = root / "data"
    history = data / "history"
    news = json.loads((data / "news.json").read_text())
    day = news["report_date"]
    datetime.strptime(day, "%Y-%m-%d")
    save(history / day / "news.json", news)
    entries = []
    for directory in sorted(history.iterdir()):
        if not directory.is_dir():
            continue
        try:
            datetime.strptime(directory.name, "%Y-%m-%d")
        except ValueError:
            continue
        entry = history_entry(directory)
        entry["has_news"] = (directory / "news.json").is_file()
        entry["has_candidate"] = (data / "candidates" / directory.name / "report.json").is_file()
        entries.append(entry)
    now = datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
    old = json.loads((history / "index.json").read_text()) if (history / "index.json").exists() else {}
    old.update(updated_at=now, dates=[e["date"] for e in entries], entries=entries)
    # latest is the latest saved report, not the latest partial market/news date.
    save(history / "index.json", old)
    dates = [e["date"] for e in entries if e["has_news"]]
    index_path = data / "news-history.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    index.update(updated_at=now, dates=dates, coverage_status="partial")
    save(index_path, index)
    market = json.loads((data / 'market.json').read_text()) if (data / 'market.json').exists() else {}
    today = now[:10]
    attempt_path = data / 'collection-attempts' / f'{today}-market.json'
    attempt = json.loads(attempt_path.read_text()) if attempt_path.exists() else None
    status = json.loads((data / 'status.json').read_text()) if (data / 'status.json').exists() else {}
    succeeded_today = status.get('status') == 'success' and str(status.get('updated_at', '')).startswith(today)
    save(data / 'collection-status.json', {
        'checked_at': now,
        'market_attempt_status': 'success' if succeeded_today else ('FAIL' if attempt else 'not_confirmed'),
        'market_attempt_note': '当日の収集成功記録あり。基準日と総合品質は別途確認。' if succeeded_today else ('再取得に失敗。取得済みの正本を保持。失敗の詳細は collection-attempts に保存。' if attempt else '当日成功記録なし。前回取得値の基準日を確認してください。'),
        'market_updated_at': market.get('updated_at'),
        'japan_calendar_note': '土日：現物の新しい取引結果はありません。直近取引日の実績を掲載。' if datetime.fromisoformat(now).weekday() >= 5 else '取引日程と実績の基準日を別々に確認してください。',
    })
    return entries

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    sync()
