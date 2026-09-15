#!/usr/bin/env python3
"""Build low-cost Japan market internals from one batched daily-price request."""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "data" / "japan-universe.json"
OUTPUT_PATH = ROOT / "data" / "japan-market.json"
JAPAN_REPORT_PATH = ROOT / "data" / "japan-stocks.json"
HISTORY_ROOT = ROOT / "data" / "history"


def finite(value):
    number = float(value)
    return number if math.isfinite(number) else None


def series_for(download, ticker, field):
    try:
        series = download[ticker][field] if ticker in download.columns.levels[0] else download[field][ticker]
        return series.dropna()
    except (KeyError, AttributeError):
        return None


def calculate_row(download, ticker, name, sector=None):
    close = series_for(download, ticker, "Close")
    volume = series_for(download, ticker, "Volume")
    if close is None or len(close) < 2:
        return {"ticker": ticker, "name": name, "sector": sector, "status": "確認できず"}
    latest, previous = finite(close.iloc[-1]), finite(close.iloc[-2])
    if latest is None or previous in (None, 0):
        return {"ticker": ticker, "name": name, "sector": sector, "status": "確認できず"}
    latest_volume = finite(volume.iloc[-1]) if volume is not None and len(volume) else None
    baseline = None
    if volume is not None and len(volume) >= 2:
        prior = volume.iloc[max(0, len(volume) - 21):-1].dropna()
        if len(prior):
            baseline = finite(prior.mean())
    ratio = latest_volume / baseline if latest_volume is not None and baseline not in (None, 0) else None
    return {
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "price": round(latest, 2),
        "change_pct": round((latest / previous - 1) * 100, 2),
        "volume": int(latest_volume) if latest_volume is not None else None,
        "volume_ratio_20d": round(ratio, 2) if ratio is not None else None,
        "trading_value_proxy_yen": round(latest * latest_volume) if latest_volume is not None else None,
        "market_date": close.index[-1].strftime("%Y-%m-%d"),
        "status": "取得成功",
    }


def dominant_market_date(rows):
    dates = [row.get("market_date") for row in rows if row.get("status") == "取得成功" and row.get("market_date")]
    if not dates:
        return None
    return Counter(dates).most_common(1)[0][0]


def rows_for_date(rows, market_date):
    return [row for row in rows if row.get("status") == "取得成功" and row.get("market_date") == market_date]


def snapshot_dates(snapshot):
    sector_rows = snapshot.get("sector_ranking", []) if isinstance(snapshot, dict) else []
    stock_rows = []
    if isinstance(snapshot, dict):
        for group in snapshot.get("sector_stock_ranking", []):
            stock_rows.extend(group.get("stocks", []))
    return dominant_market_date(sector_rows), dominant_market_date(stock_rows)


def aligned_fallback_snapshot(snapshot, expected_market_date):
    sector_date, stock_date = snapshot_dates(snapshot)
    if not expected_market_date or sector_date != expected_market_date or stock_date != expected_market_date:
        return None
    result = dict(snapshot)
    quality = dict(result.get("data_quality", {}))
    quality["date_alignment"] = {
        "expected_market_date": expected_market_date,
        "sector_market_date": sector_date,
        "stock_market_date": stock_date,
        "benchmark_market_date": None,
        "aligned": True,
        "benchmark_aligned": False,
    }
    result["data_quality"] = quality
    result["market_date"] = expected_market_date
    result["data_phase"] = "大引け後"
    return result


def scenario_review(report, sector_rows, market_date, ready=True, blocked_reason=None):
    focus = report.get("japan_quick_view", {}).get("focus_sectors", []) if isinstance(report, dict) else []
    aliases = {
        "石油・鉱業": "エネルギー資源", "商社": "商社・卸売", "半導体": "電機・精密",
        "空運・陸運": "運輸・物流", "空運": "運輸・物流", "陸運": "運輸・物流",
        "電力・ガス": "電力・ガス", "銀行": "銀行", "保険": "金融（銀行除く）",
        "不動産": "不動産", "化学": "素材・化学", "鉄鋼・非鉄": "鉄鋼・非鉄",
    }
    watched = []
    for item in focus:
        mapped = aliases.get(item, item if any(row.get("name") == item for row in sector_rows) else None)
        if mapped and mapped not in watched:
            watched.append(mapped)
    valid = [row for row in sector_rows if row.get("status") == "取得成功"]
    ranked = sorted(valid, key=lambda row: row["change_pct"], reverse=True)
    top = {row["name"] for row in ranked[:3]}
    bottom = {row["name"] for row in ranked[-3:]}
    checks = [{"sector": name, "result": "上位3" if name in top else "下位3" if name in bottom else "中位"} for name in watched]
    result = {
        "market_date": market_date,
        "basis": "朝レポートの注目業種を、TOPIX-17業種ETFの当日騰落順位と機械照合",
        "status": "判定可能" if checks else "対象なし",
        "checks": checks,
        "note": "方向予想の的中率ではなく、朝の注目業種が実際に相対的な上位・下位へ現れたかを確認",
    }
    if blocked_reason:
        result["status"] = "判定保留"
        result["checks"] = []
        result["note"] = blocked_reason
    elif not ready:
        result["status"] = "大引け待ち"
        result["checks"] = []
        result["note"] = "取引中のため判定しません。平日15:45 JSTの更新後に機械照合します"
    return result


def build(download, universe, report, now):
    sectors = []
    stocks = []
    for sector in universe["sectors"]:
        sectors.append(calculate_row(download, sector["etf"], sector["name"], sector["name"]))
        for stock in sector["stocks"]:
            stocks.append(calculate_row(download, stock["ticker"], stock["name"], sector["name"]))
    benchmarks = [calculate_row(download, value["ticker"], value["name"]) for value in universe["benchmarks"].values()]
    fetched_sectors = [row for row in sectors if row.get("status") == "取得成功"]
    fetched_stocks = [row for row in stocks if row.get("status") == "取得成功"]
    fetched_benchmarks = [row for row in benchmarks if row.get("status") == "取得成功"]
    sector_date = dominant_market_date(fetched_sectors)
    stock_date = dominant_market_date(fetched_stocks)
    benchmark_date = dominant_market_date(fetched_benchmarks)
    valid_sectors = rows_for_date(fetched_sectors, sector_date)
    valid_stocks = rows_for_date(fetched_stocks, stock_date)
    valid_benchmarks = rows_for_date(fetched_benchmarks, benchmark_date)
    expected_market_date = report.get("report_date") if isinstance(report, dict) else None
    market_date = stock_date or sector_date
    date_aligned = bool(expected_market_date and sector_date == stock_date == expected_market_date)
    benchmark_aligned = bool(stock_date and benchmark_date == stock_date)
    today = now.strftime("%Y-%m-%d")
    after_close = (now.hour, now.minute) >= (15, 30)
    review_ready = bool(date_aligned and market_date and (market_date < today or after_close))
    blocked_reason = None
    if not date_aligned:
        blocked_reason = (
            "日付が一致しないため判定しません。"
            f"朝レポート={expected_market_date or '確認できず'}、"
            f"セクター={sector_date or '確認できず'}、銘柄={stock_date or '確認できず'}"
        )
    data_phase = "日付不一致・判定保留" if blocked_reason else "大引け後" if review_ready else "取引中暫定"
    sector_rank = sorted(valid_sectors, key=lambda row: row["change_pct"], reverse=True)
    stock_groups = []
    for sector in universe["sectors"]:
        rows = sorted([row for row in valid_stocks if row["sector"] == sector["name"]], key=lambda row: row["change_pct"], reverse=True)
        stock_groups.append({"sector": sector["name"], "stocks": rows})
    advancing = sum(row["change_pct"] > 0 for row in valid_stocks)
    declining = sum(row["change_pct"] < 0 for row in valid_stocks)
    unchanged = len(valid_stocks) - advancing - declining
    topix = next((row for row in valid_benchmarks if row["ticker"] == "1306.T"), None)
    nikkei = next((row for row in valid_benchmarks if row["ticker"] == "1321.T"), None)
    return {
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S JST"),
        "market_date": market_date,
        "data_phase": data_phase,
        "source": "Yahoo Finance via yfinance（1回の一括取得）",
        "scope": "TOPIX-17業種ETFと各業種の主要監視2銘柄。全上場銘柄・東証公式統計ではない",
        "sector_ranking": sector_rank,
        "sector_stock_ranking": stock_groups,
        "trading_value_ranking": sorted(valid_stocks, key=lambda row: row.get("trading_value_proxy_yen") or -1, reverse=True)[:10],
        "volume_surge_ranking": sorted(valid_stocks, key=lambda row: row.get("volume_ratio_20d") or -1, reverse=True)[:10],
        "market_internals": {
            "universe_size": len(stocks), "available": len(valid_stocks),
            "advancing": advancing, "declining": declining, "unchanged": unchanged,
            "breadth_pct": round((advancing - declining) / len(valid_stocks) * 100, 1) if valid_stocks else None,
            "nikkei_proxy_change_pct": nikkei.get("change_pct") if nikkei else None,
            "topix_proxy_change_pct": topix.get("change_pct") if topix else None,
            "relative": "日付不一致" if not benchmark_aligned else "日経225優位" if nikkei and topix and nikkei["change_pct"] > topix["change_pct"] else "TOPIX優位" if nikkei and topix else "確認できず",
        },
        "scenario_review": scenario_review(report, sector_rank, expected_market_date, review_ready, blocked_reason),
        "data_quality": {
            "sector_total": len(sectors), "sector_available": len(valid_sectors),
            "stock_total": len(stocks), "stock_available": len(valid_stocks),
            "date_alignment": {
                "expected_market_date": expected_market_date,
                "sector_market_date": sector_date,
                "stock_market_date": stock_date,
                "benchmark_market_date": benchmark_date,
                "aligned": date_aligned,
                "benchmark_aligned": benchmark_aligned,
            },
        },
    }


def meets_quality_gate(result):
    quality = result.get("data_quality", {})
    return quality.get("sector_available", 0) >= 12 and quality.get("stock_available", 0) >= 24


def main():
    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    report = json.loads(JAPAN_REPORT_PATH.read_text(encoding="utf-8")) if JAPAN_REPORT_PATH.exists() else {}
    tickers = list(universe["benchmarks"][key]["ticker"] for key in universe["benchmarks"])
    for sector in universe["sectors"]:
        tickers.append(sector["etf"])
        tickers.extend(stock["ticker"] for stock in sector["stocks"])
    download = yf.download(tickers=sorted(set(tickers)), period="35d", interval="1d", group_by="ticker", auto_adjust=False, progress=False, threads=8, timeout=10)
    result = build(download, universe, report, datetime.now(ZoneInfo("Asia/Tokyo")))
    if not meets_quality_gate(result):
        quality = result["data_quality"]
        raise RuntimeError(
            "品質ゲート未達のため既存データを維持します: "
            f"sector={quality['sector_available']}/{quality['sector_total']}, "
            f"stock={quality['stock_available']}/{quality['stock_total']}"
        )
    alignment = result.get("data_quality", {}).get("date_alignment", {})
    if not alignment.get("aligned"):
        expected = alignment.get("expected_market_date")
        candidates = []
        if OUTPUT_PATH.exists():
            candidates.append(json.loads(OUTPUT_PATH.read_text(encoding="utf-8")))
        archive_path = HISTORY_ROOT / str(expected) / "japan-market.json"
        if expected and archive_path.exists():
            candidates.append(json.loads(archive_path.read_text(encoding="utf-8")))
        for candidate in candidates:
            fallback = aligned_fallback_snapshot(candidate, expected)
            if fallback:
                OUTPUT_PATH.write_text(json.dumps(fallback, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
                print(f"取得日不一致のため、整合済みの{expected}データを維持しました")
                return
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
