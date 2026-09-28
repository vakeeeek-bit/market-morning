#!/usr/bin/env python3
"""Build the researched weekend reports for 2026-09-26 and 2026-09-27."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from company_news_2026_09_25_28 import apply_company_news


ROOT = Path(__file__).resolve().parents[1]
MARKET = json.loads((ROOT / "data" / "market.json").read_text(encoding="utf-8"))
M = MARKET["markets"]
TARGET = "2026-09-25"

WHITE_HOUSE = "https://www.whitehouse.gov/fact-sheets/2026/09/fact-sheet-president-donald-j-trump-advances-a-fair-and-reciprocal-relationship-with-china-while-hosting-historic-state-visit/"
REUTERS_IRAN_PLAN = "https://www.reuters.com/world/middle-east/iran-ready-reopen-strait-hormuz-if-us-eases-military-pressure-lifts-blockade-2026-09-22/"
REUTERS_IRAN_REJECTED = "https://www.reuters.com/world/middle-east/iran-awaits-us-move-after-wsj-report-says-trump-rejects-peace-plan-2026-09-26/"
REUTERS_IRAN_SUNDAY = "https://www.reuters.com/world/middle-east/iran-insists-diplomatic-solution-after-trump-rejects-peace-plan-2026-09-27/"
BOJ_SCHEDULE = "https://www.boj.or.jp/en/about/calendar/index.htm"
BEA_SCHEDULE = "https://www.bea.gov/news/schedule"
BLS_SCHEDULE = "https://www.bls.gov/schedule/news_release/empsit.htm"


def pct(key: str) -> str:
    value = M[key].get("change_pct")
    return f"{value:+.2f}%" if isinstance(value, (int, float)) else "確認できず"


def market_data() -> list[dict]:
    return [
        {
            "market": item["name"],
            "price": str(item.get("price", "確認できず")),
            "change": pct(key),
            "basis_time": item.get("market_date", "確認できず"),
            "source": "data/market.json",
            "confidence": "高" if item.get("status") == "取得成功" else "要確認",
            "status": item.get("status", "確認できず"),
        }
        for key, item in M.items()
    ]


def news(title: str, fact: str, reaction: str, analysis: str, assets: list[str], sectors: list[str], importance: str, url: str, published: str) -> dict:
    return {
        "title": title,
        "fact": fact,
        "published_at": published,
        "market_reaction": reaction,
        "analysis": analysis,
        "related_assets": assets,
        "related_japan_sectors": sectors,
        "importance": importance,
        "source_url": url,
        "image_url": None,
        "image_alt": None,
        "image_credit": None,
        "image_source_url": None,
    }


def story(company: str, headline: str, category: str, fact: str, pricing: str, sectors: list[str], importance: str, url: str, analysis: str, watch: str, updated: str) -> dict:
    return {
        "company": company,
        "ticker": "-",
        "headline": headline,
        "category": category,
        "fact": fact,
        "announced_at": updated,
        "timing": "週末・東証休場",
        "market_pricing_status": pricing,
        "price_reaction": "東証休場のため未確認",
        "related_stocks": [],
        "related_sectors": sectors,
        "importance": importance,
        "confidence": "高",
        "source_url": url,
        "analysis": analysis,
        "today_watch": watch,
        "image_url": None,
        "image_alt": None,
        "image_credit": None,
        "image_source_url": None,
    }


def base_report(report_date: str, updated: str, sunday: bool) -> tuple[dict, dict]:
    iran_status = (
        "トランプ米大統領がイラン案を拒否したと表明し、イランは外交解決を主張。金曜の原油反落後に判明したため、月曜の価格には未反映。"
        if sunday
        else "イランの7日間案をトランプ米大統領が拒否したとの報道。イランは正式回答を待つとしており、金曜終値には未反映。"
    )
    iran_source = REUTERS_IRAN_SUNDAY if sunday else REUTERS_IRAN_REJECTED
    headline = (
        "金曜は日米株が上昇。ただし米国のイラン案拒否で、原油安という追い風は月曜まで続くと決めつけない。"
        if sunday
        else "金曜は日米株が上昇。半導体株高と原油安が追い風だが、円高と週末の中東情勢が月曜の注意点。"
    )
    top_materials = [
        "SOX +1.41% → 米半導体株の地合い改善 → 電機・精密、機械に追い風",
        "円高（1ドル157.185円、-1.02%）→ 輸出採算の追い風が弱まる → 自動車・機械に向かい風",
        "WTI -2.33% → 燃料・原料コストが低下 → 運輸・素材に追い風。ただし週末のイラン情勢は未反映",
        "米10年金利5.184%へ上昇 → 高PER株の割引率負担が増す → 情報通信・高PER株に向かい風",
        "米中首脳会談で限定的な通商前進 → 中国関連需要の不透明感が一部後退 → 機械・素材を監視。レアアース問題は未解決",
    ]
    top_news = [
        {"title": "日経平均+1.30%、TOPIX参考値+1.29%。金曜の日本株は主要指数がそろって上昇"},
        {"title": "SOX+1.41%、米工業株+0.95%。月曜の電機・機械に追い風候補"},
        {"title": "米国がイラン案を拒否。金曜の原油-2%台は月曜にそのまま引き継がれない可能性"},
    ]
    report_news = [
        news(
            "金曜の日米株は上昇、半導体と景気敏感株が優位",
            f"9月25日はS&P500 {pct('sp500')}、NYダウ {pct('dow')}、SOX {pct('sox')}。日経平均は{pct('nikkei225')}、TOPIX参考値は{pct('topix')}。",
            "VIXは-5.11%。米国では工業+0.95%、情報技術+0.80%が上位だった。",
            "月曜の日本株には電機・精密と機械への追い風候補。ただし金曜に日本株も上昇済みで、追随余地は個別確認が必要。",
            ["日経平均", "TOPIX", "S&P500", "SOX", "VIX"],
            ["電機・精密", "機械", "銀行"],
            "★★★★★",
            "https://finance.yahoo.com/quote/%5EN225/history/",
            "2026-09-25 close",
        ),
        news(
            "米国がイランの7日間案を拒否、中東リスクは月曜に未反映",
            iran_status,
            "WTI -2.33%、Brent -2.14%は9月25日終値。拒否表明後の新しい日足反応はまだない。",
            "金曜の原油安を運輸・化学への恒久的な追い風と見なさない。月曜は原油の窓開けと海峡再開交渉を優先確認する。",
            ["WTI", "Brent", "米10年債"],
            ["運輸・物流", "エネルギー資源", "素材・化学"],
            "★★★★★",
            iran_source,
            "2026-09-27" if sunday else "2026-09-26",
        ),
        news(
            "米中首脳会談は限定的な通商前進、レアアース問題は未解決",
            "米政府は双方300億ドル分の非センシティブ品への有利な関税待遇、農業作業部会、中国による2027・2028年の米国産石炭各1000万トン以上の輸入などを発表。一方、レアアース供給不足は協議継続。",
            "会談後の金曜米株は上昇したが、個別施策だけの寄与は分離できない。",
            "中国関連株には不透明感後退の材料だが、重要鉱物の供給制約が解消したとは扱わない。",
            ["中国株", "石炭", "レアアース"],
            ["機械", "鉄鋼・非鉄", "商社・卸売"],
            "★★★★☆",
            WHITE_HOUSE,
            "2026-09-25",
        ),
        news(
            "円高と米長期金利上昇が株高の中の逆風",
            f"USD/JPYは{M['usdjpy']['price']:.3f}円（{pct('usdjpy')}）、米10年債利回りは{M['us10y']['price']:.3f}%（{pct('us10y')}）。",
            "ドル指数は-0.32%。円高方向と米長期金利上昇が同時に進んだ。",
            "輸出株は米株高だけで一括評価せず、為替感応度を確認。高PER株には金利面の負担が残る。",
            ["USD/JPY", "米10年債", "DXY"],
            ["自動車・輸送機", "機械", "情報通信・サービス"],
            "★★★★☆",
            "https://finance.yahoo.com/quote/JPY=X/history/",
            "2026-09-26 FX close",
        ),
    ]
    scenarios = [
        {
            "name": "基本シナリオ",
            "conditions": "原油が金曜終値付近にとどまり、SOX高の流れが続く一方、円は157円台、米10年金利は5.1%台。",
            "impact_on_japan": "電機・精密と機械が相対的に支えられるが、輸出株は円高、高PER株は金利高で上値が限られる。",
            "strong_sectors": ["電機・精密", "機械", "銀行"],
            "weak_sectors": ["情報通信・サービス", "自動車・輸送機"],
            "invalidation": "原油急騰、SOX反落、円高加速のうち2つ以上が同時に発生。",
        },
        {
            "name": "上振れシナリオ",
            "conditions": "外交協議が再開し原油が続落、米金利も低下、SOXが続伸。",
            "impact_on_japan": "半導体・機械に加え、運輸・素材にも追い風が広がる。",
            "strong_sectors": ["電機・精密", "機械", "運輸・物流", "素材・化学"],
            "weak_sectors": ["エネルギー資源"],
            "invalidation": "イラン情勢悪化による原油反発、またはSOX反落。",
        },
        {
            "name": "下振れシナリオ",
            "conditions": "イラン情勢悪化で原油が急反発し、円高と米金利高が継続、SOXも反落。",
            "impact_on_japan": "輸出、成長、運輸が同時に弱くなり、金曜高の反動が出る。",
            "strong_sectors": ["エネルギー資源"],
            "weak_sectors": ["自動車・輸送機", "情報通信・サービス", "運輸・物流"],
            "invalidation": "原油反落とSOX反発が同時に確認される。",
        },
    ]
    report = {
        "report_date": report_date,
        "target_market_date": TARGET,
        "updated_at": updated,
        "report_type": "weekend",
        "week_period": None,
        "quick_view": {"headline": headline, "top_news": top_news, "important_today": ["イラン情勢後の原油初動", "円相場と輸出株", "SOX高が日本の電機・精密へ続くか"]},
        "executive_summary": {
            "headline": headline,
            "market_mood": "金曜は日米とも株高。月曜は週末の中東材料を織り込むため、金曜の原油安をそのまま延長しない。",
            "main_driver": "SOX高と原油安。ただしイラン案拒否は未反映",
            "winners": ["米半導体", "米工業株", "金曜の日本の銀行・電機・運輸"],
            "losers": ["米エネルギー", "米通信サービス", "円高に弱い輸出株候補"],
            "important_today": ["イラン情勢", "米中会談の具体策", "月曜の原油・円・SOX"],
            "watch_markets": ["WTI・Brent", "SOX", "USD/JPY", "米10年債"],
            "current_environment": ["日経平均+1.30%", "SOX+1.41%", "WTI-2.33%", "円高157円台", "米10年5.184%"],
        },
        "main_story": {
            "title": "金曜の株高に、週末の中東リスクが重なる",
            "fact": "日米株は上昇し原油は下落したが、その後に米国のイラン案拒否が判明。",
            "market_reaction": "拒否表明後の日本株と主要商品の日足反応はまだ確認できない。",
            "importance_reason": "月曜は金曜終値の延長ではなく、原油の新しい価格反応で運輸・資源・素材の見方を更新する必要がある。",
            "confidence": "高",
        },
        "news": report_news,
        "policy": {
            "us_iran": {"fact": iran_status, "market_reaction": "金曜終値には未反映", "outlook": "原油とホルムズ海峡交渉の初動で判断"},
            "us_china": {"fact": "関税・農業・石炭で限定的な合意。レアアース供給不足は協議継続。", "market_reaction": "金曜米株は上昇したが寄与は分離できない", "outlook": "実施時期と重要鉱物の進展を確認"},
            "fed": {"fact": "米10年金利は5.184%。米2年金利は公表が1日遅れ。", "market_reaction": "SOXは上昇したが高PER株の割引率負担は残る", "outlook": "長短金利差は算出せず、10年金利の方向を確認"},
        },
        "scenarios": scenarios,
        "events": [
            {"event": "日銀会合議事要旨・企業向けサービス価格指数", "jst_time": "2026-09-28 08:50 JST", "consensus": "確認できず", "previous": "確認できず", "focus": "金利・賃金・サービス価格の示唆", "affected_markets": ["円", "銀行", "不動産"], "importance": "★★★★☆"},
            {"event": "米個人所得・支出（8月）", "jst_time": "2026-09-30 21:30 JST", "consensus": "確認できず", "previous": "確認できず", "focus": "PCE物価と消費", "affected_markets": ["米金利", "ドル", "日本株"], "importance": "★★★★★"},
            {"event": "日銀短観（9月）・金融政策決定会合の主な意見", "jst_time": "2026-10-01 08:50 JST", "consensus": "確認できず", "previous": "確認できず", "focus": "企業景況感、設備投資、物価見通し", "affected_markets": ["日本株", "円", "銀行"], "importance": "★★★★★"},
            {"event": "米雇用統計（9月）", "jst_time": "2026-10-02 21:30 JST", "consensus": "確認できず", "previous": "確認できず", "focus": "雇用者数、失業率、賃金", "affected_markets": ["米金利", "ドル", "世界株"], "importance": "★★★★★"},
        ],
        "market_data": market_data(),
        "market_overview": [
            {"market": "日本株（金曜終値）", "move": f"日経平均 {pct('nikkei225')} / TOPIX参考値 {pct('topix')}", "relative_strength": "強い", "background": "主要指数がそろって上昇", "impact_on_japan": "金曜時点は広く買い優勢"},
            {"market": "米半導体・工業", "move": f"SOX {pct('sox')} / 米工業ETF {pct('sector_xli')}", "relative_strength": "強い", "background": "リスク選好", "impact_on_japan": "電機・精密、機械に追い風候補"},
            {"market": "為替・金利", "move": f"USD/JPY {pct('usdjpy')} / 米10年 {M['us10y']['price']:.3f}%", "relative_strength": "円高・金利高", "background": "ドル安と長期金利上昇が併存", "impact_on_japan": "輸出と高PER株に逆風"},
            {"market": "原油", "move": f"WTI {pct('wti')} / Brent {pct('brent')}", "relative_strength": "金曜は下落", "background": "外交期待。ただし拒否表明は未反映", "impact_on_japan": "月曜の初動確認まで運輸追い風を保留"},
        ],
        "changes_from_previous": ["日経平均の取得値が9月25日終値へ更新され、古い9月18日値の問題は解消", "SOXは+1.41%へ反発", "WTI・Brentは2%台下落", "USD/JPYは1.02%下落し円高", "米国のイラン案拒否が週末に判明"],
        "internal_strength": {"large_vs_small": f"S&P500 {pct('sp500')}、Russell2000 {pct('russell2000')}。大型株が相対優位。", "sectors": "米工業+0.95%、情報技術+0.80%、金融+0.57%が上位。通信サービス-0.90%、エネルギー-0.89%が下位。", "assessment": "金曜の米国は指数上昇とVIX低下でリスク選好。ただし小型株はほぼ横ばい。"},
        "japan_market_links": [
            {"pair": "SOX高 → 国内半導体", "fact": "SOX +1.41%", "usual_relation": "米半導体株の投資家心理が国内関連株へ波及しやすい", "consistency": "金曜の電機・精密ETFは+1.57%", "interpretation": "電機・精密、機械に追い風候補", "confidence": "高"},
            {"pair": "円高 → 輸出採算", "fact": "USD/JPY 157.185円、-1.02%", "usual_relation": "円高は海外売上の円換算と輸出採算を押し下げやすい", "consistency": "月曜の日本株反応は未確認", "interpretation": "自動車・機械に向かい風", "confidence": "高"},
            {"pair": "原油安 → 燃料・原料コスト", "fact": "WTI -2.33%、Brent -2.14%", "usual_relation": "原油安は運輸・素材のコストを下げやすい", "consistency": "週末のイラン案拒否は金曜価格に未反映", "interpretation": "月曜の原油初動まで判断を保留", "confidence": "高"},
        ],
        "commodities_crypto": {
            "commodities": {
                "gold": {"price": str(M["gold"]["price"]), "change": pct("gold"), "analysis": "小幅高。日本株の固定主要材料にはしない。"},
                "oil": {"price": f"WTI {M['wti']['price']} / Brent {M['brent']['price']}", "change": f"WTI {pct('wti')} / Brent {pct('brent')}", "analysis": "金曜は下落したが、週末のイラン案拒否は未反映。"},
                "other": f"Copper {M['copper']['price']}（{pct('copper')}）。小幅安で、日本株の主要材料には選ばない。",
            },
            "crypto": {"btc": f"{M['btc']['price']:.2f}（{pct('btc')}）", "eth": f"{M['eth']['price']:.2f}（{pct('eth')}）", "xrp": "確認できず", "basis_time": "2026-09-27日足", "assessment": "週末も小幅高。日本株への波及は限定的。" if sunday else "9月26日分を後日作成したため、9月27日付の暗号資産値は当日の判断に使用しない。"},
        },
        "unusual_moves": [{"move": "米10年金利上昇でもSOXが+1.41%", "usual_relation": "長期金利上昇は高PER株の逆風になりやすい", "possible_reason": "金曜は半導体・工業への買いが金利負担を上回った可能性", "confidence": "中"}],
        "monitoring_points": [
            {"target": "イラン情勢と原油", "current_view": "金曜の原油安は運輸・素材に追い風", "today_check": "拒否表明後のWTI・Brent初動", "view_change_condition": "原油急反発なら運輸追い風を撤回し、資源を上方修正"},
            {"target": "SOXと電機・精密", "current_view": "追い風候補", "today_check": "SOXの続伸と国内ETFのTOPIX比", "view_change_condition": "SOX反落または国内ETFがTOPIXを下回れば影響を弱く見る"},
            {"target": "USD/JPY", "current_view": "輸出株に向かい風", "today_check": "157円台からの方向", "view_change_condition": "円安へ反転し輸出ETFも上向けば見方を修正"},
        ],
        "strength": [{"asset": "日本株（金曜）", "rating": 4, "comment": "日経平均・TOPIX参考値がともに約1.3%上昇"}, {"asset": "米半導体", "rating": 4, "comment": "SOX +1.41%"}, {"asset": "原油（金曜）", "rating": 2, "comment": "2%台下落。ただし週末材料は未反映"}, {"asset": "円", "rating": 4, "comment": "対ドルで1.02%上昇"}],
        "data_quality": {
            "overall": "正常（注意事項あり）",
            "missing": ["OSE日経平均先物の限月付き正式値", "週末のイラン情勢を反映した原油・日本株の価格反応"],
            "differences": ["米2年債は9月24日、米10年債は9月25日。長短金利差は算出しない", "TOPIXは指数そのものではなく1306 ETF参考値", "USD/JPYは9月26日付、現物日本株は9月25日終値"],
            "excluded": ["34監視銘柄による日本市場全体の上昇・下落の広がり判定", "各業種2銘柄によるセクター全体評価", "推定値の実測値扱い", "Copper・Goldの固定主要材料化"],
            "cautions": ["土日は東証休場。金曜終値を週末当日の値動きとして扱わない", "商品値は連続先物の参考日足で限月付き清算値ではない", "週末ニュースは月曜市場に未反映"],
        },
        "final_conclusion": {"headline": headline, "winners": ["半導体・電機候補", "機械候補", "原油安が続く場合の運輸・素材"], "losers": ["円高に弱い輸出株候補", "高PER株", "原油が反発した場合の運輸"], "top_three": ["原油の月曜初動", "SOXと国内電機・精密", "USD/JPY"], "triggers": ["原油急反発", "SOX反落", "156円台への円高", "米10年金利5%割れ"], "disclaimer": "休場中のため、週末ニュースの価格反応は確認できません。確認できない値は補完しません。"},
        "japan_equities_preview": {"summary": headline, "top_materials": top_materials, "focus_sectors": ["電機・精密", "機械", "銀行", "運輸・物流", "自動車・輸送機"], "top_stories": [], "total_story_count": 6},
        "source_notes": [WHITE_HOUSE, REUTERS_IRAN_PLAN, iran_source, BOJ_SCHEDULE, BEA_SCHEDULE, BLS_SCHEDULE, "data/market.json", "data/japan-market.json"],
    }

    japan = {
        "report_date": report_date,
        "target_market_date": TARGET,
        "updated_at": updated,
        "report_type": "japan_stocks",
        "japan_quick_view": {"headline": headline, "top_materials": top_materials, "focus_sectors": ["電機・精密", "機械", "銀行", "運輸・物流", "自動車・輸送機"], "unpriced_materials": ["米国のイラン案拒否後の原油反応", "月曜の日本株現物", "円高とSOX高のどちらを重く見るか"]},
        "top_stories": [
            story("半導体・電機", "SOX +1.41%は月曜の追い風候補", "海外市場", "米半導体株は金曜に上昇。日本の電機・精密ETFも金曜+1.57%。", "金曜分は織り込み済み・月曜分は未反映", ["電機・精密", "機械"], "★★★★★", "https://finance.yahoo.com/quote/%5ESOX/history/", "米半導体高は追い風だが、日本株も金曜に上昇済み。月曜は追加上昇の有無をTOPIX比で確認する。", "SOXの続伸と電機・精密ETFのTOPIX比", updated),
            story("運輸・資源・素材", "原油安の追い風に週末のイラン案拒否が重なる", "原油・外交", iran_status, "週末材料は未反映", ["運輸・物流", "エネルギー資源", "素材・化学"], "★★★★★", iran_source, "原油の方向が業種間の勝ち負けを反転させ得る。金曜の原油安だけで月曜を決めない。", "拒否表明後のWTI・Brentと業種ETF", updated),
            story("輸出株", "円高157円台で米株高の追い風を一部相殺", "為替", f"USD/JPYは{M['usdjpy']['price']:.3f}円、前日比{pct('usdjpy')}。", "月曜の日本株には未反映", ["自動車・輸送機", "機械"], "★★★★★", "https://finance.yahoo.com/quote/JPY=X/history/", "自動車・機械はSOXや米工業株高だけでなく、円高の逆風も同時に評価する。", "ドル円と輸出型ETFのTOPIX比", updated),
            story("銀行・高PER株", "米10年金利5.184%、銀行には追い風候補・高PER株には逆風", "金利", "米10年金利は上昇。米2年金利は1日古いため長短金利差は算出しない。", "金曜分は一部織り込み済み", ["銀行", "情報通信・サービス", "電機・精密"], "★★★★☆", "https://fred.stlouisfed.org/series/DGS10", "金利上昇の影響は銀行と高PER株で方向が異なる。", "米10年金利と銀行ETF・情報通信ETFの相対方向", updated),
        ],
        "important_stories": [
            story("中国関連株", "米中会談は限定前進、レアアースは未解決", "米中政策", "有利な関税待遇、農業作業部会、石炭輸入目標が発表された一方、レアアース供給不足は協議継続。", "金曜分は一部織り込み済み", ["機械", "鉄鋼・非鉄", "商社・卸売"], "★★★★☆", WHITE_HOUSE, "会談開催そのものではなく、具体策と未解決点を分けて評価する。", "中国市場と重要鉱物の続報", updated),
            story("金曜の業種ETF", "銀行+3.49%が首位、電機・精密+1.57%、運輸+1.52%", "セクター", "TOPIX-17業種ETF自身の9月25日騰落。金融（銀行除く）は-0.72%、電力・ガスは-0.36%。", "金曜終値で確認済み", ["銀行", "電機・精密", "運輸・物流", "金融（銀行除く）"], "★★★★☆", "https://finance.yahoo.co.jp/quote/1631.T/history", "2銘柄の代理ではなく、業種ETF自身の価格・出来高・5日推移を使用。", "月曜のTOPIX比と出来高", updated),
        ],
        "other_stories": [],
        "company_events": [],
        "sector_implications": [
            {"driver": "SOX高", "affected_sectors": ["電機・精密", "機械"], "possible_impact": "追い風候補", "confirmation_condition": "月曜の業種ETFがTOPIXを上回る"},
            {"driver": "円高", "affected_sectors": ["自動車・輸送機", "機械"], "possible_impact": "輸出採算に向かい風", "confirmation_condition": "円高継続と外需ETFのTOPIX比低下"},
            {"driver": "原油とイラン情勢", "affected_sectors": ["運輸・物流", "エネルギー資源", "素材・化学"], "possible_impact": "原油が反発すれば金曜の関係が逆転", "confirmation_condition": "月曜のWTI・Brent初動と業種ETF"},
        ],
        "data_quality": {"overall": "正常（注意事項あり）", "missing": ["週末ニュース後の月曜価格反応", "OSE先物の限月付き正式値", "TDnet全件の完全網羅"], "differences": ["日本株・米株は9月25日終値、USD/JPYは9月26日付、暗号資産は9月27日付", "TOPIXは1306 ETF参考値"], "unpriced": ["米国のイラン案拒否", "週末の外交続報", "月曜の日本株現物"], "cautions": ["34監視銘柄から日本市場全体を評価しない", "セクター全体を主要2銘柄で評価しない", "休場とデータ異常を区別する"]},
        "source_notes": report["source_notes"],
    }
    apply_company_news(report, japan, report_date)
    return report, japan


def write_candidate(report_date: str, updated: str, sunday: bool) -> None:
    report, japan = base_report(report_date, updated, sunday)
    market = copy.deepcopy(MARKET)
    us2y = market["markets"].get("us2y", {})
    if us2y.get("market_date") != market["markets"]["us10y"].get("market_date"):
        us2y["stale_reason"] = "FRED DGS2の公表タイミング差。最新公表値を維持し、同日でない米10年債とのスプレッドは算出しません"
    output = ROOT / f"candidate-{report_date}"
    output.mkdir(exist_ok=True)
    for name, payload in (("report.json", report), ("japan-stocks.json", japan), ("market.json", market)):
        (output / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(output)


write_candidate("2026-09-26", "2026-09-27 10:25 JST（9月26日分を後日作成）", sunday=False)
write_candidate("2026-09-27", "2026-09-27 10:25 JST", sunday=True)
