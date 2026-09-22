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
CYCLICAL_SECTORS = {"エネルギー資源", "建設・資材", "素材・化学", "自動車・輸送機", "鉄鋼・非鉄", "機械", "電機・精密", "運輸・物流", "商社・卸売", "銀行", "金融（銀行除く）", "不動産"}
DEFENSIVE_SECTORS = {"食品", "医薬品", "情報通信・サービス", "電力・ガス", "小売"}


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
    external = average_change(sector_rows, EXTERNAL_SECTORS)
    domestic = average_change(sector_rows, DOMESTIC_SECTORS)
    cyclical = average_change(sector_rows, CYCLICAL_SECTORS)
    defensive = average_change(sector_rows, DEFENSIVE_SECTORS)
    breadth = internals.get("breadth_pct")
    nikkei = internals.get("nikkei_proxy_change_pct")
    topix = internals.get("topix_proxy_change_pct")
    dimensions = [
        {"axis": "成長株と割安株", "label": "判定対象外", "status": "unavailable", "reason": "同じ基準で比較できる成長株・割安株指数がないため"},
        {"axis": "大型株と小型株", "label": "判定対象外", "status": "unavailable", "reason": "小型株指数を取得しておらず、日経平均とTOPIXの差を規模差と断定できないため"},
        comparison_axis("外需と内需", "外需", "内需", external, domestic, "固定17業種ETFのうち外需5・内需10業種の代理比較"),
        comparison_axis("景気敏感とディフェンシブ", "景気敏感", "ディフェンシブ", cyclical, defensive, "固定17業種ETFのうち景気敏感12・ディフェンシブ5業種の代理比較"),
    ]
    financial = average_change(sector_rows, {"銀行", "金融（銀行除く）"})
    dimensions.extend([
        {"axis": "国内半導体", "label": "判定対象外", "status": "unavailable", "reason": "電機・精密ETFを半導体だけの値動きとして扱えないため。米国半導体は主要材料欄で確認"},
        {"axis": "金融", "label": "強い" if financial is not None and financial >= 0.3 else "弱い" if financial is not None and financial <= -0.3 else "中立", "status": "observed" if financial is not None else "unavailable", "reason": f"銀行・金融（銀行除く）ETFの平均騰落 {financial:+.2f}%" if financial is not None else "同日データ不足"},
        {"axis": "上昇・下落の広がり", "label": "広い上昇" if breadth is not None and breadth >= 20 else "広い下落" if breadth is not None and breadth <= -20 else "まちまち", "status": "observed" if breadth is not None else "unavailable", "value": breadth, "reason": f"主要監視34銘柄の値上がり{internals.get('advancing', 0)}・値下がり{internals.get('declining', 0)}、広がり指数 {breadth:+.1f}" if breadth is not None else "同日データ不足"},
    ])
    divergence = bool(nikkei is not None and topix is not None and breadth is not None and nikkei > 0 and (topix < 0 or breadth < -20))
    if divergence:
        posture = "指数主導の選別相場"
        posture_reason = f"日経225連動ETF {nikkei:+.2f}%に対しTOPIX連動ETF {topix:+.2f}%、Breadth {breadth:+.1f}"
    elif breadth is not None and breadth >= 20 and cyclical is not None and defensive is not None and cyclical > defensive:
        posture = "リスクオン寄り"
        posture_reason = "値上がりの広がりと景気敏感優位が同時に確認されたため"
    elif breadth is not None and breadth <= -20:
        posture = "リスクオフ寄り"
        posture_reason = "主要監視銘柄で値下がりが広がっているため"
    else:
        posture = "中立・方向感限定"
        posture_reason = "Breadthと業種間比較に明確な同方向シグナルがないため"
    dimensions.append({"axis": "市場全体の姿勢", "label": posture, "status": "estimated", "reason": posture_reason})
    return {
        "headline": posture,
        "headline_reason": posture_reason,
        "scoreboard": [
            {"label": "日経平均", "value": nikkei, "unit": "%", "meaning": "プラスなら日経平均型が上昇"},
            {"label": "TOPIX", "value": topix, "unit": "%", "meaning": "市場全体の方向"},
            {"label": "上昇・下落の広がり", "value": breadth, "unit": "", "meaning": "プラスほど上昇銘柄が多い"},
            {"label": "値上がり／値下がり", "value": f"{internals.get('advancing', 0)}／{internals.get('declining', 0)}", "unit": "銘柄", "meaning": "主要監視34銘柄の内訳"},
        ],
        "divergence_alert": f"指数と市場内部が乖離：{posture_reason}" if divergence else None,
        "dimensions": dimensions,
        "method_note": "実測は固定17業種ETF・主要監視34銘柄。分類軸とリスク姿勢は値動きからの推定で、投資主体別フローではありません。",
    }


def driver_item(market, key, title, category, affected, evaluator, caveat=None, weight=1.0):
    row = market.get("markets", {}).get(key, {}) if isinstance(market, dict) else {}
    if row.get("status") != "取得成功" or not isinstance(row.get("change_pct"), (int, float)):
        return {"driver": title, "category": category, "assessment": "確認できず", "status": "unavailable", "reason": "確認済みの同系列データがない", "affected_sectors": affected, "impact_score": -1}
    assessment, transmission = evaluator(row)
    reason = f"{row.get('name', title)} {row.get('price')}、前日比 {row['change_pct']:+.2f}%（{row.get('market_date', '日付不明')}）→ {transmission}"
    if caveat:
        reason += f"。{caveat}"
    raw_move = abs(row.get("change_pct") or 0)
    if key == "us10y":
        raw_move = abs(row.get("change") or 0) * 20
    return {"driver": title, "category": category, "assessment": assessment, "status": "observed", "market_value": row.get("price"), "change_pct": row.get("change_pct"), "transmission_path": transmission, "reason": reason, "affected_sectors": affected, "market_date": row.get("market_date"), "impact_score": round(raw_move * weight, 3)}


def build_key_drivers(market, japan_market_date):
    candidates = [
        driver_item(market, "usdjpy", "ドル円", "為替", ["自動車・輸送機", "機械", "小売"], lambda row: ("外需に追い風／輸入コストに向かい風" if row["change_pct"] > 0.3 else "外需に向かい風／輸入コストに追い風" if row["change_pct"] < -0.3 else "中立", "円安・円高 → 輸出採算と輸入コスト"), weight=2.0),
        driver_item(market, "us10y", "米10年金利", "金利", ["電機・精密", "情報通信・サービス", "銀行"], lambda row: ("高PER株に追い風" if row.get("change", 0) < -0.02 else "高PER株に向かい風" if row.get("change", 0) > 0.02 else "中立", "米金利 → 株式の割引率と銀行収益期待"), weight=2.0),
        driver_item(market, "sox", "米国半導体株", "海外株", ["電機・精密", "機械"], lambda row: ("追い風" if row["change_pct"] > 0.5 else "向かい風" if row["change_pct"] < -0.5 else "中立", "米半導体株 → 国内半導体関連の初期センチメント"), weight=1.5),
        driver_item(market, "nasdaq100", "米国大型ハイテク株", "海外株", ["電機・精密", "情報通信・サービス"], lambda row: ("追い風" if row["change_pct"] > 0.5 else "向かい風" if row["change_pct"] < -0.5 else "中立", "米国ハイテク株 → 国内グロース株の投資家心理")),
        driver_item(market, "wti", "原油", "商品", ["エネルギー資源", "運輸・物流", "素材・化学"], lambda row: ("運輸に追い風／資源に向かい風" if row["change_pct"] < -0.5 else "資源に追い風／運輸に向かい風" if row["change_pct"] > 0.5 else "中立", "原油価格 → 資源収益と燃料コスト"), "継続先物のため限月付き清算値としては扱いません"),
        driver_item(market, "gold", "金", "商品", ["鉄鋼・非鉄", "商社・卸売"], lambda row: ("関連株に追い風候補" if row["change_pct"] > 0.7 else "関連株に向かい風候補" if row["change_pct"] < -0.7 else "影響限定", "金価格 → 貴金属関連の収益期待")),
        driver_item(market, "copper", "銅", "商品", ["鉄鋼・非鉄", "機械", "商社・卸売"], lambda row: ("関連株に追い風候補" if row["change_pct"] > 0.7 else "関連株に向かい風候補" if row["change_pct"] < -0.7 else "影響限定", "銅価格 → 非鉄・設備投資関連の収益期待"), "継続先物だけで中国実需を断定しません"),
    ]
    drivers = sorted(candidates, key=lambda item: item.get("impact_score", -1), reverse=True)[:4]
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
        if item.get("market_date") and japan_market_date and item["market_date"] > japan_market_date:
            item["pricing_status"] = "日本株現物に未反映"
            item["reason"] += f"。日本株現物の基準日{japan_market_date}より新しく、次回取引の監視材料"
        else:
            item["pricing_status"] = "同日または既反映の参考値"
    return drivers


def build_rotation(sector_rows, internals):
    pairs = [
        comparison_axis("外需と内需", "外需", "内需", average_change(sector_rows, EXTERNAL_SECTORS), average_change(sector_rows, DOMESTIC_SECTORS), "固定セクターETFの相対騰落"),
        comparison_axis("景気敏感とディフェンシブ", "景気敏感", "ディフェンシブ", average_change(sector_rows, CYCLICAL_SECTORS), average_change(sector_rows, DEFENSIVE_SECTORS), "固定セクターETFの相対騰落"),
    ]
    nikkei, topix = internals.get("nikkei_proxy_change_pct"), internals.get("topix_proxy_change_pct")
    pairs.append(comparison_axis("日経平均とTOPIX", "日経平均", "TOPIX", nikkei, topix, "指数連動ETFの相対騰落（大型株・小型株の代理ではない）", threshold=0.2))
    pairs.append({"axis": "成長株と割安株", "label": "判定対象外", "status": "unavailable", "reason": "同じ基準のスタイル指数がないため"})
    return {"label": "値動きから見たローテーション（推定）", "items": pairs, "note": "投資主体別売買を取得していないため『資金流入』とは表現しません。"}


def build_sector_quality(sector_rows, stock_rows, topix):
    output = []
    topix_5d = topix.get("return_5d_pct") if topix else None
    for sector in sector_rows:
        members = [row for row in stock_rows if row.get("sector") == sector.get("name")]
        up = sum(row.get("change_pct", 0) > 0 for row in members)
        participation = "2銘柄とも上昇" if len(members) == 2 and up == 2 else "2銘柄とも下落" if len(members) == 2 and up == 0 else "まちまち"
        volume_ratio = sector.get("volume_ratio_20d")
        volume_label = "出来高増" if isinstance(volume_ratio, (int, float)) and volume_ratio >= 1.2 else "商い低調" if isinstance(volume_ratio, (int, float)) and volume_ratio <= 0.8 else "平常圏" if volume_ratio is not None else "確認できず"
        return_5d = sector.get("return_5d_pct")
        persistence = "確認できず"
        if isinstance(return_5d, (int, float)) and isinstance(topix_5d, (int, float)):
            relative_5d = round(return_5d - topix_5d, 2)
            persistence = "5日相対優位" if relative_5d >= 0.5 else "5日相対劣後" if relative_5d <= -0.5 else "5日ほぼ同等"
        quality = "広がりを伴う上昇" if sector.get("change_pct", 0) > 0 and up == 2 else "選別的な上昇" if sector.get("change_pct", 0) > 0 else "広がりを伴う下落" if sector.get("change_pct", 0) < 0 and up == 0 else "方向感まちまち"
        momentum = "強い" if sector.get("change_pct", 0) >= 0.7 else "弱い" if sector.get("change_pct", 0) <= -0.7 else "中立"
        breadth_label = "広い" if up == 2 else "狭い" if up == 0 else "まちまち"
        output.append({"sector": sector.get("name"), "change_pct": sector.get("change_pct"), "quality": quality, "participation": participation, "volume_confirmation": volume_label, "volume_ratio_20d": volume_ratio, "persistence": persistence, "return_5d_pct": return_5d, "axes": {"momentum": {"label": momentum, "value": sector.get("change_pct"), "rule": "当日騰落が+0.7%以上で強い、-0.7%以下で弱い"}, "breadth": {"label": breadth_label, "value": f"{up}/{len(members)}", "rule": "主要監視2銘柄のうち同方向に動いた銘柄数"}, "activity": {"label": volume_label, "value": volume_ratio, "rule": "20日平均出来高比1.2倍以上で増加、0.8倍以下で低調"}, "persistence": {"label": persistence, "value": return_5d, "rule": "5日騰落をTOPIX連動ETFと比較"}}, "comment": f"{quality}。{participation}、{volume_label}、{persistence}。", "coverage_note": "主要監視2銘柄と業種ETFによる限定評価。総合点は算出しない"})
    return sorted(output, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999, reverse=True)


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
        "previous_view": " / ".join(focus) if focus else "前回レポートに注目業種なし",
        "market_result": " / ".join(f"{row['name']} {row['change_pct']:+.2f}%" for row in ranked[:3]) if ranked else "確認できず",
        "revision": "注目業種の相対順位を踏まえて強弱判断を更新" if checks else "修正対象なし",
        "today_watch": report.get("japan_quick_view", {}).get("unpriced_materials", []) if isinstance(report, dict) else [],
        "note": "予想の○×採点ではありません。前回の見方と実績の差から、今日の監視点を修正します。",
    }
    if holiday:
        result["status"] = "休場・検証保留"
        result["checks"] = []
        result["note"] = "東証現物は休場です。前営業日の実績は保持し、次の取引日に見方を修正します。"
        result["market_result"] = "休場のため新しい現物株の結果はありません"
        result["revision"] = "先物・海外材料は監視し、現物株の判断は次の取引日まで保留"
    elif blocked_reason:
        result["status"] = "判定保留"
        result["checks"] = []
        result["note"] = blocked_reason
        result["market_result"] = "日付不一致のため比較しません"
        result["revision"] = "データ整合後に再検証"
    elif not ready:
        result["status"] = "大引け待ち"
        result["checks"] = []
        result["note"] = "取引中のため検証しません。大引け後の更新で前回の見方を再点検します"
    return result


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
    result["sector_quality"] = build_sector_quality(sector_rows, stock_rows, topix_benchmark)
    result["monitoring_points"] = [
        {"watch": item["driver"], "current_view": item["assessment"], "change_condition": item.get("change_condition", "確認できず"), "pricing_status": item.get("pricing_status", "確認できず")}
        for item in result["key_drivers"] if item.get("status") == "observed"
    ][:5]
    result["methodology"] = {
        "tier_1_existing_data": ["今日の市場観", "主要材料", "値動きから見たローテーション", "セクター4軸評価", "昨日のシナリオ検証と今日への修正"],
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
    advancing = sum(row["change_pct"] > 0 for row in valid_stocks)
    declining = sum(row["change_pct"] < 0 for row in valid_stocks)
    unchanged = len(valid_stocks) - advancing - declining
    topix = next((row for row in valid_benchmarks if row["ticker"] == "1306.T"), None)
    nikkei = next((row for row in valid_benchmarks if row["ticker"] == "1321.T"), None)
    result = {
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S JST"),
        "market_date": market_date,
        "data_phase": data_phase,
        "data_state": data_state,
        "source": "Yahoo Finance via yfinance（1回の一括取得）",
        "scope": "TOPIX-17業種ETFと各業種の主要監視2銘柄。全上場銘柄・東証公式統計ではない",
        "sector_ranking": sector_rank,
        "sector_stock_ranking": stock_groups,
        "benchmark_rows": valid_benchmarks,
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
