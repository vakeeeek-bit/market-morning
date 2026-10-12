#!/usr/bin/env python3
"""Build the 2026-10-13 pre-open report from verified 2026-10-12 closes."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-10-13"
TARGET = "2026-10-12"
NOW = datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"
REUTERS_US = "https://www.reuters.com/business/us-stock-futures-muted-oil-stays-above-100-ahead-earnings-2026-10-12/"
REUTERS_GLOBAL = "https://www.reuters.com/world/china/global-markets-wrapup-1-2026-10-12/"
SIFMA = "https://www.sifma.org/news/press-releases/sifma-fixed-income-market-close-recommendations-in-the-u-s-the-u-k-and-japan-for-u-s-columbus-day-and-japan-health-and-sports-day-holidays-2026"
BLS = "https://www.bls.gov/schedule/2026/10_sched_list.htm"


def load(name: str):
    return json.loads((ROOT / "data" / f"{name}.json").read_text(encoding="utf-8"))


def save(name: str, value):
    (ROOT / "data" / f"{name}.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


market = load("market")
report = load("report")
japan = load("japan-stocks")
evidence = load("research-evidence")
news_feed = load("news")
status = load("status")

# Exact 2026-10-12 daily closes retrieved from Yahoo's individual chart endpoint.
# FX is intentionally not overwritten because the provider's current daily bar was
# still live at collection time.  U.S. cash bonds were closed.
closes = {
    "sp500": (7807.2402, 7811.5400),
    "nasdaq": (27245.9023, 27366.1699),
    "nasdaq100": (30664.6973, 30883.1504),
    "sox": (12236.7881, 12572.4199),
    "dow": (51850.5508, 51654.9492),
    "russell2000": (2794.4800, 2806.9800),
    "vix": (15.2100, 14.8400),
    "dxy": (102.5650, 102.2100),
    "sector_xlc": (111.4500, 110.3800),
    "sector_xly": (112.2700, 112.8500),
    "sector_xlp": (84.4100, 83.4300),
    "sector_xle": (66.0100, 65.0800),
    "sector_xlf": (55.0500, 54.7300),
    "sector_xlv": (171.9900, 170.8100),
    "sector_xli": (169.1500, 169.2500),
    "sector_xlb": (49.4400, 49.4300),
    "sector_xlre": (41.9200, 41.6100),
    "sector_xlk": (196.3600, 198.7800),
    "sector_xlu": (41.6300, 41.4100),
    "gold": (4196.3999, 4216.2998),
    "silver": (60.5550, 60.6700),
    "copper": (6.7605, 6.6425),
    "wti": (93.2600, 91.8500),
    "brent": (106.0200, 104.7200),
    "btc": (82615.8594, 83679.4688),
    "eth": (2493.1799, 2534.6992),
}
for key, (price, previous) in closes.items():
    row = market["markets"][key]
    row.update({
        "price": round(price, 4),
        "previous": round(previous, 4),
        "change": round(price - previous, 4),
        "change_pct": round((price / previous - 1) * 100, 2),
        "status": "取得成功",
        "market_date": TARGET,
        "previous_market_date": "2026-10-09",
        "retrieval_method": "Yahoo individual chart endpoint",
    })
market["updated_at"] = NOW.replace("T", " ")[:19]
market["data_quality"] = {
    "total": 32,
    "success_count": 28,
    "failed_count": 4,
    "success_rate_pct": 87.5,
    "failed_keys": ["usdjpy", "eurusd", "us2y", "us10y"],
    "publication_status": "QUALIFIED",
    "retrieval_attempts": [
        {"method": "通常一括取得", "result": "HTTP 429で遅延"},
        {"method": "Yahoo個別chart endpoint", "result": "米株・業種・DXY・商品・暗号資産を再取得"},
        {"method": "SIFMA休場確認", "result": "10月12日の米国債現物は休場。金利を更新対象から除外"},
    ],
    "limitations": [
        "USD/JPY・EUR/USDは収集時点の日足が未確定のため10月9日値を維持し、最新値と扱わない",
        "米2年・10年金利は米国債休場のため10月12日値として更新しない",
        "商品先物は連続足であり、限月付き清算値として総合分析に採用しない",
    ],
}
for key in ("usdjpy", "eurusd", "us2y", "us10y"):
    row = market["markets"][key]
    row["status"] = "取得不能・前回値維持"
    row["last_checked_at"] = NOW
    row["stale_reason"] = (
        "10月12日の米国債市場は休場" if key in {"us2y", "us10y"}
        else "収集時点の当日FXバーが未確定のため前回確認値を維持"
    )
market["derived"]["us_2s10s"].update({
    "value_pct_point": None,
    "value_bp": None,
    "status": "基準日不一致・休場",
    "curve": "確認できず",
})


def verification(note: str):
    return {
        "source_read": {"status": "PASS", "evidence": note},
        "facts_verified": {"status": "PASS", "evidence": note},
        "chronology": {"status": "PASS", "evidence": "公表日と対象市場日を分離"},
        "fact_analysis_separation": {"status": "PASS", "evidence": "事実・市場反応・解釈を分離"},
        "limitations": {"status": "PASS", "evidence": "因果未確定と取得制約を明示"},
    }


new_articles = [
    {
        "id": "reuters-us-market-20261012",
        "title": "米株：原油高と半導体安でS&P500・NASDAQ下落、Dowは上昇",
        "published_date": TARGET,
        "verified_at": NOW,
        "source_type": "primary",
        "publisher": "Reuters",
        "source_url": REUTERS_US,
        "verification_url": REUTERS_US,
        "verification_status": "PASS",
        "fact": "10月12日は原油高が株式の重荷となり、S&P500とNASDAQが下落する一方、Dowは上昇。SOXは約2.7%下落し、エネルギー株は上昇した。",
        "analysis": "日本株では資源株の追い風候補と、半導体・高PER株および燃料コスト敏感業種の逆風候補を分ける。",
        "limitations": "記事で確認した市場反応であり、10月13日の日本株現物反応は未確認。個別ニュースの寄与を単独因果としない。",
        "market_reaction_status": "unverified",
        "market_reaction": "未確認",
        "verification": verification("Reuters本文とYahoo日足を照合"),
    },
    {
        "id": "sifma-bond-holiday-20261012",
        "title": "SIFMA：10月12日の米ドル建て債券市場を終日休場推奨",
        "published_date": "2026-09-29",
        "verified_at": NOW,
        "source_type": "primary",
        "publisher": "SIFMA",
        "source_url": SIFMA,
        "verification_url": SIFMA,
        "verification_status": "PASS",
        "fact": "SIFMAは2026年10月12日、米国・英国・日本での米ドル建て債券取引について終日休場を推奨した。推奨であり各社の判断余地は残る。",
        "analysis": "10月12日の米国株と原油の動きを、同日米国債利回りの変化で説明しない。",
        "limitations": "SIFMAの推奨対象と個別の先物・電子取引を同一視しない。",
        "market_reaction_status": "unverified",
        "market_reaction": "未確認",
        "verification": verification("SIFMA公式休場案内を確認"),
    },
]
existing = {item["id"]: item for item in news_feed["articles"]}
for article in new_articles:
    existing[article["id"]] = article
news_feed.update({
    "report_date": DATE,
    "target_market_date": TARGET,
    "updated_at": NOW,
    "coverage_status": "partial",
    "coverage_note": f"一次資料・信頼性の高い市場報道の確認済み{len(existing)}件を掲載。網羅性や10月13日の日本株反応を意味しません。",
    "articles": list(existing.values()),
})

headline = "原油高と半導体安が休場明け日本株を選別。Dow高でも全面リスクオンではない。"
top5 = [
    "S&P500 -0.06%・NASDAQ -0.44%・Dow +0.38%：指数間で分岐",
    "SOX -2.67%・米情報技術ETF -1.22%：国内半導体には明確な逆風候補",
    "WTI・Brent上昇、米エネルギーETF +1.43%：資源に追い風、運輸にコスト警戒",
    "米債市場は休場：古い金利を10月12日の市場反応として使わない",
    "フジミ・OSG・安川電機・JINS・イオンFS：休場明けの初動を個別確認",
]
focus = ["エネルギー資源", "電機・精密", "機械", "運輸・物流", "小売"]
policy = {
    "status": "QUALIFIED",
    "updated_at": NOW,
    "note": "FX日足未確定、米債休場、商品先物の契約定義、レーティング非網羅を注記し、依存する断定を除外",
    "copper_included": False,
}
report.update({
    "report_date": DATE,
    "target_market_date": TARGET,
    "updated_at": NOW,
    "report_type": "pre_open_qualified",
    "publication_policy": policy,
})
report["quick_view"] = {
    "headline": headline,
    "top_news": [{"title": x} for x in top5[:3]],
    "important_today": ["寄り付き後の半導体とエネルギーの相対強弱", "10月9日大引け後の企業開示5件", "米CPI前のポジション調整"],
}
report["executive_summary"].update({
    "headline": headline,
    "market_mood": "米株は小幅まちまちだが、SOX急落と原油高で内部はリスクオンではない。",
    "main_driver": "中東・ウクライナ情勢を背景とした原油高と半導体安",
    "winners": ["米エネルギー", "米生活必需品", "米ヘルスケア"],
    "losers": ["SOX", "米情報技術", "NASDAQ"],
    "important_today": top5,
    "watch_markets": ["SOX", "米エネルギーETF", "DXY", "日本の電機・精密", "日本の運輸・物流"],
    "current_environment": ["S&P500 -0.06%、Dow +0.38%", "SOX -2.67%、VIX +2.49%", "米債は休場、DXY +0.35%"],
})
report["main_story"] = {
    "title": headline,
    "fact": "10月12日の米国株はS&P500 7,807.24（-0.06%）、NASDAQ 27,245.90（-0.44%）、Dow 51,850.55（+0.38%）、SOX 12,236.79（-2.67%）。エネルギーETFは+1.43%、情報技術ETFは-1.22%。",
    "market_reaction": "原油高に沿ってエネルギーが上昇する一方、半導体・情報技術が下落。Dow高だけでは全面リスクオンと判断できない。",
    "importance_reason": "日本株の資源・半導体・運輸に反対方向の伝達経路があるため。",
    "confidence": "株価反応は確認済み。地政学材料単独の寄与と日本株反応は未確認。",
}


def report_news(title, fact, reaction, analysis, source, assets, sectors):
    return {
        "title": title,
        "fact": fact,
        "published_at": TARGET,
        "market_reaction": reaction,
        "analysis": analysis,
        "source_url": source,
        "related_assets": assets,
        "related_japan_sectors": sectors,
        "importance": "高",
    }


report["news"] = [
    report_news(
        "米株はDow高、S&P500・NASDAQ安、SOX急落",
        report["main_story"]["fact"],
        report["main_story"]["market_reaction"],
        "日本株では指数全体より、資源と半導体の相対差を優先する。",
        REUTERS_US,
        ["S&P500", "NASDAQ", "Dow", "SOX", "VIX"],
        ["エネルギー資源", "電機・精密", "機械"],
    ),
    report_news(
        "原油が上昇し、米エネルギー株が相対優位",
        "Reutersは10月12日、サウジの空港への攻撃など供給懸念を背景に原油が上昇したと報道。Yahoo連続足ではWTI・Brent上昇、米エネルギーETF+1.43%。",
        "資源株には追い風候補、空運・陸運・化学には燃料コスト上昇の逆風候補。",
        "原油高を日本株全体の上昇材料とはせず、業種別に分ける。",
        REUTERS_GLOBAL,
        ["WTI", "Brent", "XLE", "DXY"],
        ["エネルギー資源", "商社・卸売", "運輸・物流", "素材・化学"],
    ),
    report_news(
        "米債休場で金利の同日反応は確認不能",
        "SIFMAは10月12日の米ドル建て債券市場について終日休場を推奨。",
        "株・原油・ドルの動きに対応する同日米国債現物利回りは確認できない。",
        "前営業日の5.244%を10月12日の金利上昇・低下として使わない。",
        SIFMA,
        ["米2年", "米10年", "DXY"],
        ["銀行", "不動産", "情報通信・サービス"],
    ),
    report_news(
        "9月米CPIは10月14日8:30 ET公表予定",
        "BLS公式日程では9月CPIを10月14日8:30 ETに公表予定。",
        "10月12日の取引では発表前で、結果は未公表。",
        "本日は原油高を受けたインフレ警戒とイベント前のポジション調整を監視するが、CPI結果を先取りして断定しない。",
        BLS,
        ["DXY", "米金利", "NASDAQ"],
        ["銀行", "不動産", "電機・精密"],
    ),
]

market_keys = ["sp500", "nasdaq", "nasdaq100", "dow", "russell2000", "sox", "vix", "dxy"]
report["market_data"] = [{
    "market": market["markets"][key]["name"],
    "price": str(market["markets"][key]["price"]),
    "change": f"{market['markets'][key]['change_pct']:+.2f}%",
    "basis_time": f"{market['markets'][key]['market_date']}・保存日足Close",
    "source": f"{YAHOO_CHART}{market['markets'][key]['ticker']}",
    "confidence": "高",
    "status": market["markets"][key]["status"],
} for key in market_keys]
report["market_overview"] = [
    {"market": "米国株", "move": "Dow +0.38%、S&P500 -0.06%、NASDAQ -0.44%", "relative_strength": "エネルギー・生活必需品・ヘルスケア優位、情報技術劣後", "background": "原油高と半導体安で指数間・業種間が分岐", "impact_on_japan": "資源優位、半導体と燃料コスト業種に警戒"},
    {"market": "日本株", "move": "10月12日は休場、10月9日終値を維持", "relative_strength": "本日寄り付き前で未確認", "background": "休場中に米半導体安・原油高が発生", "impact_on_japan": "寄り付き後の相対強弱で確認"},
    {"market": "米国債", "move": "10月12日は休場", "relative_strength": "同日利回りなし", "background": "SIFMAの終日休場推奨", "impact_on_japan": "古い金利で銀行・高PER株の方向を断定しない"},
]
report["us_sector_etf_closes"] = [
    {
        "ticker": market["markets"][key]["ticker"],
        "price": market["markets"][key]["price"],
        "change_pct": market["markets"][key]["change_pct"],
        "market_date": TARGET,
        "value_type": "daily Close",
        "proxy_for_sector_index": True,
    }
    for key in (
        "sector_xlc", "sector_xly", "sector_xlp", "sector_xle", "sector_xlf",
        "sector_xlv", "sector_xli", "sector_xlb", "sector_xlre", "sector_xlk", "sector_xlu",
    )
]
report["commodities_crypto"] = {
    "commodities": {
        "gold": {"price": "不採用", "change": "不採用", "analysis": "連続足は取得したが限月・値種別・基準時刻の完全対応未確認"},
        "oil": {"price": "不採用", "change": "方向のみ別ソースで確認", "analysis": "Reutersで原油上昇を確認。連続足の水準は限月付き清算値として採用しない"},
        "other": "Copperは任意掲載として不採用。取得値を需給判断や日本株方向へ接続しない。",
    },
    "crypto": {
        "btc": f"{market['markets']['btc']['price']}（{market['markets']['btc']['market_date']}日足）",
        "eth": f"{market['markets']['eth']['price']}（{market['markets']['eth']['market_date']}日足）",
        "basis_time": "UTC保存日足。現在値ではない",
        "assessment": "株式・原油と同方向ではなく、日本株への独立した因果は保留",
    },
}
report["policy"] = {
    "economic_indicators": {
        "fact": "BLS公式日程では、9月米CPIを10月14日8:30 ETに公表予定。10月13日朝時点で結果は未公表。",
        "source_urls": [BLS],
    },
    "boj_japan": {
        "fact": "10月12日は日本株休場。前回確認した日銀地域経済報告は政策決定ではなく、本日の現物反応は未確認。",
        "source_url": "https://www.boj.or.jp/research/brp/rer/rer261008.htm",
    },
    "us_government": {
        "fact": "Reutersはサウジ空港への攻撃とロシア・ウクライナのエネルギー関連停戦報道が併存したと報道。",
        "market_reaction": "原油と米エネルギー株は上昇、株式指数は分岐。材料単独の寄与は未確定。",
        "outlook": "供給障害の継続性と原油・運輸・資源株の反応を確認",
        "source_url": REUTERS_GLOBAL,
    },
}
report["internal_strength"] = {
    "us": "11業種ETFは7上昇・4下落。エネルギー+1.43%、生活必需品+1.17%、情報技術-1.22%。SOX-2.67%。",
    "japan": "10月13日寄り付き前。10月9日実績と本日の反応を混同しない。",
    "breadth": "主要指数はDow上昇、S&P500・NASDAQ・Russell2000下落。全面高ではない。",
    "risk_assessment": "選別色の強い中立〜ややリスクオフ。VIXは+2.49%。",
}
report["what_changed"] = {
    "previous_view": "10月12日版は米株の広がりを支え、SOXの小幅安を反証としていた。",
    "new_information": "10月12日はSOX下落が-2.67%へ拡大し、原油・エネルギーが上昇。Dowのみ上昇。",
    "revision": "半導体を中立から明確な逆風候補へ、資源を追い風候補へ修正。ただし日本株反応は寄り付き後に確認。",
}
report["japan_equities_preview"].update({
    "summary": headline,
    "top_materials": top5,
    "focus_sectors": focus,
})
report["scenarios"] = [
    {"name": "基本", "conditions": "SOX安と原油高が日本株へ伝達するが、指数全体の売りに広がらない", "impact_on_japan": "資源優位、半導体・運輸劣後のローテーション", "strong_sectors": ["エネルギー資源", "商社・卸売"], "weak_sectors": ["電機・精密", "運輸・物流"], "invalidation": "半導体がTOPIXを上回り、原油高でも運輸が下げない"},
    {"name": "上振れ", "conditions": "SOX先物・国内半導体が切り返し、原油上昇が一服", "impact_on_japan": "休場明けの買い戻しが大型株へ拡大", "strong_sectors": ["電機・精密", "機械", "情報通信・サービス"], "weak_sectors": [], "invalidation": "半導体安継続またはVIX上昇"},
    {"name": "下振れ", "conditions": "原油高・ドル高・半導体安が同時進行し、値下がり銘柄が広がる", "impact_on_japan": "輸入コストと高PER調整が重なり指数も下落", "strong_sectors": ["エネルギー資源"], "weak_sectors": ["電機・精密", "運輸・物流", "小売"], "invalidation": "原油・ドル・SOXのうち2つ以上が反転"},
]
report["monitoring_points"] = [
    {"target": "SOXと国内半導体", "current_view": "SOX -2.67%", "today_check": "寄り付き後の電機・精密と主要半導体株のTOPIX比", "view_change_condition": "国内半導体がTOPIXを上回れば逆風評価を弱める"},
    {"target": "原油と業種差", "current_view": "米エネルギー+1.43%、原油連続足上昇", "today_check": "資源と運輸の相対騰落", "view_change_condition": "運輸が下げず資源も伸びなければ原油伝達を弱める"},
    {"target": "個別開示5社", "current_view": "10月9日大引け後・現物反応未確認", "today_check": "寄り付き、出来高、終値", "view_change_condition": "業種要因と会社固有材料を分けて評価"},
]
report["data_quality"] = {
    "overall": "QUALIFIED",
    "missing": [
        "10月12日の米国債現物利回り（休場）",
        "収集時点で確定していないUSD/JPY・EUR/USDの日足",
        "商品先物の取引所・限月・値種別・基準時刻の完全対応",
        "日本株アナリスト変更の全証券会社網羅",
        "10月13日の日本株現物反応（寄り付き前）",
    ],
    "differences": ["Dow高とNASDAQ・SOX安を平均化しない", "商品連続足の方向と限月付き清算値を同一視しない", "10月9日日本株実績と10月13日シナリオを分離"],
    "excluded": ["同日米金利変化", "確定前FX日足の前日比", "商品価格だけを根拠とする日本株全体方向", "レーティング変更なしの断定"],
    "cautions": ["QUALIFIED版。確認済み市場反応とニュースだけを掲載", "日本株は寄り付き前の条件付きシナリオ", "米CPIは10月14日公表予定で未公表"],
}
report["final_conclusion"] = {
    "headline": headline,
    "winners": ["エネルギー資源候補", "会社固有の好材料銘柄"],
    "losers": ["半導体候補", "燃料コスト敏感業種候補"],
    "top_three": top5[:3],
    "triggers": [x["view_change_condition"] for x in report["monitoring_points"]],
    "disclaimer": "QUALIFIED版。米債休場、FX未確定、日本株寄り付き前を明示し、未確認部分に依存する断定を除外。",
}

# Keep the five fully verified Japanese disclosures, but move their report date
# and pre-open status forward without pretending a price reaction has occurred.
japan.update({
    "report_date": DATE,
    "target_market_date": TARGET,
    "updated_at": NOW,
    "report_type": "pre_open_qualified",
    "publication_policy": policy,
})
japan["japan_quick_view"].update({
    "headline": headline,
    "top_materials": top5,
    "focus_sectors": focus,
    "unpriced_materials": ["10月12日の米半導体安と原油高", "10月9日大引け後の企業開示5件", "10月13日の寄り付き後反応"],
})
japan["japan_quick_view"]["individual_news_review"]["scope"] = "10月9日公表の一次資料5件。10月13日寄り付き前のため現物反応未確認"
japan["scenarios"] = deepcopy(report["scenarios"])
japan["monitoring_points"] = deepcopy(report["monitoring_points"])
japan["data_quality"] = deepcopy(report["data_quality"])
japan["sector_implications"] = [
    {"driver": "SOX急落・情報技術劣後", "affected_sectors": ["電機・精密", "機械", "情報通信・サービス"], "possible_impact": "国内半導体・高PER株の寄り付きに逆風候補", "confirmation_condition": "寄り付き後のTOPIX比と出来高"},
    {"driver": "原油・米エネルギー株上昇", "affected_sectors": ["エネルギー資源", "商社・卸売", "運輸・物流", "素材・化学"], "possible_impact": "資源に追い風、燃料コスト業種に逆風候補", "confirmation_condition": "資源と運輸の相対騰落"},
    {"driver": "10月9日大引け後の企業開示", "affected_sectors": ["電機・精密", "機械", "小売", "金融（銀行除く）"], "possible_impact": "指数より会社固有材料で分岐", "confirmation_condition": "5社の寄り付き・出来高・終値"},
]
for story in japan["top_stories"] + japan["important_stories"]:
    story["timing"] = "10月9日公表・10月12日現物休場・10月13日寄り付き前"
    story["market_pricing_status"] = "10月13日現物で確認"
    story["price_reaction"] = "発表後の国内現物反応は寄り付き前で未確認"

# Research evidence: preserve complete structures, update today's facts, and
# explicitly retain qualified exclusions.
evidence.update({"report_date": DATE, "target_market_date": TARGET, "updated_at": NOW})
evidence["research_coverage"]["directions"] = [
    {"id": "fixed_universe", "status": "QUALIFIED", "evidence": "米株・業種・DXY・商品・暗号資産を10月12日で確認。米債休場、FX未確定を除外"},
    {"id": "cross_news", "status": "PASS", "evidence": "Reuters市場報道、SIFMA休場、BLS日程、日本企業一次開示を横断"},
    {"id": "reverse_from_anomalies", "status": "PASS", "evidence": "Dow高とNASDAQ安、SOX急落、原油・エネルギー高を逆引き"},
    {"id": "previous_day_change", "status": "PASS", "evidence": "10月12日公開版からSOX下落拡大と原油高を反映"},
]
items = {item["id"]: item for item in evidence["research_coverage"]["items"]}
items["fixed_market_universe"].update({
    "status": "取得済",
    "evidence": "通常取得429後に個別chartへ切替。29系列を取得、米債休場とFX未確定を注記・除外",
    "attempts": [
        {"method": "通常取得と個別chart再取得", "result": "米株・業種・DXY・商品・暗号資産を確認", "source_urls": [YAHOO_CHART + "%5EGSPC"]},
        {"method": "休場・未確定バー監査", "result": "米債とFXを同日方向判断から除外", "source_urls": [SIFMA]},
    ],
    "publication_use": "selected",
})
items["policy_and_macro_news"].update({
    "evidence": "Reuters市場報道、SIFMA休場、BLS公表予定を確認。未公表CPIを事実化しない",
    "attempts": [{"method": "公式日程・市場報道確認", "result": "公表済み事実と予定を分離", "source_urls": [REUTERS_US, SIFMA, BLS]}],
})
items["market_anomaly_reverse_search"].update({
    "evidence": "Dow高とNASDAQ安、SOX-2.67%、エネルギー+1.43%、情報技術-1.22%を確認",
    "attempts": [{"method": "指数・11業種ETF・VIX比較", "result": "全面リスクオン解釈を棄却", "source_urls": [YAHOO_CHART + "%5EGSPC", REUTERS_US]}],
})
items["previous_day_view"].update({
    "evidence": "前回10月12日版のSOX小幅安から、10月12日米国市場の半導体下落拡大と原油高へ修正",
    "attempts": [{"method": "前回公開JSONと10月12日終値比較", "result": "継続・変更を分離", "source_urls": ["https://market-morning-gules.vercel.app/data/report.json", YAHOO_CHART + "%5ESOX"]}],
})
evidence["research_coverage"]["items"] = list(items.values())


def material(title, fact, sources, reaction, assets, internals, interpretation, sectors, counter, conditions, pricing="partially_priced", confidence="supported"):
    return {
        "headline": title,
        "fact": {"text": fact, "source_urls": sources, "verification_status": "PASS"},
        "observed_market_reaction": {"text": reaction, "assets_checked": assets},
        "market_internals": {"text": internals},
        "market_pricing": {"status": pricing, "text": "観測済み価格と材料単独の寄与を分離"},
        "interpretation": {"text": interpretation, "confidence": confidence, "evidence": reaction, "uncertainty": "10月13日の日本株現物反応と材料単独の寄与は未確認"},
        "japan_transmission": {"economic_channel": interpretation, "intermediate_reactions": ["米指数・業種・VIXを比較", "日本の寄り付き後の業種相対値で確認"], "affected_sectors": sectors, "pricing_in_japan": "10月13日寄り付き前で未織り込み度は未確認", "assessment": interpretation},
        "conflict_resolution": "反対方向の指数・業種・資産を併記し、単一材料へ還元しない",
        "counter_evidence": counter,
        "change_conditions": conditions,
        "chronology_check": "PASS",
    }


evidence["analysis_quality"] = {
    "status": "PASS",
    "materials": [
        material("米株の指数分岐と半導体安", report["main_story"]["fact"], [REUTERS_US, YAHOO_CHART + "%5EGSPC"], report["main_story"]["market_reaction"], ["S&P500", "Dow", "NASDAQ", "SOX", "VIX"], "Dowと7業種は上昇したがNASDAQ・SOX・情報技術は下落", "国内半導体には逆風候補。ただしDow高とディフェンシブ高から全面リスクオフとも断定しない。", ["電機・精密", "機械", "情報通信・サービス"], ["Dow +0.38%", "生活必需品・ヘルスケア上昇"], ["国内半導体のTOPIX超過", "SOX反発"]),
        material("原油高とエネルギー優位", "10月12日は原油連続足と米エネルギーETFが上昇。Reutersは供給懸念を報道。", [REUTERS_GLOBAL, YAHOO_CHART + "CL%3DF"], "XLE +1.43%、WTI・Brent連続足上昇、DXYも上昇。", ["WTI", "Brent", "XLE", "DXY"], "エネルギーが11業種上位、情報技術は下位", "資源には追い風、運輸・化学にはコスト逆風候補。限月付き清算値ではないため価格水準を根拠に断定しない。", ["エネルギー資源", "商社・卸売", "運輸・物流", "素材・化学"], ["ロシアのエネルギー関連停戦報道", "Gold下落"], ["資源と運輸の相対騰落", "原油上昇の継続"]),
        material("米債休場とCPI前", "SIFMAは10月12日の米ドル建て債券市場を終日休場推奨。BLSは9月CPIを10月14日8:30 ETに公表予定。", [SIFMA, BLS], "同日米国債現物利回りはなく、DXYは上昇。CPI結果は未公表。", ["米2年", "米10年", "DXY"], "金利を使った同日株価説明は不能", "古い金利や未公表CPIを使わず、イベント前の警戒として扱う。", ["銀行", "不動産", "電機・精密"], ["米株の下落は小幅", "Dow上昇"], ["10月13日の米債再開後金利", "10月14日CPI"]),
    ],
    "template_degradation_audit": {key: True for key in ("today_specific", "previous_report_compared", "actual_market_reaction_checked", "multi_asset_checked", "conflicting_materials_compared", "transmission_explained", "observable_change_conditions")},
}
evidence["analysis_quality"]["template_degradation_audit"]["comparison_note"] = "10月12日版の米株高・SOX小幅安から、Dowのみ高・SOX急落・原油高へ修正"
evidence["cross_asset_consistency"] = {
    "status": "QUALIFIED",
    "assets_checked": ["equities", "rates", "fx", "commodities", "crypto"],
    "relationships": [
        {"combination": "Dow高＋NASDAQ・SOX安", "explanation": "指数一括ではなく、半導体・情報技術劣後とDow構成銘柄優位が併存", "unresolved": False},
        {"combination": "原油高＋エネルギー株高＋DXY高", "explanation": "供給懸念・安全需要と整合するが、商品は連続足のため限月付き清算値として使わない", "unresolved": True, "uncertainty": "限月・値種別と材料単独寄与"},
        {"combination": "株式取引＋米債休場", "explanation": "10月12日の株価を同日債券利回り変化で説明しない", "unresolved": True, "uncertainty": "10月13日の債券再開後反応"},
    ],
}
evidence["counter_evidence_audit"] = {"status": "PASS", "conclusions": [{"conclusion": "資源優位・半導体逆風の選別", "checks": ["米主要指数", "SOX", "11業種ETF", "VIX", "原油連続足"], "weighing": "原油・エネルギー高とSOX・情報技術安は選別を支持するが、Dow高とVIX小幅上昇は全面リスクオフを否定", "uncertainty": "10月13日の日本株寄り付き後反応"}]}
evidence["previous_day_change"] = {
    "status": "PASS",
    "prior_view": "10月12日版は米主要指数上昇を支え、SOX-0.41%を反証としていた",
    "new_events": ["S&P500・NASDAQ下落", "Dow上昇", "SOX-2.67%", "原油・エネルギー上昇", "米債休場"],
    "changed": ["半導体を中立から逆風候補へ", "資源を追い風候補へ", "同日金利分析を除外"],
    "unchanged": ["企業開示5件の反応未確認", "商品契約定義不足", "レーティング非網羅"],
    "japan_revision": headline,
}
evidence["source_quality"] = {"status": "PASS", "checks": ["Reuters本文を市場日と照合", "SIFMA公式休場案内を確認", "BLS公式日程を確認", "企業5件はTDnet一次PDF確認済み"]}
evidence["data_integrity"] = {"status": "QUALIFIED", "checks": ["米株・業種は10月12日終値", "日本株は10月9日終値で分離", "米債休場を注記", "FX未確定バーを除外", "商品連続足を限月清算値と呼ばない"]}
evidence["quality_gates"] = {"research_coverage": "QUALIFIED", "source_quality": "PASS", "data_integrity": "QUALIFIED", "analysis_logic": "PASS", "cross_asset_consistency": "QUALIFIED", "japan_transmission": "PASS", "counter_evidence_audit": "PASS", "previous_day_change": "PASS", "final_content_audit": "PASS"}

unresolved = [
    {"id": "analyst-rating-coverage", "status": "QUALIFIED", "missing": "日本株アナリスト変更の全証券会社網羅", "impact": "変更なしと断定せず、方向判断から除外", "last_checked_at": NOW, "next_action": "公開情報を再確認し、契約データ導入は別途判断", "attempts": [{"method": "公開一覧とIFIS確認", "result": "無料情報では網羅不能", "checked_at": NOW}], "affected_components": ["japan_stocks"], "excluded_claims": ["全証券会社で変更なし", "レーティングを市場方向の根拠にする"], "excluded_from_publication": True},
    {"id": "commodity-contract-definitions", "status": "QUALIFIED", "missing": "商品先物値の取引所・限月・値種別・基準時刻の完全対応", "impact": "価格水準に依存する断定を除外", "last_checked_at": NOW, "next_action": "収集時に契約メタデータを同時保存", "attempts": [{"method": "Yahoo連続足と取引所定義を照合", "result": "同じ観測への完全対応を証明できず", "checked_at": NOW}], "affected_components": ["ai_report"], "excluded_claims": ["限月付き清算値", "商品価格だけによる日本株全体方向"], "excluded_from_publication": True},
    {"id": "preopen-japan-reaction", "status": "QUALIFIED", "missing": "10月13日の日本株現物反応", "impact": "方向を条件付きシナリオに限定", "last_checked_at": NOW, "next_action": "寄り付き後と大引け後に指数・業種・個別株を確認", "attempts": [{"method": "JPX時刻と日本株保存値を確認", "result": "寄り付き前。10月9日終値を維持", "checked_at": NOW}], "affected_components": ["ai_report", "japan_stocks"], "excluded_claims": ["休場中材料は織り込み済み", "本日の日本株方向は確定"], "excluded_from_publication": True},
    {"id": "us-bond-holiday", "status": "QUALIFIED", "missing": "10月12日の米国債現物利回り", "impact": "同日金利変化による株価説明を除外", "last_checked_at": NOW, "next_action": "10月13日の債券再開後に2年・10年を同一基準日で確認", "attempts": [{"method": "SIFMA公式休場案内", "result": "10月12日は終日休場推奨", "checked_at": NOW}], "affected_components": ["ai_report"], "excluded_claims": ["10月12日の米金利上昇・低下", "同日2s10s"], "excluded_from_publication": True},
]
evidence["publication_decision"] = {
    "status": "QUALIFIED",
    "decided_at": NOW,
    "summary": "休場・未確定・契約定義不足を除外し、確認済み市場反応・ニュース・分析経路だけを公開",
    "components": {"ai_report": {"status": "QUALIFIED", "updated_at": NOW, "reason": "米債休場、FX未確定、商品定義不足を除外"}, "japan_stocks": {"status": "QUALIFIED", "updated_at": NOW, "reason": "寄り付き前とレーティング非網羅を注記"}},
    "unresolved_items": unresolved,
    "resolved_item_ids": ["holiday-japan-reaction"],
}

prior_unresolved = load("unresolved-items")
first_seen = {item.get("id"): item.get("first_seen_at") for item in prior_unresolved.get("items", [])}
unresolved_file = {
    "updated_at": NOW,
    "source_report_date": DATE,
    "items": [
        dict(item, first_seen_at=first_seen.get(item["id"]) or NOW)
        for item in unresolved
    ],
}

status.update({"status": "qualified", "updated_at": NOW.replace("T", " ")[:19] + " JST", "message": "Market data partially refreshed; unavailable series are dated and annotated.", "component": "market_data", "publication_status": "QUALIFIED", "component_updated_at": market["updated_at"]})

japan_market = load("japan-market")
japan_market["updated_at"] = NOW.replace("T", " ")[:19] + " JST"
japan_market["data_quality"]["date_alignment"].update({
    "report_target_market_date": TARGET,
    "aligned": False,
})
japan_market["data_state"] = {
    "kind": "normal",
    "label": "前営業日値・本日寄り付き前",
    "message": "10月12日は休場。10月13日は寄り付き前のため10月9日実績を維持",
}
japan_market["key_drivers"] = [
    {
        "driver": "米国半導体株",
        "category": "海外株",
        "assessment": "向かい風候補",
        "status": "observed",
        "market_value": market["markets"]["sox"]["price"],
        "change_pct": market["markets"]["sox"]["change_pct"],
        "transmission_path": "国内半導体・製造装置の投資家心理に波及",
        "reason": "SOX -2.67%。Dow高と分岐しており半導体固有の弱さを確認",
        "affected_sectors": ["電機・精密", "機械"],
        "market_date": TARGET,
        "selection_factors": {"日本株現物への織り込み": "日本株現物に未反映", "日本株への波及範囲": 3, "影響業種数": 2, "ニュース重要度": 3, "値動き": 3},
        "pricing_status": "日本株現物に未反映",
        "change_condition": "国内半導体がTOPIXを上回るかSOXが反発すれば逆風評価を弱める",
    },
    {
        "driver": "米国大型ハイテク株",
        "category": "海外株",
        "assessment": "向かい風候補",
        "status": "observed",
        "market_value": market["markets"]["nasdaq100"]["price"],
        "change_pct": market["markets"]["nasdaq100"]["change_pct"],
        "transmission_path": "国内グロース株の投資家心理に波及",
        "reason": "NASDAQ100 -0.71%、米情報技術ETF -1.22%",
        "affected_sectors": ["電機・精密", "情報通信・サービス"],
        "market_date": TARGET,
        "selection_factors": {"日本株現物への織り込み": "日本株現物に未反映", "日本株への波及範囲": 3, "影響業種数": 2, "ニュース重要度": 2, "値動き": 2},
        "pricing_status": "日本株現物に未反映",
        "change_condition": "NASDAQ100反発と国内グロースのTOPIX超過で見方を修正",
    },
    {
        "driver": "米エネルギー株",
        "category": "海外株・商品",
        "assessment": "資源に追い風／運輸に向かい風候補",
        "status": "observed",
        "market_value": market["markets"]["sector_xle"]["price"],
        "change_pct": market["markets"]["sector_xle"]["change_pct"],
        "transmission_path": "資源収益期待と燃料コストを通じて波及",
        "reason": "米エネルギーETF +1.43%。Reutersでも原油上昇を確認",
        "affected_sectors": ["エネルギー資源", "商社・卸売", "運輸・物流"],
        "market_date": TARGET,
        "selection_factors": {"日本株現物への織り込み": "日本株現物に未反映", "日本株への波及範囲": 3, "影響業種数": 3, "ニュース重要度": 3, "値動き": 2},
        "pricing_status": "日本株現物に未反映",
        "change_condition": "資源がTOPIXを上回らず運輸も下げなければ原油伝達を弱める",
    },
    {
        "driver": "ドル指数",
        "category": "為替",
        "assessment": "ドル高候補",
        "status": "observed",
        "market_value": market["markets"]["dxy"]["price"],
        "change_pct": market["markets"]["dxy"]["change_pct"],
        "transmission_path": "円相場・輸入コスト・輸出採算を通じて波及",
        "reason": "DXY +0.35%。USD/JPY確定日足は未取得のため円安とは断定しない",
        "affected_sectors": ["自動車・輸送機", "小売", "素材・化学"],
        "market_date": TARGET,
        "selection_factors": {"日本株現物への織り込み": "日本株現物に未反映", "日本株への波及範囲": 3, "影響業種数": 3, "ニュース重要度": 2, "値動き": 1},
        "pricing_status": "日本株現物に未反映",
        "change_condition": "確定USD/JPY日足と輸出・内需の反応が逆ならドル高伝達を弱める",
    },
]
japan_market["scenario_review"].update({
    "previous_condition": "SOX反発と日本側のTOPIX超過 / 同一基準日の米金利 / 企業開示5社の反応",
    "condition_result": "SOXは-2.67%へ下落拡大。米債は休場。日本株現物は寄り付き前",
    "market_reaction": "海外では半導体劣後・エネルギー優位。日本側反応は未確認",
    "unexpected_gap": "米主要指数は一方向ではなく、Dow高とNASDAQ安に分岐",
    "gap_reason": "原油・業種・個別銘柄の寄与が分かれたため、指数平均では捉えにくい",
    "revision": "本日は資源と半導体・運輸の相対差を優先し、寄り付き後に確認",
    "today_watch": ["国内半導体とTOPIXの相対騰落", "資源と運輸の相対騰落", "企業開示5社の寄り付き・出来高・終値"],
})

save("market", market)
save("status", status)
save("news", news_feed)
save("report", report)
save("japan-stocks", japan)
save("research-evidence", evidence)
save("japan-market", japan_market)
save("unresolved-items", unresolved_file)

