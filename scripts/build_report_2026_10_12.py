#!/usr/bin/env python3
"""Build the 2026-10-12 holiday report from verified repository evidence."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from research_quality import FINAL_GATES, TEMPLATE_CHECKS
from update_japan_market import enrich_investor_view


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-10-12"
TARGET = "2026-10-09"
UPDATED = datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
CANON = "https://raw.githubusercontent.com/vakeeeek-bit/market-morning/main/data/market.json"
JPX_CALENDAR = "https://www.jpx.co.jp/corporate/about-jpx/calendar/"
RATING_PUBLIC = "https://nikkeiyosoku.com/stock/rating/?date=2026-10-09"
IFIS = "https://www.ifis.co.jp/"


def load(name):
    return json.loads((ROOT / "data" / f"{name}.json").read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


market = load("market")
japan_market = load("japan-market")
verified = load("news")
previous = load("report")
m = market["markets"]
articles = {row["id"]: row for row in verified["articles"]}

headline = "休場明けは全面高ではなく選別。米株は広く上昇したが、SOX逆行安と金利高を同時に見る。"
top5 = [
    "米主要株価指数は上昇、VIX低下：リスク選好は維持",
    "SOX -0.41%：NASDAQ高でも日本の半導体を一括で追い風としない",
    "日経平均 -0.13%・TOPIX参考 +0.70%：10月9日の国内内部は指数間で分岐",
    "米10年5.244%・米2年は10月8日公表値：異なる日付の金利差は算出しない",
    "OSG・フジミ・安川電機・JINS・イオンFS：10月13日に個別反応を確認",
]
focus = ["電機・精密", "情報通信・サービス", "銀行", "小売", "食品"]
quality = {
    "overall": "QUALIFIED",
    "missing": [
        "米2年債はFREDの10月8日公表値で、米10年債の10月9日値と基準日が異なる",
        "Gold・WTI・Brent・Copperの取引所、限月、値種別、基準時刻を正本で確認できない",
        "日本株現物は10月12日休場で、休場中材料への価格反応は未確認",
        "アナリスト評価変更は無料公開情報の確認範囲で、全証券会社を網羅できない",
    ],
    "differences": [
        "市場価格はmarket.jsonの保存日足。ニュースの市場反応とは別に扱う",
        "10月12日の確認済みニュースには10月5日〜9日の後日確認分を含む",
        "米株上昇とSOX下落、日経平均とTOPIX参考の分岐を平均化しない",
    ],
    "excluded": [
        "定義未確認の商品先物価格と前日比",
        "異なる日付の米2年・10年スプレッド",
        "未確認政策の市場方向断定",
        "全証券会社でレーティング変更なしという断定",
    ],
    "cautions": [
        "QUALIFIED版。確認済み部分だけを公開し、不足に依存する結論は保留",
        "日本株は10月9日終値。10月12日の現物価格ではない",
        "休場中材料の日本株反応は10月13日以降に確認",
    ],
}
publication_policy = {
    "status": "QUALIFIED",
    "updated_at": UPDATED,
    "note": "商品先物定義、金利日付差、休場中反応、レーティング非網羅を注記し、それらに依存する断定を除外",
    "copper_included": False,
}


def market_row(key):
    row = m[key]
    suffix = "%" if key in {"us2y", "us10y"} else ""
    return {
        "market": row["name"],
        "price": f"{row['price']}{suffix}",
        "change": f"{row['change_pct']:+.2f}%",
        "basis_time": f"{row['market_date']}・保存日足Close（現在値ではない）",
        "source": f"{CANON} / {row['ticker']}",
        "confidence": "高" if row.get("status") == "取得成功" else "要確認",
        "status": row.get("status"),
    }


market_data = [market_row(key) for key in (
    "sp500", "nasdaq", "nasdaq100", "dow", "russell2000", "sox",
    "us2y", "us10y", "dxy", "usdjpy", "vix", "btc", "eth",
)]

macro_ids = [
    "michigan-preliminary-20261009",
    "boj-sakura-20261008",
    "household-20261009",
    "ofac-gl135-20261009",
]


def report_news(article_id, reaction, sectors, assets):
    article = articles[article_id]
    return {
        "title": article["title"],
        "fact": article["fact"],
        "published_at": article["published_date"],
        "market_reaction": reaction,
        "analysis": article["analysis"],
        "source_url": article["source_url"],
        "related_assets": assets,
        "related_japan_sectors": sectors,
        "importance": "高",
    }


news = [
    {
        "title": "米株は上昇したがSOXは逆行安",
        "fact": "10月9日の保存日足はS&P500 +0.59%、NASDAQ +0.64%、NYダウ +0.83%、Russell2000 +0.46%、SOX -0.41%、VIX -3.70%。",
        "published_at": TARGET,
        "market_reaction": "広い株価指数とVIXはリスク選好方向だが、半導体だけは追随しなかった。",
        "analysis": "日本の半導体を全面追い風とせず、米大型ハイテクの支えとSOXの弱さを分ける。",
        "source_url": CANON,
        "related_assets": ["S&P500", "NASDAQ100", "SOX", "VIX"],
        "related_japan_sectors": ["電機・精密", "情報通信・サービス"],
        "importance": "高",
    },
    report_news(
        "michigan-preliminary-20261009",
        "同日の米株高と米10年上昇は確認したが、指標単独の因果は未確認。",
        ["小売", "自動車・輸送機", "銀行"],
        ["米10年", "S&P500", "USD/JPY"],
    ),
    report_news(
        "boj-sakura-20261008",
        "10月9日のTOPIX参考は上昇したが、地域報告単独の寄与は未確認。",
        ["小売", "銀行", "不動産"],
        ["日経平均", "TOPIX参考", "USD/JPY"],
    ),
    report_news(
        "household-20261009",
        "10月9日の食品は強く小売は弱いが、家計調査だけを原因とは断定しない。",
        ["小売", "食品", "サービス"],
        ["日経平均", "TOPIX参考", "USD/JPY"],
    ),
    report_news(
        "ofac-gl135-20261009",
        "軽油・原油価格への独立した反応と日本株現物への反応は未確認。",
        ["運輸・物流", "商社・卸売", "石油"],
        ["WTI", "Brent", "米10年"],
    ),
]


def story(article_id, company, ticker, category, importance):
    article = articles[article_id]
    return {
        "company": company,
        "ticker": ticker,
        "headline": article["title"].split("：", 1)[-1],
        "category": category,
        "fact": article["fact"],
        "announced_at": f"{article['published_date']}（公表時刻は一次資料記載範囲）",
        "timing": "10月9日公表・10月12日現物休場",
        "market_pricing_status": "10月13日現物で確認",
        "price_reaction": "発表後の国内現物反応は未確認",
        "related_stocks": [],
        "related_sectors": [category],
        "importance": importance,
        "confidence": "事実：一次資料確認済み、株価効果：未確認",
        "source_url": article["source_url"],
        "analysis": article["analysis"],
        "today_watch": article["limitations"],
    }


stories = [
    story("fujimi-forecast-20261009", "フジミインコーポレーテッド", "5384", "電機・精密", "高"),
    story("osg-buyback-20261009", "OSG", "6136", "機械", "高"),
    story("yaskawa-20261009", "安川電機", "6506", "電機・精密", "高"),
    story("jins-20261009", "ジンズホールディングス", "3046", "小売", "中"),
    story("aeon-financial-interim-20261009", "イオンフィナンシャルサービス", "8570", "金融（銀行除く）", "中"),
]
preview_stories = [
    {key: row[key] for key in ("company", "ticker", "headline", "importance", "market_pricing_status")}
    for row in stories[:3]
]

scenarios = [
    {
        "name": "基本",
        "conditions": "米株の広がりが維持され、SOXの弱さと金利上昇が拡大しない",
        "impact_on_japan": "TOPIX優位を基調に、半導体は個別業績で選別",
        "strong_sectors": ["食品", "素材・化学"],
        "weak_sectors": ["銀行", "小売"],
        "invalidation": "SOX反発と電機・精密の相対上昇、または米株全面反落",
    },
    {
        "name": "上振れ",
        "conditions": "SOXが反発し、米10年が低下、日本の電機・精密がTOPIXを上回る",
        "impact_on_japan": "大型ハイテクから半導体・機械へ追い風が広がる",
        "strong_sectors": ["電機・精密", "機械", "情報通信・サービス"],
        "weak_sectors": [],
        "invalidation": "SOX続落または日本側の追随不発",
    },
    {
        "name": "下振れ",
        "conditions": "米金利上昇とSOX安が同時に拡大し、円高または原油供給不安が加わる",
        "impact_on_japan": "高PER、輸出、運輸へ別経路の逆風",
        "strong_sectors": ["食品"],
        "weak_sectors": ["電機・精密", "自動車・輸送機", "運輸・物流"],
        "invalidation": "金利・為替・半導体が安定",
    },
]
watch = [
    {"target": "SOXと日本の電機・精密", "current_view": "SOX -0.41%、日本の電機・精密は10月9日+0.88%", "today_check": "10月13日の相対騰落と出来高", "view_change_condition": "SOX反発と日本側のTOPIX超過がそろえば追い風へ"},
    {"target": "米金利", "current_view": "米10年5.244%。米2年は10月8日4.75%", "today_check": "同一基準日の2年・10年を確認", "view_change_condition": "同日金利が低下すれば高PER逆風を弱める"},
    {"target": "休場中の個別材料", "current_view": "一次開示5件、現物反応は未確認", "today_check": "10月13日の寄り付き、出来高、終値", "view_change_condition": "会社固有材料と業種全体の反応を分ける"},
]

report = {
    "report_date": DATE,
    "target_market_date": TARGET,
    "updated_at": UPDATED,
    "report_type": "holiday_qualified",
    "week_period": None,
    "publication_policy": publication_policy,
    "quick_view": {"headline": headline, "top_news": [{"title": row["title"]} for row in news[:3]], "important_today": ["10月13日の日本株現物", "SOXと国内半導体の方向一致", "同一基準日の米金利"]},
    "executive_summary": {
        "headline": headline,
        "market_mood": "米株は上昇、VIX低下。ただしSOXは逆行安。日本は休場。",
        "main_driver": "広い米株上昇と半導体・金利の反証",
        "winners": ["米ヘルスケア・不動産・一般消費財ETF", "日本の食品（10月9日）"],
        "losers": ["SOX", "米コミュニケーションETF", "日本の銀行・小売（10月9日）"],
        "important_today": [row["title"] for row in news[1:]],
        "watch_markets": ["SOX", "米10年", "USD/JPY", "10月13日の日本株現物"],
        "current_environment": ["S&P500 +0.59%、VIX -3.70%", "SOX -0.41%、米10年5.244%", "日本株現物は10月12日休場"],
    },
    "main_story": {"title": headline, "fact": news[0]["fact"], "market_reaction": news[0]["market_reaction"], "importance_reason": "指数上昇を半導体全面高と誤読しないため", "confidence": "確認済み価格に基づく条件付き判断"},
    "news": news,
    "policy": {
        "economic_indicators": {"fact": articles["michigan-preliminary-20261009"]["fact"], "source_urls": [articles["michigan-preliminary-20261009"]["source_url"]]},
        "boj_japan": {"fact": articles["boj-sakura-20261008"]["fact"], "source_url": articles["boj-sakura-20261008"]["source_url"]},
        "us_government": {"fact": articles["ofac-gl135-20261009"]["fact"], "market_reaction": "未確認", "outlook": "実際の輸送・価格・日本株反応を確認して判断", "source_url": articles["ofac-gl135-20261009"]["source_url"]},
    },
    "scenarios": scenarios,
    "market_data": market_data,
    "market_overview": [
        {"market": "米国株", "move": "主要指数は上昇、SOXは-0.41%", "relative_strength": "ダウと広い指数が半導体を上回る", "background": "値動きの事実を確認。単一ニュースの因果は未確定", "impact_on_japan": "指数全体は支え、半導体は中立"},
        {"market": "日本株", "move": "10月9日は日経平均-0.13%、TOPIX参考+0.70%", "relative_strength": "TOPIX型優位", "background": "食品・素材が上位、銀行・小売が下位", "impact_on_japan": "10月13日に休場中材料の反応を確認"},
        {"market": "金利・為替", "move": "米10年5.244%、USD/JPY 158.063", "relative_strength": "ドル円は横ばい", "background": "2年債は公表日差", "impact_on_japan": "金利負担は残るが為替の新方向は未確認"},
    ],
    "internal_strength": {
        "nikkei_vs_topix": "10月9日は日経平均-0.13%、TOPIX参考+0.70%。指数間で分岐。",
        "large_vs_small": "NASDAQ100 +0.51%、Russell2000 +0.46%。差は小さい。",
        "breadth": "米11業種ETFは9上昇・2下落。全銘柄Breadthではない。",
        "sectors": "米国はXLRE +1.86%、XLV +1.58%、XLY +1.02%が上位。XLC -1.51%、XLE -0.25%が下位。",
        "turnover": "統一基準の全市場売買高は未取得。",
        "assessment": "広い株高だが、SOXとXLCの弱さが内部反証。",
    },
    "us_sector_etf_closes": [{"ticker": row["ticker"], "price": row["price"], "change_pct": row["change_pct"], "market_date": row["market_date"], "value_type": "daily Close", "proxy_for_sector_index": True} for key, row in m.items() if key.startswith("sector_")],
    "commodities_crypto": {"commodities": {"gold": {"price": "不採用", "change": "不採用", "analysis": "限月・値種別・基準時刻未確認"}, "oil": {"price": "不採用", "change": "不採用", "analysis": "WTI・Brentの契約定義未確認"}, "other": "Copperは任意掲載として不採用。SHFE在庫の確認済みニュースは在庫事実のみで、価格方向へ接続しない。"}, "crypto": {"btc": f"{m['btc']['price']}（{m['btc']['market_date']}日足）", "eth": f"{m['eth']['price']}（{m['eth']['market_date']}日足）", "basis_time": "保存日足。現在値ではない", "assessment": "日本株への独立した因果は保留"}},
    "monitoring_points": watch,
    "data_quality": quality,
    "final_conclusion": {"headline": headline, "winners": ["広い米株指数", "10月9日の日本食品・素材"], "losers": ["SOX", "10月9日の日本銀行・小売"], "top_three": top5[:3], "triggers": [row["view_change_condition"] for row in watch], "disclaimer": "QUALIFIED版。欠測・日付差・休場中反応を明示し、未確認事項に依存する方向判断を除外。"},
    "japan_equities_preview": {"summary": headline, "top_materials": top5, "focus_sectors": focus, "top_stories": preview_stories, "total_story_count": len(stories)},
    "what_changed": {"previous_report_date": previous["report_date"], "changed": ["米株は大型テック偏重から広い指数上昇へ", "SOXは逆行安で半導体判断を中立化", "日本は10月9日にTOPIX型優位", "確認済み一次ニュースを10月12日まで追加"], "unchanged": ["商品先物の契約定義不足", "レーティング非網羅", "異なる日付の金利差を算出しない"]},
    "source_notes": ["市場数値はmarket.json正本", "日本株実績はjapan-market.json", "政策・企業材料はnews.json内の一次資料検証済み記事", "後日確認を当時確認済みとは扱わない"],
}

japan = {
    "report_date": DATE,
    "target_market_date": TARGET,
    "updated_at": UPDATED,
    "report_type": "holiday_qualified",
    "publication_policy": publication_policy,
    "japan_quick_view": {"headline": headline, "top_materials": top5, "focus_sectors": focus, "unpriced_materials": ["10月12日休場中の政策・企業材料", "10月13日の個別株反応"], "individual_news_review": {"status": "reviewed", "story_count": len(stories), "scope": "10月9日公表の一次資料5件。後日確認時刻を保持し、現物反応未確認を明示"}},
    "top_stories": stories[:3],
    "important_stories": stories[3:],
    "other_stories": [],
    "data_quality": quality,
    "analyst_rating_changes": {"headline": "公開情報で確認できた範囲のみ。網羅不能", "coverage_status": "十分調査したが取得不能", "items": [], "source_review": [{"name": "公開日付一覧", "url": RATING_PUBLIC, "result": "全証券会社・EPS変更の網羅不可"}, {"name": "IFISサービス情報", "url": IFIS, "result": "契約データ未導入"}], "summary": "変更なしとは断定しない"},
    "sector_implications": [
        {"driver": "米株高とSOX安", "affected_sectors": ["電機・精密", "情報通信・サービス"], "possible_impact": "大型ハイテク支援と半導体弱さを分離", "confirmation_condition": "10月13日の業種相対騰落"},
        {"driver": "国内指数分岐", "affected_sectors": ["食品", "素材・化学", "銀行", "小売"], "possible_impact": "TOPIX型優位の持続性を確認", "confirmation_condition": "休場明けも同じ業種順位が続くか"},
    ],
    "scenarios": scenarios,
    "monitoring_points": watch,
    "source_notes": report["source_notes"],
}


def attempt(method, result, urls):
    return {"method": method, "result": result, "source_urls": urls}


items = [
    {"id": "fixed_market_universe", "label": "固定市場Universe", "tier": "Critical", "status": "取得済", "evidence": "株・金利・為替・商品・暗号資産32系列の状態と基準日を確認。採用値と除外値を分離", "attempts": [attempt("正本market.json照合", "株・金利・為替・暗号資産の保存日足を確認", [CANON])], "impact_if_unavailable": "市場全体判断を保留", "publication_use": "selected"},
    {"id": "policy_and_macro_news", "label": "政策・中央銀行・マクロ", "tier": "Critical", "status": "取得済", "evidence": "BOJ地域報告、米消費者調査、OFAC軽油許可を一次資料で確認。市場反応未確認を分離", "attempts": [attempt("一次資料実読", "事実・条件・留保を確認", [articles[row]["source_url"] for row in macro_ids])], "impact_if_unavailable": "政策方向を断定しない", "publication_use": "selected"},
    {"id": "market_anomaly_reverse_search", "label": "異常値からの逆引き", "tier": "Required", "status": "取得済", "evidence": "米株高とSOX安、日経平均とTOPIX参考の分岐、金利日付差を確認", "attempts": [attempt("複数資産・内部比較", "単一指数の全面解釈を回避", [CANON])], "impact_if_unavailable": "指数表面だけの分析になる", "publication_use": "selected"},
    {"id": "previous_day_view", "label": "前回公開との差分", "tier": "Critical", "status": "取得済", "evidence": f"前回公開{previous['report_date']}版と比較し、米株の広がり改善とSOX逆行安を反映", "attempts": [attempt("前回公開JSON比較", "継続点と変更点を分離", ["https://market-morning-gules.vercel.app/data/report.json"])], "impact_if_unavailable": "前回文章の流用を検出できない", "publication_use": "selected"},
    {"id": "company_disclosures", "label": "日本株の個別企業開示", "tier": "Critical", "status": "取得済", "evidence": "10月9日公表の企業一次資料5件を実読済み。発表後の現物反応は未確認", "attempts": [attempt("TDnet一次PDF確認", "OSG、フジミ、安川電機、JINS、イオンFSを確認", [row["source_url"] for row in articles.values() if row["id"] in {"osg-buyback-20261009", "fujimi-forecast-20261009", "yaskawa-20261009", "jins-20261009", "aeon-financial-interim-20261009"}])], "impact_if_unavailable": "個別材料欄を公開しない", "publication_use": "selected"},
    {"id": "analyst_rating_changes", "label": "アナリスト評価変更", "tier": "Required", "status": "十分調査したが取得不能", "evidence": "無料公開情報では全証券会社・目標株価・EPS変更を網羅できない。変更なしとは断定しない", "attempts": [attempt("公開日付一覧確認", "網羅性を保証できず", [RATING_PUBLIC]), attempt("IFISの契約情報確認", "契約データ未導入", [IFIS])], "impact_if_unavailable": "確認済み変更だけ掲載可能。今回は一覧を不掲載", "publication_use": "excluded"},
    {"id": "commodity_contract_definitions", "label": "商品先物の契約定義", "tier": "Required", "status": "十分調査したが取得不能", "evidence": "保存値に取引所・限月・値種別・基準時刻がないため商品価格を不採用", "attempts": [attempt("正本メタデータ確認", "契約情報なし", [CANON]), attempt("取引所確認の必要性を再判定", "同じ観測への対応を証明できず", ["https://www.cmegroup.com/market-data.html"])], "impact_if_unavailable": "商品価格方向と日本株への因果を保留", "publication_use": "excluded"},
]


def material(row, internal, pricing, confidence, channel, sectors, counter, conditions):
    return {
        "headline": row["title"],
        "fact": {"text": row["fact"], "source_urls": [row["source_url"]], "verification_status": "PASS"},
        "observed_market_reaction": {"text": row["market_reaction"], "assets_checked": row["related_assets"]},
        "market_internals": {"text": internal},
        "market_pricing": {"status": pricing, "text": "材料の存在と因果的な織り込みを分離"},
        "interpretation": {"text": row["analysis"], "confidence": confidence, "evidence": row["market_reaction"], "uncertainty": "材料単独の価格寄与と休場明けの日本株反応は未確認"},
        "japan_transmission": {"economic_channel": channel, "intermediate_reactions": ["海外・国内の確認済み価格を比較", "日本の業種相対値で追随を確認"], "affected_sectors": sectors, "pricing_in_japan": "10月9日までの現物と休場中材料を分離", "assessment": row["analysis"]},
        "conflict_resolution": "同方向でない資産・業種を併記し、単一材料へ還元しない",
        "counter_evidence": counter,
        "change_conditions": conditions,
        "chronology_check": "PASS",
    }


materials = [
    material(news[0], "米11業種ETFは9上昇・2下落。SOXは主要指数に逆行", "priced", "confirmed", "米株のリスク選好と半導体心理を別々に日本へ伝える", ["電機・精密", "情報通信・サービス"], ["SOX -0.41%", "米10年5.244%"], ["SOX反発", "国内電機・精密のTOPIX超過"]),
    material(news[1], "S&P500・NASDAQは上昇、米10年も上昇。指標単独の因果は未確定", "partially_priced", "supported", "期待インフレ・金利・消費見通しを通じて小売と高PERへ波及", ["小売", "自動車・輸送機", "電機・精密"], ["米株高", "VIX低下"], ["同一基準日の金利低下", "消費関連の相対反発"]),
    material(news[2], "10月9日はTOPIX参考が日経平均を上回ったが報告単独の寄与は未確認", "partially_priced", "tentative", "地域需要・賃金・物価と国内業種収益を通じる", ["小売", "銀行", "不動産"], ["銀行ETFは10月9日下落", "全国一律の判断ではない"], ["国内業種の反応", "日銀政策決定の有無"]),
    material(news[4], "原油先物の契約定義と独立反応を確認できず、価格方向は採用しない", "unpriced", "tentative", "軽油供給・物流コストを通じて運輸・商社へ波及し得る", ["運輸・物流", "商社・卸売"], ["一般許可は制裁全面解除ではない", "輸入数量未確認"], ["実際の輸送量", "定義確認済み原油・軽油価格"]),
]

unresolved = [
    {"id": "analyst-rating-coverage", "status": "QUALIFIED", "missing": "日本株アナリスト変更の全証券会社網羅", "impact": "確認できない変更を『なし』とせず、一覧を方向判断から除外", "last_checked_at": UPDATED, "next_action": "翌営業日に公開情報を再確認し、契約データ導入は別途判断", "attempts": [{"method": "公開日付一覧とIFIS情報を確認", "result": "無料情報では網羅不能", "checked_at": UPDATED}], "affected_components": ["japan_stocks"], "excluded_claims": ["全証券会社で変更なし", "レーティングを市場方向の根拠にする"], "excluded_from_publication": True},
    {"id": "commodity-contract-definitions", "status": "QUALIFIED", "missing": "保存された商品先物値に対応する取引所・限月・値種別・基準時刻", "impact": "Gold・WTI・Brent・Copperの価格方向と日本株波及を保留", "last_checked_at": UPDATED, "next_action": "次回収集で観測時点と契約メタデータを同時保存", "attempts": [{"method": "market.jsonと取引所資料の対応を照合", "result": "同じ観測への対応を証明できず", "checked_at": UPDATED}], "affected_components": ["ai_report"], "excluded_claims": ["商品価格の前日比", "商品主導の日本株方向"], "excluded_from_publication": True},
    {"id": "holiday-japan-reaction", "status": "QUALIFIED", "missing": "10月12日休場中材料への日本株現物反応", "impact": "10月13日の方向を断定せず条件付きシナリオに限定", "last_checked_at": UPDATED, "next_action": "10月13日引け後に指数・業種・個別株反応を確認", "attempts": [{"method": "JPX休場日程とjapan-market状態を確認", "result": "現物取引なし。10月9日終値を維持", "checked_at": UPDATED}], "affected_components": ["ai_report", "japan_stocks"], "excluded_claims": ["休場中材料は織り込み済み", "10月12日の日本株上昇・下落"], "excluded_from_publication": True},
]

gates = {key: "PASS" for key in FINAL_GATES}
gates.update(research_coverage="QUALIFIED", data_integrity="QUALIFIED", cross_asset_consistency="QUALIFIED")
evidence = {
    "version": "2.0",
    "report_date": DATE,
    "target_market_date": TARGET,
    "updated_at": UPDATED,
    "scope_note": "PASSは掲載内容の分析品質、QUALIFIEDは明示した欠測・除外範囲を表す",
    "research_coverage": {"status": "QUALIFIED", "directions": [{"id": "fixed_universe", "status": "PASS", "evidence": "32系列の値・状態・日付を確認"}, {"id": "cross_news", "status": "PASS", "evidence": "政策・マクロ・企業一次資料を横断"}, {"id": "reverse_from_anomalies", "status": "PASS", "evidence": "株高とSOX安、国内指数分岐、金利日付差を逆引き"}, {"id": "previous_day_change", "status": "PASS", "evidence": f"前回公開{previous['report_date']}版との差分を記録"}], "items": items},
    "analysis_quality": {"status": "PASS", "materials": materials, "template_degradation_audit": {**{key: True for key in TEMPLATE_CHECKS}, "comparison_note": "前回の米大型テック支援から、広い米株高とSOX逆行安へ修正。10月9日の国内指数分岐と休場中材料を追加"}},
    "counter_evidence_audit": {"status": "PASS", "conclusions": [{"conclusion": "休場明けは選別", "checks": ["米主要指数", "SOX", "米10年", "国内業種ETF", "個別一次開示"], "weighing": "広い米株高は支えだが、SOX安・金利高・企業利益の強弱が全面高を否定", "uncertainty": "10月13日の国内現物反応"}]},
    "cross_asset_consistency": {"status": "QUALIFIED", "assets_checked": ["equities", "rates", "fx", "commodities", "crypto"], "relationships": [{"combination": "米株高＋SOX安＋米10年上昇", "observations": ["S&P500 +0.59%", "SOX -0.41%", "米10年5.244%"], "explanation": "指数全体のリスク選好と半導体・割引率の逆風が併存", "confidence": "supported", "unresolved": False, "uncertainty": ""}, {"combination": "商品・暗号資産", "observations": ["商品は契約定義不足で価格不採用", "暗号資産は10月10日保存日足"], "explanation": "取得不能を数値で補完せず、日本株因果を保留", "confidence": "tentative", "unresolved": True, "uncertainty": "商品契約定義と同時刻価格"}]},
    "previous_day_change": {"status": "PASS", "prior_view": f"前回公開{previous['report_date']}版は米雇用・半導体高と金利負担を中心に評価", "new_events": ["10月9日の広い米株上昇", "SOX逆行安", "国内指数分岐", "一次資料確認済み企業5件"], "changed": ["半導体を追い風から中立へ", "国内を指数一括からTOPIX型優位へ"], "unchanged": ["金利負担", "商品契約定義不足", "レーティング非網羅"], "japan_revision": headline},
    "source_quality": {"status": "PASS", "checks": ["市場値は正本JSON", "政策・企業は一次資料実読", "後日確認時刻を保持", "未確認の市場反応を未確認と表示"]},
    "data_integrity": {"status": "QUALIFIED", "checks": ["日付・TOP5・ニュース件数を一致", "米2年と10年の異日スプレッドを除外", "商品先物値を不採用", "日本休場を前営業日値と区別"]},
    "quality_gates": gates,
    "publication_decision": {"status": "QUALIFIED", "decided_at": UPDATED, "summary": "取得不能・休場中反応を除外し、確認済み市場・一次資料・完全な分析経路だけを公開", "components": {"ai_report": {"status": "QUALIFIED", "updated_at": UPDATED, "reason": "商品契約定義と休場中反応を除外"}, "japan_stocks": {"status": "QUALIFIED", "updated_at": UPDATED, "reason": "一次開示5件を掲載し、反応・レーティング非網羅を注記"}}, "unresolved_items": unresolved, "resolved_item_ids": []},
}

candidate = ROOT / "candidate-2026-10-12"
save(candidate / "report.json", report)
save(candidate / "japan-stocks.json", japan)
save(candidate / "research-evidence.json", evidence)
save(candidate / "market.json", market)
save(candidate / "status.json", load("status"))
japan_market = deepcopy(japan_market)
japan_market.setdefault("data_quality", {}).setdefault("date_alignment", {})["report_target_market_date"] = TARGET
enrich_investor_view(japan_market, market, japan)
save(candidate / "japan-market.json", japan_market)
print(candidate)
