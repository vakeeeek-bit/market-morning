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
MARKET_PATH = ROOT / "data" / "market.json"
HISTORY_ROOT = ROOT / "data" / "history"

EXTERNAL_SECTORS = {"自動車・輸送機", "鉄鋼・非鉄", "機械", "電機・精密", "商社・卸売"}
DOMESTIC_SECTORS = {"食品", "建設・資材", "医薬品", "情報通信・サービス", "電力・ガス", "運輸・物流", "小売", "銀行", "金融（銀行除く）", "不動産"}


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
    return_5d = None
    if len(close) >= 6:
        five_days_ago = finite(close.iloc[-6])
        if five_days_ago not in (None, 0):
            return_5d = round((latest / five_days_ago - 1) * 100, 2)
    return {
        "ticker": ticker,
        "name": name,
        "sector": sector,
        "price": round(latest, 2),
        "change_pct": round((latest / previous - 1) * 100, 2),
        "return_5d_pct": return_5d,
        "volume": int(latest_volume) if latest_volume is not None else None,
        "volume_ratio_20d": round(ratio, 2) if ratio is not None else None,
        "trading_value_proxy_yen": round(latest * latest_volume) if latest_volume is not None else None,
        "market_date": close.index[-1].strftime("%Y-%m-%d"),
        "status": "取得成功",
    }


def average_change(rows, names):
    values = [row.get("change_pct") for row in rows if row.get("name") in names and isinstance(row.get("change_pct"), (int, float))]
    return round(sum(values) / len(values), 2) if values else None


def comparison_axis(name, left_label, right_label, left_value, right_value, coverage, threshold=0.3):
    if left_value is None or right_value is None:
        return {"axis": name, "label": "判定対象外", "status": "unavailable", "reason": f"{coverage}の比較に必要な同日データが不足"}
    spread = round(left_value - right_value, 2)
    label = f"{left_label}優位" if spread >= threshold else f"{right_label}優位" if spread <= -threshold else "拮抗"
    return {
        "axis": name,
        "label": label,
        "result": label,
        "status": "estimated",
        "left_label": left_label,
        "right_label": right_label,
        "left_value": left_value,
        "right_value": right_value,
        "spread_pt": spread,
        "detail": f"{left_label} {left_value:+.2f}% ／ {right_label} {right_value:+.2f}%",
        "reason": f"相対騰落：{left_label} {left_value:+.2f}%／{right_label} {right_value:+.2f}%（差 {spread:+.2f}pt）",
        "basis": coverage,
    }


def build_market_regime(sector_rows, stock_rows, internals):
    nikkei = internals.get("nikkei_proxy_change_pct")
    topix = internals.get("topix_proxy_change_pct")
    divergence = bool(nikkei is not None and topix is not None and nikkei * topix < 0)
    if nikkei is None or topix is None:
        posture = "確認できず"
        posture_reason = "日経平均またはTOPIXの同日データが不足しています"
    elif divergence:
        posture = "指数ごとに強弱が分かれる相場"
        posture_reason = f"日経平均 {nikkei:+.2f}%に対しTOPIX {topix:+.2f}%"
    elif nikkei >= 0.3 and topix >= 0.3:
        posture = "主要指数がそろって上昇"
        posture_reason = f"日経平均 {nikkei:+.2f}%、TOPIX {topix:+.2f}%"
    elif nikkei <= -0.3 and topix <= -0.3:
        posture = "主要指数がそろって下落"
        posture_reason = f"日経平均 {nikkei:+.2f}%、TOPIX {topix:+.2f}%"
    else:
        posture = "方向感は限定的"
        posture_reason = f"日経平均 {nikkei:+.2f}%、TOPIX {topix:+.2f}%で値動きが小幅です"
    return {
        "headline": posture,
        "headline_reason": posture_reason,
        "scoreboard": [
            {"label": "日経平均", "value": nikkei, "unit": "%", "meaning": "プラスなら日経平均型が上昇"},
            {"label": "TOPIX", "value": topix, "unit": "%", "meaning": "市場全体の方向"},
        ],
        "divergence_alert": f"主要指数が逆方向：{posture_reason}" if divergence else None,
        "dimensions": [],
        "method_note": "市場観は日経平均・TOPIX連動ETFの同日騰落だけで判定します。34銘柄を市場全体の広がりには使用しません。",
    }


def driver_item(market, key, title, category, affected, evaluator, caveat=None, market_reach=1, news_importance=1):
    row = market.get("markets", {}).get(key, {}) if isinstance(market, dict) else {}
    if row.get("status") != "取得成功" or not isinstance(row.get("change_pct"), (int, float)):
        return {"driver": title, "category": category, "assessment": "確認できず", "status": "unavailable", "reason": "確認済みの同系列データがない", "affected_sectors": affected}
    assessment, transmission = evaluator(row)
    reason = f"{row.get('name', title)} {row.get('price')}、前日比 {row['change_pct']:+.2f}%（{row.get('market_date', '日付不明')}）→ {transmission}"
    if caveat:
        reason += f"。{caveat}"
    move = abs(row.get("change_pct") or 0)
    if key == "us10y":
        move = abs(row.get("change") or 0) * 20
    move_level = 3 if move >= 1.5 else 2 if move >= 0.5 else 1
    return {"driver": title, "category": category, "assessment": assessment, "status": "observed", "market_value": row.get("price"), "change_pct": row.get("change_pct"), "transmission_path": transmission, "reason": reason, "affected_sectors": affected, "market_date": row.get("market_date"), "selection_factors": {"日本株への波及範囲": market_reach, "影響業種数": len(affected), "ニュース重要度": news_importance, "値動き": move_level}}


def build_key_drivers(market, japan_market_date):
    candidates = [
        driver_item(market, "usdjpy", "ドル円", "為替", ["自動車・輸送機", "機械", "小売"], lambda row: ("外需に追い風／輸入コストに向かい風" if row["change_pct"] > 0.3 else "外需に向かい風／輸入コストに追い風" if row["change_pct"] < -0.3 else "中立", "輸出採算と輸入コストが変化"), market_reach=3, news_importance=3),
        driver_item(market, "us10y", "米10年金利", "金利", ["電機・精密", "情報通信・サービス", "銀行"], lambda row: ("高PER株に追い風" if row.get("change", 0) < -0.02 else "高PER株に向かい風" if row.get("change", 0) > 0.02 else "中立", "高PER株の割引率と銀行収益期待が変化"), market_reach=3, news_importance=3),
        driver_item(market, "sox", "米国半導体株", "海外株", ["電機・精密", "機械"], lambda row: ("追い風" if row["change_pct"] > 0.5 else "向かい風" if row["change_pct"] < -0.5 else "中立", "国内半導体関連の投資家心理に波及"), market_reach=3, news_importance=3),
        driver_item(market, "nasdaq100", "米国大型ハイテク株", "海外株", ["電機・精密", "情報通信・サービス"], lambda row: ("追い風" if row["change_pct"] > 0.5 else "向かい風" if row["change_pct"] < -0.5 else "中立", "国内グロース株の投資家心理に波及"), market_reach=2, news_importance=2),
        driver_item(market, "wti", "原油", "商品", ["エネルギー資源", "運輸・物流", "素材・化学"], lambda row: ("運輸に追い風／資源に向かい風" if row["change_pct"] < -0.5 else "資源に追い風／運輸に向かい風" if row["change_pct"] > 0.5 else "中立", "資源収益と燃料コストが変化"), "継続先物のため限月付き清算値としては扱いません", market_reach=2, news_importance=2),
        driver_item(market, "gold", "金", "商品", ["鉄鋼・非鉄", "商社・卸売"], lambda row: ("関連株に追い風候補" if row["change_pct"] > 0.7 else "関連株に向かい風候補" if row["change_pct"] < -0.7 else "影響限定", "貴金属関連の収益期待が変化")),
        driver_item(market, "copper", "銅", "商品", ["鉄鋼・非鉄", "機械", "商社・卸売"], lambda row: ("関連株に追い風候補" if row["change_pct"] > 0.7 else "関連株に向かい風候補" if row["change_pct"] < -0.7 else "影響限定", "非鉄・設備投資関連の収益期待が変化"), "継続先物だけで中国実需を断定しません"),
    ]
    # 不透明な合算点は作らず、未反映 → 波及範囲 → ニュース重要度 → 値動きの順で選ぶ。
    for item in candidates:
        item["pricing_status"] = "日本株現物に未反映" if item.get("market_date") and japan_market_date and item["market_date"] > japan_market_date else "同日または既反映の参考値"
        item["selection_factors"] = {"日本株現物への織り込み": item["pricing_status"], **item.get("selection_factors", {})}
    def selection_key(item):
        factors = item.get("selection_factors", {})
        return (item.get("status") == "observed", item.get("pricing_status") == "日本株現物に未反映", factors.get("日本株への波及範囲", 0), factors.get("ニュース重要度", 0), factors.get("値動き", 0))
    drivers = sorted(candidates, key=selection_key, reverse=True)[:4]
    change_conditions = {
        "ドル円": "為替が反転し、自動車・機械の相対方向も変われば見方を修正する",
        "米10年金利": "金利の方向が反転し、電機・精密や銀行の反応も変われば見方を修正する",
        "米国半導体株": "米半導体株が反転するか、日本の電機・精密が追随しなければ影響を弱く見る",
        "米国大型ハイテク株": "米国ハイテク株が反転し、日本のグロース株が追随しなければ影響を弱く見る",
        "銅": "銅の方向が継続せず、非鉄・機械も反応しなければ影響材料から外す",
        "金": "金の方向が継続せず、貴金属関連も反応しなければ影響材料から外す",
        "原油": "原油が反発するか、運輸・物流が相対優位にならなければコスト追い風の見方を修正する",
    }
    for item in drivers:
        item["change_condition"] = change_conditions[item["driver"]]
        if item.get("pricing_status") == "日本株現物に未反映":
            item["reason"] += f"。日本株現物の基準日{japan_market_date}より新しく、次回取引の監視材料"
    return drivers


def build_rotation(sector_rows, internals):
    pairs = [
        comparison_axis("外需と内需", "外需", "内需", average_change(sector_rows, EXTERNAL_SECTORS), average_change(sector_rows, DOMESTIC_SECTORS), "固定セクターETFの相対騰落"),
    ]
    return {"label": "どちらが強い？", "items": pairs, "note": "17業種ETFを外需型・内需型に分けた相対騰落です。投資主体別の資金流入を示すものではありません。"}


def build_sector_quality(sector_rows, stock_rows, topix):
    output = []
    topix_5d = topix.get("return_5d_pct") if topix else None
    for sector in sector_rows:
        volume_ratio = sector.get("volume_ratio_20d")
        volume_label = f"出来高：普段の{volume_ratio:.2f}倍" if isinstance(volume_ratio, (int, float)) else "出来高：確認できず"
        return_5d = sector.get("return_5d_pct")
        relative_today = round(sector.get("change_pct") - topix.get("change_pct"), 2) if isinstance(sector.get("change_pct"), (int, float)) and topix and isinstance(topix.get("change_pct"), (int, float)) else None
        relative_5d = None
        persistence = "確認できず"
        if isinstance(return_5d, (int, float)) and isinstance(topix_5d, (int, float)):
            relative_5d = round(return_5d - topix_5d, 2)
            persistence = "直近5日：TOPIXより強い" if relative_5d >= 0.5 else "直近5日：TOPIXより弱い" if relative_5d <= -0.5 else "直近5日：TOPIXと同程度"
        quality = "強い" if relative_today is not None and relative_today >= 0.5 else "弱い" if relative_today is not None and relative_today <= -0.5 else "市場並み"
        momentum = f"TOPIXより{abs(relative_today):.2f}pt強い" if relative_today is not None and relative_today > 0 else f"TOPIXより{abs(relative_today):.2f}pt弱い" if relative_today is not None and relative_today < 0 else "TOPIX並み"
        attention = bool((relative_today is not None and abs(relative_today) >= 1.5) or (isinstance(volume_ratio, (int, float)) and volume_ratio >= 2.0))
        output.append({"sector": sector.get("name"), "change_pct": sector.get("change_pct"), "relative_today_pct": relative_today, "quality": quality, "attention": attention, "volume_confirmation": volume_label, "volume_ratio_20d": volume_ratio, "persistence": persistence, "return_5d_pct": return_5d, "relative_5d_pct": relative_5d, "axes": {"momentum": {"label": momentum, "value": relative_today, "rule": "業種ETFの当日騰落をTOPIXと比較し、差±0.5ptで強弱を判定"}, "activity": {"label": volume_label, "value": volume_ratio, "rule": "業種ETFの出来高を直近20日平均と比較"}, "persistence": {"label": persistence, "value": relative_5d, "rule": "業種ETFの5日騰落をTOPIXと比較し、差±0.5ptで判定"}}, "comment": f"当日{sector.get('change_pct', 0):+.2f}%（TOPIX比{relative_today:+.2f}pt）。{volume_label}。{persistence}。" if relative_today is not None else f"当日{sector.get('change_pct', 0):+.2f}%。TOPIX比は確認できません。", "coverage_note": "業種ETF自身の値動き・出来高・5日推移による評価。個別監視銘柄は評価に使用せず、総合点も算出しません。"})
    return sorted(output, key=lambda row: row.get("relative_today_pct") if row.get("relative_today_pct") is not None else -999, reverse=True)


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


def aligned_fallback_snapshot(snapshot, expected_market_date, market=None, report=None):
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
    enrich_investor_view(result, market or {}, report or {})
    return result


def scenario_review(report, sector_rows, market_date, ready=True, blocked_reason=None, holiday=False):
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
        "title": "昨日のシナリオ検証 → 今日への修正",
        "basis": "前回レポートの注目業種をTOPIX-17業種ETFの実績と照合し、次の取引日へ見方を修正",
        "status": "検証可能" if checks else "対象なし",
        "checks": checks,
        "previous_condition": " / ".join(report.get("japan_quick_view", {}).get("unpriced_materials", [])) if isinstance(report, dict) and report.get("japan_quick_view", {}).get("unpriced_materials") else "前回レポートに明示された条件なし",
        "condition_result": "発生条件を自動判定できる一次データがないため、確認できず",
        "market_reaction": " / ".join(f"{row['name']} {row['change_pct']:+.2f}%" for row in ranked[:3]) if ranked else "確認できず",
        "unexpected_gap": " / ".join(f"{item['sector']}は{item['result']}" for item in checks) if checks else "比較対象なし",
        "gap_reason": "業種ETFの結果だけでは個別ニュースとの因果を分離できないため、理由は断定しません",
        "revision": "注目業種の相対順位を踏まえて強弱判断を更新" if checks else "修正対象なし",
        "today_watch": report.get("japan_quick_view", {}).get("unpriced_materials", []) if isinstance(report, dict) else [],
        "note": "予想の○×採点ではありません。前回の見方と実績の差から、今日の監視点を修正します。",
    }
    if holiday:
        result["status"] = "休場・検証保留"
        result["checks"] = []
        result["note"] = "東証現物は休場です。前営業日の実績は保持し、次の取引日に見方を修正します。"
        result["market_reaction"] = "休場のため新しい現物株の結果はありません"
        result["revision"] = "先物・海外材料は監視し、現物株の判断は次の取引日まで保留"
    elif blocked_reason:
        result["status"] = "判定保留"
        result["checks"] = []
        result["note"] = blocked_reason
        result["market_reaction"] = "日付不一致のため比較しません"
        result["revision"] = "データ整合後に再検証"
    elif not ready:
        result["status"] = "大引け待ち"
        result["checks"] = []
        result["note"] = "取引中のため検証しません。大引け後の更新で前回の見方を再点検します"
    return result


def build_morning_summary(regime, drivers, sector_quality):
    observed = [item for item in drivers if item.get("status") == "observed"]
    tailwinds = [f"{item['driver']}：{item['assessment']}" for item in observed if "追い風" in item.get("assessment", "")][:2]
    headwinds = [f"{item['driver']}：{item['assessment']}" for item in observed if "向かい風" in item.get("assessment", "")][:2]
    focus = [row["sector"] for row in sector_quality if row.get("quality") == "強い"][:3]
    return {
        "stance": regime.get("headline", "確認できず"),
        "reason": regime.get("headline_reason", "主要指数のデータを確認できません"),
        "tailwinds": tailwinds or ["明確な追い風は確認できず"],
        "headwinds": headwinds or ["明確な向かい風は確認できず"],
        "focus_sectors": focus or ["TOPIX比で明確に強い業種は確認できず"],
    }


def enrich_investor_view(result, market, report):
    sector_rows = result.get("sector_ranking", [])
    stock_rows = [row for group in result.get("sector_stock_ranking", []) for row in group.get("stocks", [])]
    internals = result.get("market_internals", {})
    topix = next((row for row in sector_rows if row.get("ticker") == "1306.T"), None)
    result["market_regime"] = build_market_regime(sector_rows, stock_rows, internals)
    result["key_drivers"] = build_key_drivers(market, result.get("market_date"))
    result["rotation_read"] = build_rotation(sector_rows, internals)
    benchmark_rows = result.get("benchmark_rows", [])
    topix_benchmark = next((row for row in benchmark_rows if row.get("ticker") == "1306.T"), topix)
    if topix_benchmark is None and isinstance(internals.get("topix_proxy_change_pct"), (int, float)):
        topix_benchmark = {"change_pct": internals["topix_proxy_change_pct"], "return_5d_pct": None}
    result["sector_quality"] = build_sector_quality(sector_rows, stock_rows, topix_benchmark)
    result["morning_summary"] = build_morning_summary(result["market_regime"], result["key_drivers"], result["sector_quality"])
    current_review = result.get("scenario_review", {})
    result["scenario_review"] = scenario_review(
        report, sector_rows, result.get("market_date"),
        ready=current_review.get("status") != "大引け待ち",
        blocked_reason=current_review.get("note") if current_review.get("status") == "判定保留" else None,
        holiday=result.get("data_state", {}).get("kind") == "holiday",
    )
    result.pop("monitoring_points", None)
    result["methodology"] = {
        "tier_1_existing_data": ["今日の市場観", "主要材料", "外需と内需の比較", "業種ETFのセクター3軸評価", "昨日のシナリオ検証と今日への修正"],
        "tier_2_light_fetch": ["Growth/Value指数", "小型株指数", "半導体専用指数・ETF"],
        "tier_3_new_api_or_ai": ["投資主体別リアルタイム資金フロー", "ニュース因果の自動生成", "大規模な類似局面バックテスト"],
        "implemented_tier": 1,
    }
    result.pop("benchmark_rows", None)
    return result


def build(download, universe, report, market, now):
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
    expected_market_date = (
        report.get("target_market_date") or report.get("report_date")
        if isinstance(report, dict) else None
    )
    report_text = json.dumps(report, ensure_ascii=False) if isinstance(report, dict) else ""
    report_date = report.get("report_date") if isinstance(report, dict) else None
    holiday = bool(
        report_date
        and expected_market_date
        and report_date != expected_market_date
        and "休場" in report_text
    )
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
    data_phase = "休場" if holiday and not blocked_reason else "データ異常・検証保留" if blocked_reason else "大引け後" if review_ready else "取引中暫定"
    data_state = {
        "kind": "data_error" if blocked_reason else "holiday" if holiday else "normal",
        "label": "データ異常" if blocked_reason else "東証現物は休場" if holiday else "通常取引日",
        "message": blocked_reason or (f"{report_date}は休場。{expected_market_date}の前営業日データを表示" if holiday else "取引日データを正常取得"),
    }
    sector_rank = sorted(valid_sectors, key=lambda row: row["change_pct"], reverse=True)
    stock_groups = []
    for sector in universe["sectors"]:
        rows = sorted([row for row in valid_stocks if row["sector"] == sector["name"]], key=lambda row: row["change_pct"], reverse=True)
        stock_groups.append({"sector": sector["name"], "stocks": rows})
    topix = next((row for row in valid_benchmarks if row["ticker"] == "1306.T"), None)
    nikkei = next((row for row in valid_benchmarks if row["ticker"] == "1321.T"), None)
    result = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S JST"),
        "market_date": market_date,
        "data_phase": data_phase,
        "data_state": data_state,
        "source": "Yahoo Finance via yfinance（1回の一括取得）",
        "scope": "市場・セクター評価は指数連動ETFとTOPIX-17業種ETFを使用。主要監視34銘柄は銘柄ランキングだけに使用",
        "sector_ranking": sector_rank,
        "sector_stock_ranking": stock_groups,
        "benchmark_rows": valid_benchmarks,
        "trading_value_ranking": sorted(valid_stocks, key=lambda row: row.get("trading_value_proxy_yen") or -1, reverse=True)[:10],
        "volume_surge_ranking": sorted(valid_stocks, key=lambda row: row.get("volume_ratio_20d") or -1, reverse=True)[:10],
        "market_internals": {
            "nikkei_proxy_change_pct": nikkei.get("change_pct") if nikkei else None,
            "topix_proxy_change_pct": topix.get("change_pct") if topix else None,
            "relative": "日付不一致" if not benchmark_aligned else "日経225優位" if nikkei and topix and nikkei["change_pct"] > topix["change_pct"] else "TOPIX優位" if nikkei and topix else "確認できず",
        },
        "scenario_review": scenario_review(report, sector_rank, expected_market_date, review_ready, blocked_reason, holiday),
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
    enrich_investor_view(result, market, report)
    return result


def meets_quality_gate(result):
    quality = result.get("data_quality", {})
    return quality.get("sector_available", 0) >= 12 and quality.get("stock_available", 0) >= 24


def main():
    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    report = json.loads(JAPAN_REPORT_PATH.read_text(encoding="utf-8")) if JAPAN_REPORT_PATH.exists() else {}
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8")) if MARKET_PATH.exists() else {}
    tickers = list(universe["benchmarks"][key]["ticker"] for key in universe["benchmarks"])
    for sector in universe["sectors"]:
        tickers.append(sector["etf"])
        tickers.extend(stock["ticker"] for stock in sector["stocks"])
    download = yf.download(tickers=sorted(set(tickers)), period="35d", interval="1d", group_by="ticker", auto_adjust=False, progress=False, threads=8, timeout=10)
    result = build(download, universe, report, market, datetime.now(ZoneInfo("Asia/Tokyo")))
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
            fallback = aligned_fallback_snapshot(candidate, expected, market, report)
            if fallback:
                OUTPUT_PATH.write_text(json.dumps(fallback, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
                print(f"取得日不一致のため、整合済みの{expected}データを維持しました")
                return
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
