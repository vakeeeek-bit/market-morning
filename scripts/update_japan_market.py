#!/usr/bin/env python3
"""Build low-cost Japan market internals from one batched daily-price request."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "data" / "japan-universe.json"
OUTPUT_PATH = ROOT / "data" / "japan-market.json"
JAPAN_REPORT_PATH = ROOT / "data" / "japan-stocks.json"


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


def scenario_review(report, sector_rows, market_date, ready=True):
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
    if not ready:
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
    valid_sectors = [row for row in sectors if row.get("status") == "取得成功"]
    valid_stocks = [row for row in stocks if row.get("status") == "取得成功"]
    market_dates = [row["market_date"] for row in valid_sectors + valid_stocks]
    market_date = max(market_dates) if market_dates else None
    today = now.strftime("%Y-%m-%d")
    after_close = (now.hour, now.minute) >= (15, 30)
    review_ready = bool(market_date and (market_date < today or after_close))
    data_phase = "大引け後" if review_ready else "取引中暫定"
    sector_rank = sorted(valid_sectors, key=lambda row: row["change_pct"], reverse=True)
    stock_groups = []
    for sector in universe["sectors"]:
        rows = sorted([row for row in valid_stocks if row["sector"] == sector["name"]], key=lambda row: row["change_pct"], reverse=True)
        stock_groups.append({"sector": sector["name"], "stocks": rows})
    advancing = sum(row["change_pct"] > 0 for row in valid_stocks)
    declining = sum(row["change_pct"] < 0 for row in valid_stocks)
    unchanged = len(valid_stocks) - advancing - declining
    topix = next((row for row in benchmarks if row["ticker"] == "1306.T" and row.get("status") == "取得成功"), None)
    nikkei = next((row for row in benchmarks if row["ticker"] == "1321.T" and row.get("status") == "取得成功"), None)
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
            "relative": "日経225優位" if nikkei and topix and nikkei["change_pct"] > topix["change_pct"] else "TOPIX優位" if nikkei and topix else "確認できず",
        },
        "scenario_review": scenario_review(report, sector_rank, market_date, review_ready),
        "data_quality": {"sector_total": len(sectors), "sector_available": len(valid_sectors), "stock_total": len(stocks), "stock_available": len(valid_stocks)},
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
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
