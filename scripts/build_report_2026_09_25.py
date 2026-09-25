#!/usr/bin/env python3
"""Build the researched 2026-09-25 morning-report publish candidate."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "candidate-2026-09-25"
MARKET = json.loads((ROOT / "data" / "market.json").read_text(encoding="utf-8"))
M = MARKET["markets"]
UPDATED = "2026-09-25 11:55 JST"


def pct(key):
    value = M[key].get("change_pct")
    return f"{value:+.2f}%" if isinstance(value, (int, float)) else "確認できず"


def news(title, fact, reaction, analysis, assets, sectors, importance, url, published):
    return {
        "title": title, "fact": fact, "published_at": published,
        "market_reaction": reaction, "analysis": analysis,
        "related_assets": assets, "related_japan_sectors": sectors,
        "importance": importance, "source_url": url,
        "image_url": None, "image_alt": None, "image_credit": None,
        "image_source_url": None,
    }


materials = [
    "米10年金利が5.162%へ上昇 → 高PER株の割引率負担が増す → 半導体・情報通信に向かい風",
    "SOXが-0.33% → 米半導体株の勢いが鈍る → 国内半導体・電機に弱い追い風しかない",
    "円安（1ドル158.793円） → 輸出採算を支える → 自動車・機械に追い風。ただし介入警戒",
    "Brentが+3.83% → 燃料・原料コスト懸念が再上昇 → 空運・陸運・化学に向かい風",
    "米・イランの段階的協議観測 → 原油高が一服する可能性 → 合意確認までは中立",
]

top_news = [
    {"title": "原油高と米長期金利上昇が重し。米株は方向感まちまち"},
    {"title": "米・イランが戦争終結へ段階案を協議との報道。合意は未確認"},
    {"title": "円安は輸出株を支える一方、1ドル160円接近で介入警戒"},
]

report_news = [
    news(
        "原油高と米長期金利上昇で米株は方向感まちまち",
        "9月24日はS&P500 -0.02%、NASDAQ総合 +0.01%、NASDAQ100 +0.03%、SOX -0.33%、NYダウ -0.31%。米10年債利回りは5.162%。",
        "主要指数は小幅まちまちだが、S&P500内では下落銘柄が上昇銘柄の約1.9倍。VIXは+3.23%。",
        "指数の小動きに対して内部は弱い。日本では円安だけで全面高を想定せず、半導体・高PER株と輸出株を分けて見る。",
        ["米10年債", "S&P500", "SOX", "VIX"],
        ["電機・精密", "情報通信・サービス", "自動車・輸送機"],
        "★★★★★",
        "https://www.reuters.com/business/wall-st-futures-fall-middle-east-uncertainties-ahead-trump-xi-talks-2026-09-24/",
        "2026-09-24 US close",
    ),
    news(
        "米・イランが段階的な戦争終結案を協議との報道",
        "Reutersは、イランのホルムズ海峡再開と米国の経済封鎖解除を含む段階案を米・イラン交渉担当者が検討していると報道。最終合意は確認できていない。",
        "米株は安値から戻した一方、Brentは終値ベースで107.03ドル、前日比+3.83%。",
        "合意なら原油・金利・輸送コストの逆風が和らぐ可能性があるが、報道だけで供給正常化を織り込まない。",
        ["Brent", "WTI", "米10年債"],
        ["エネルギー資源", "空運", "陸運", "素材・化学"],
        "★★★★★",
        "https://www.reuters.com/business/wall-st-futures-fall-middle-east-uncertainties-ahead-trump-xi-talks-2026-09-24/",
        "2026-09-24 US",
    ),
    news(
        "円は1ドル158円台後半、輸出支援と介入警戒が同居",
        "USD/JPYの日足終値は158.793円、前日比+0.84%。",
        "円安が続いた一方、160円接近では日本当局の対応への警戒が強まりやすい。",
        "自動車・機械の採算には追い風だが、輸入コスト上昇と急な円高反転の両方を監視する。",
        ["USD/JPY", "DXY"],
        ["自動車・輸送機", "機械", "小売", "運輸・物流"],
        "★★★★☆",
        "https://www.reuters.com/world/asia-pacific/volatile-yen-draws-intervention-watch-other-currencies-subdued-2026-09-21/",
        "2026-09-24 US close",
    ),
    news(
        "米中首脳会談は貿易休戦延長が焦点、最終成果は確認待ち",
        "米中は首脳会談に先立ち貿易休戦延長で合意したと米財務長官が説明。AI、重要鉱物、台湾、イランも論点。更新時点で首脳会談の最終共同発表は確認できていない。",
        "最終成果への市場反応は確認できず。",
        "会談開催ではなく、半導体規制・重要鉱物・関税の具体策で日本の機械、電機、非鉄への影響を判定する。",
        ["中国株", "半導体", "Copper"],
        ["機械", "電機・精密", "鉄鋼・非鉄", "自動車・輸送機"],
        "★★★★☆",
        "https://www.reuters.com/markets/europe/global-markets-view-europe-2026-09-24/",
        "2026-09-24",
    ),
]

market_data = [
    {
        "market": item["name"], "price": str(item.get("price", "確認できず")),
        "change": f"{item['change_pct']:+.2f}%" if isinstance(item.get("change_pct"), (int, float)) else "確認できず",
        "basis_time": item.get("market_date", "確認できず"), "source": "data/market.json",
        "confidence": "高" if item.get("status") == "取得成功" else "要確認",
        "status": item.get("status", "確認できず"),
    }
    for item in M.values()
]

scenarios = [
    {"name": "基本シナリオ", "conditions": "米10年金利が5.1%台、原油が高止まり、SOXが戻り切らない。", "impact_on_japan": "円安が輸出株を支える一方、半導体・高PER株と運輸には逆風が残り、方向感はまちまち。", "strong_sectors": ["自動車・輸送機", "機械"], "weak_sectors": ["情報通信・サービス", "空運", "不動産"], "invalidation": "米10年金利5%割れ、原油反落、SOX反発が同時に確認される。"},
    {"name": "上振れシナリオ", "conditions": "米・イラン合意で原油が反落し、米金利低下とSOX反発が続く。", "impact_on_japan": "半導体・電機と運輸へ追い風が広がる。", "strong_sectors": ["電機・精密", "情報通信・サービス", "運輸・物流"], "weak_sectors": ["エネルギー資源"], "invalidation": "協議決裂または原油・金利の再上昇。"},
    {"name": "下振れシナリオ", "conditions": "中東緊張激化で原油と米金利が一段高、SOX続落、円が急反発。", "impact_on_japan": "成長株、輸出株、運輸が同時に弱くなる。", "strong_sectors": ["確認できず"], "weak_sectors": ["電機・精密", "自動車・輸送機", "運輸・物流"], "invalidation": "原油と米金利が反落し、SOXが反発。"},
]

report = {
    "report_date": "2026-09-25", "target_market_date": "2026-09-24",
    "updated_at": UPDATED, "report_type": "daily", "week_period": None,
    "quick_view": {"headline": "今日の日本株は方向感がまちまち。円安は輸出株の追い風だが、原油高・米長期金利高・SOX安が成長株と運輸の重し。", "top_news": top_news, "important_today": ["米・イラン協議の具体的進展", "米10年金利が5.1%台を維持するか", "SOX反発と円相場の組み合わせ"]},
    "executive_summary": {"headline": "円安の追い風だけで全面高とは見にくい。原油・金利・SOXを業種別に読む日。", "market_mood": "方向感まちまち。米主要指数は小動きだが、S&P500内では下落銘柄が多い。", "main_driver": "原油高と米10年金利5.162%", "winners": ["米通信サービス", "米ヘルスケア", "円安恩恵の輸出株候補"], "losers": ["米素材・公益", "米半導体", "原油高に弱い運輸"], "important_today": ["米・イラン協議", "米中首脳会談の最終成果", "米金利とSOX"], "watch_markets": ["Brent", "米10年債", "SOX", "USD/JPY"], "current_environment": ["米10年金利5.162%", "Brent 107.03ドル", "円安158円台", "SOX -0.33%"]},
    "main_story": {"title": "原油高と米金利上昇が、日本株への円安効果を相殺", "fact": "Brent +3.83%、米10年債利回り5.162%、USD/JPY 158.793円、SOX -0.33%。", "market_reaction": "S&P500はほぼ横ばいだが、構成銘柄では下落が優勢。", "importance_reason": "円安は輸出株に追い風でも、金利は高PER株、原油は運輸・化学の負担になるため、指数一括ではなく業種別に見る必要がある。", "confidence": "高"},
    "news": report_news,
    "policy": {"fed": {"fact": "米10年金利は5.162%。Fed高官は年内の追加利上げ余地を示唆。", "market_reaction": "高PER株の上値を抑え、VIXは上昇。", "outlook": "金利が5%を下回るまでは成長株の負担が残る。"}, "us_iran": {"fact": "段階的な戦争終結案の協議が報じられたが、合意は未確認。", "market_reaction": "米株は安値から戻したが、原油はなお上昇。", "outlook": "ホルムズ海峡再開と封鎖解除の具体化を確認する。"}, "us_china": {"fact": "貿易休戦延長は前進したが、首脳会談の最終成果は確認待ち。", "market_reaction": "最終成果への反応は未確認。", "outlook": "半導体規制・重要鉱物・関税の具体策で判断する。"}},
    "scenarios": scenarios,
    "events": [
        {"event": "米中首脳会談の最終発表", "jst_time": "2026-09-25（確認時刻未定）", "consensus": "大規模合意より関係安定化", "previous": "貿易休戦延長で事前合意", "focus": "半導体規制、重要鉱物、関税、イラン", "affected_markets": ["中国株", "半導体", "Copper", "日本株"], "importance": "★★★★★"},
        {"event": "米・イラン協議", "jst_time": "時刻確認できず", "consensus": "確認できず", "previous": "段階案を検討との報道", "focus": "ホルムズ海峡再開と米国の封鎖解除", "affected_markets": ["原油", "米金利", "運輸株"], "importance": "★★★★★"},
    ],
    "market_data": market_data,
    "market_overview": [
        {"market": "米大型株", "move": f"S&P500 {pct('sp500')} / NYダウ {pct('dow')}", "relative_strength": "やや弱い", "background": "原油・金利上昇", "impact_on_japan": "全面高を支持しない"},
        {"market": "米ハイテク・半導体", "move": f"NASDAQ100 {pct('nasdaq100')} / SOX {pct('sox')}", "relative_strength": "半導体が弱い", "background": "長期金利5.162%", "impact_on_japan": "半導体・高PER株に向かい風"},
        {"market": "為替", "move": f"USD/JPY {M['usdjpy']['price']:.3f}（{pct('usdjpy')}）", "relative_strength": "円安", "background": "日米金利差", "impact_on_japan": "輸出に追い風、輸入コストと介入警戒"},
        {"market": "原油", "move": f"WTI {M['wti']['price']:.2f} / Brent {M['brent']['price']:.2f}", "relative_strength": "強い", "background": "供給不安", "impact_on_japan": "資源に追い風、運輸・化学に向かい風"},
    ],
    "changes_from_previous": ["米株の全面安から主要指数の小動きへ", "SOXは-1.23%から-0.33%へ下げ幅縮小", "米10年金利は5.114%から5.162%へ上昇", "Brentは下落から+3.83%へ反発", "米・イラン段階協議観測が浮上"],
    "internal_strength": {"large_vs_small": "S&P500 -0.02%、Russell2000 -0.11%。小型株がやや弱い。", "sectors": "通信サービス+1.27%、ヘルスケア+0.63%が上位。素材-1.19%、公益-0.98%、生活必需品-0.89%が下位。", "assessment": "指数は横ばいでもS&P500内の下落銘柄が上昇銘柄の約1.9倍。表面より弱い。"},
    "japan_market_links": [
        {"pair": "米10年金利 → 高PER株", "fact": "5.162%へ上昇", "usual_relation": "金利上昇は将来利益の現在価値を下げやすい", "consistency": "SOX下落で整合", "interpretation": "半導体・情報通信に向かい風", "confidence": "高"},
        {"pair": "円安 → 輸出採算", "fact": "USD/JPY 158.793円", "usual_relation": "円安は海外売上の円換算と輸出採算を支えやすい", "consistency": "日本株の当日反応は取引中", "interpretation": "自動車・機械に追い風。ただし160円接近で介入警戒", "confidence": "高"},
        {"pair": "原油高 → コスト", "fact": "Brent +3.83%", "usual_relation": "燃料・原料コストを押し上げやすい", "consistency": "米エネルギー株上昇で整合", "interpretation": "資源に追い風、運輸・化学に向かい風", "confidence": "高"},
    ],
    "commodities_crypto": {"commodities": {"gold": {"price": str(M['gold']['price']), "change": pct('gold'), "analysis": "ドル高・金利高の重し。日本株の固定主要材料にはしない。"}, "oil": {"price": f"WTI {M['wti']['price']} / Brent {M['brent']['price']}", "change": f"WTI {pct('wti')} / Brent {pct('brent')}", "analysis": "中東供給不安で上昇。米・イラン合意確認までは高止まりリスク。"}, "other": f"Copper {M['copper']['price']}（{pct('copper')}）。価格上昇は確認するが、在庫同日値を確認できないため需給を断定しない。"}, "crypto": {"btc": f"{M['btc']['price']:.2f}（{pct('btc')}）", "eth": f"{M['eth']['price']:.2f}（{pct('eth')}）", "xrp": "確認できず", "basis_time": "2026-09-24日足", "assessment": "小幅高で方向感は限定的。"}},
    "unusual_moves": [{"move": "原油・金利上昇でもNASDAQ100は小幅高", "usual_relation": "原油・金利上昇は高PER株の逆風になりやすい", "possible_reason": "Metaなど一部大型株の上昇が指数を支えた", "confidence": "中"}],
    "monitoring_points": [
        {"target": "原油と米・イラン協議", "current_view": "運輸・化学に向かい風", "today_check": "合意とホルムズ海峡再開の具体化", "view_change_condition": "Brent反落と合意確認で逆風を縮小"},
        {"target": "米10年金利とSOX", "current_view": "半導体・高PER株に向かい風", "today_check": "5.1%台とSOX反発の有無", "view_change_condition": "5%割れとSOX反発が同時に確認"},
        {"target": "USD/JPY", "current_view": "輸出に追い風、介入警戒", "today_check": "160円接近と当局対応", "view_change_condition": "急な円高反転で輸出株の見方を引き下げ"},
    ],
    "strength": [{"asset": "米大型株", "rating": 3, "comment": "指数はほぼ横ばい、内部は弱い"}, {"asset": "米半導体", "rating": 2, "comment": "SOX -0.33%"}, {"asset": "原油", "rating": 5, "comment": "WTI・Brentが上昇"}, {"asset": "円", "rating": 1, "comment": "対ドルで下落"}],
    "data_quality": {"overall": "要確認項目あり", "missing": ["日経225の9月24日正本値", "OSE日経平均先物の限月付き正式値", "CopperのLME・SHFE・COMEX同日在庫", "米中首脳会談の最終共同発表"], "differences": ["米2年債は9月23日、米10年債は9月24日。2年-10年差は算出しない", "TOPIXは指数そのものではなく1306 ETF参考値"], "excluded": ["限月を確認できない商品先物の厳密な終値解釈", "34監視銘柄による日本市場全体の上昇・下落の広がり判定", "外部記事の数値によるdata/market.json正本の置換"], "cautions": ["日本株は9月25日取引中のため当日値を終値として扱わない", "日経225の自動取得値は9月18日のため、今日の方向判断には使用しない", "商品値は連続先物の参考日足で、限月情報がない"]},
    "final_conclusion": {"headline": "方向感はまちまち。円安は輸出株を支えるが、原油高・米金利高・SOX安が相殺。", "winners": ["円安恩恵の輸出株候補", "資源株候補"], "losers": ["半導体・高PER株", "運輸・化学"], "top_three": ["原油と米・イラン協議", "米10年金利とSOX", "USD/JPYと介入警戒"], "triggers": ["Brent反落", "米10年金利5%割れ", "SOX反発", "急な円高反転"], "disclaimer": "確認できない数値は補完せず、取引中値を終値として扱いません。"},
    "japan_equities_preview": {"summary": "円安は輸出に追い風。ただし原油高・米金利高・SOX安で、日本株全体は方向感がまちまち。", "top_materials": materials, "focus_sectors": ["自動車・輸送機", "機械", "電機・精密", "運輸・物流", "エネルギー資源"], "top_stories": [], "total_story_count": 6},
    "source_notes": ["https://www.reuters.com/business/wall-st-futures-fall-middle-east-uncertainties-ahead-trump-xi-talks-2026-09-24/", "https://www.reuters.com/markets/europe/global-markets-view-europe-2026-09-24/", "https://www.reuters.com/world/asia-pacific/volatile-yen-draws-intervention-watch-other-currencies-subdued-2026-09-21/"],
}


def story(company, headline, category, fact, pricing, sectors, importance, url, analysis, watch):
    return {"company": company, "ticker": "-", "headline": headline, "category": category, "fact": fact, "announced_at": UPDATED, "timing": "9月25日取引中", "market_pricing_status": pricing, "price_reaction": "大引け未確認", "related_stocks": [], "related_sectors": sectors, "importance": importance, "confidence": "高", "source_url": url, "analysis": analysis, "today_watch": watch, "image_url": None, "image_alt": None, "image_credit": None, "image_source_url": None}


japan = {
    "report_date": "2026-09-25", "target_market_date": "2026-09-24", "updated_at": UPDATED, "report_type": "japan_stocks",
    "japan_quick_view": {"headline": "今日は方向感がまちまち。円安は輸出株に追い風だが、原油高・米金利高・SOX安が成長株と運輸の重し。", "top_materials": materials, "focus_sectors": ["自動車・輸送機", "機械", "電機・精密", "運輸・物流", "エネルギー資源"], "unpriced_materials": ["米中首脳会談の最終成果", "米・イラン協議の合意", "9月25日の日本株大引け反応"]},
    "top_stories": [
        story("半導体・高PER株", "米10年金利5.162%とSOX -0.33%が向かい風", "海外市場", "米金利上昇と米半導体株下落が同時発生。", "取引中", ["電機・精密", "情報通信・サービス"], "★★★★★", report["source_notes"][0], "割引率と米半導体株心理の両面で逆風。", "SOX反発と米10年金利5%割れ"),
        story("輸出株", "円安158.793円は追い風だが介入警戒", "為替", "USD/JPYは前日比+0.84%。", "一部織り込み中", ["自動車・輸送機", "機械"], "★★★★★", report["source_notes"][2], "輸出採算を支える一方、160円接近では円高反転リスクが増す。", "円相場と輸出株の相対強弱"),
        story("運輸・化学", "Brent 107.03ドルでコスト懸念が再上昇", "原油", "Brent +3.83%、WTI +2.82%。", "取引中", ["運輸・物流", "素材・化学"], "★★★★★", report["source_notes"][0], "燃料・原料コストの逆風。米・イラン合意で反転する可能性もある。", "原油と米・イラン協議"),
        story("エネルギー資源", "原油高は追い風候補、ただし外交で反転リスク", "原油", "米エネルギーETFは+0.37%。", "取引中", ["エネルギー資源", "商社・卸売"], "★★★★☆", report["source_notes"][0], "原油高は採算面の追い風だが、協議進展で急反落し得る。", "Brentの方向と業種ETFの相対騰落"),
    ],
    "important_stories": [
        story("中国関連株", "米中首脳会談の最終成果は確認待ち", "米中政策", "貿易休戦延長は前進したが、半導体・重要鉱物の具体策は確認待ち。", "結果待ち", ["機械", "電機・精密", "鉄鋼・非鉄"], "★★★★☆", report["source_notes"][1], "会談開催だけで好材料とは判定しない。", "共同発表と中国株の反応"),
        story("非鉄・商社", "Copper +1.43%、在庫未確認のため需給は断定しない", "Copper", "連続先物の参考日足は上昇。", "一部織り込み中", ["鉄鋼・非鉄", "商社・卸売"], "★★★☆☆", report["source_notes"][1], "価格は追い風候補だが、日本株主要材料の固定枠にはしない。", "業種ETFのTOPIX比と取引所在庫"),
    ],
    "other_stories": [], "company_events": [],
    "sector_implications": [
        {"driver": "円安", "affected_sectors": ["自動車・輸送機", "機械"], "possible_impact": "輸出採算に追い風", "confirmation_condition": "大引け後の業種ETFがTOPIXを上回るか"},
        {"driver": "米金利高・SOX安", "affected_sectors": ["電機・精密", "情報通信・サービス"], "possible_impact": "向かい風", "confirmation_condition": "SOX反発と米10年金利5%割れ"},
        {"driver": "原油高", "affected_sectors": ["エネルギー資源", "運輸・物流", "素材・化学"], "possible_impact": "資源に追い風、運輸・化学に向かい風", "confirmation_condition": "Brentと各業種ETFの相対騰落"},
    ],
    "data_quality": {"overall": "要確認項目あり", "missing": ["日経225の9月24日正本値", "9月25日大引け値", "TDnet全件の完全網羅"], "differences": ["海外市場の主対象日は9月24日、日本株は9月25日取引中", "TOPIXは1306 ETF参考値"], "unpriced": ["米中首脳会談最終成果", "米・イラン合意", "9月25日日本株終値"], "cautions": ["取引中値を終値として扱わない", "34監視銘柄から日本市場全体を評価しない", "セクター全体を主要2銘柄で評価しない"]},
    "source_notes": report["source_notes"],
}

OUT.mkdir(exist_ok=True)
us2y = MARKET["markets"].get("us2y", {})
if us2y.get("market_date") != MARKET["markets"]["us10y"].get("market_date"):
    us2y["stale_reason"] = "FRED DGS2の公表タイミング差。最新公表値を維持し、同日でない米10年債とのスプレッドは算出しません"
nikkei = MARKET["markets"].get("nikkei225", {})
if nikkei.get("market_date") != report["target_market_date"]:
    nikkei["stale_reason"] = "Yahoo Financeの日経225日足が9月18日以降更新されていないため保存値を維持。今日の方向判断には使用しません"
for name, payload in (("report.json", report), ("japan-stocks.json", japan), ("market.json", MARKET)):
    (OUT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(OUT)
