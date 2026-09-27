#!/usr/bin/env python3
"""Build the researched pre-open report for 2026-09-28."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from update_japan_market import enrich_investor_view


ROOT = Path(__file__).resolve().parents[1]
REPORT_DATE = "2026-09-28"
TARGET_DATE = "2026-09-25"
UPDATED = "2026-09-28 07:25 JST"

WHITE_HOUSE = "https://www.whitehouse.gov/fact-sheets/2026/09/fact-sheet-president-donald-j-trump-advances-a-fair-and-reciprocal-relationship-with-china-while-hosting-historic-state-visit/"
REUTERS_IRAN = "https://www.reuters.com/world/middle-east/iran-insists-diplomatic-solution-after-trump-rejects-peace-plan-2026-09-27/"
BOJ_SCHEDULE = "https://www.boj.or.jp/en/about/calendar/index.htm"
BEA_SCHEDULE = "https://www.bea.gov/news/schedule"
BLS_SCHEDULE = "https://www.bls.gov/schedule/news_release/empsit.htm"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def dump(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def market_row(markets: dict, key: str) -> dict:
    item = markets[key]
    change = item.get("change_pct")
    return {
        "market": item["name"],
        "price": str(item.get("price", "確認できず")),
        "change": f"{change:+.2f}%" if isinstance(change, (int, float)) else "確認できず",
        "basis_time": item.get("market_date", "確認できず"),
        "source": "data/market.json",
        "confidence": "高" if item.get("status") == "取得成功" else "要確認",
        "status": item.get("status", "確認できず"),
    }


def story(
    company: str,
    headline: str,
    category: str,
    fact: str,
    pricing: str,
    sectors: list[str],
    importance: str,
    source_url: str,
    analysis: str,
    today_watch: str,
) -> dict:
    return {
        "company": company,
        "ticker": "-",
        "headline": headline,
        "category": category,
        "fact": fact,
        "announced_at": UPDATED,
        "timing": "取引開始前",
        "market_pricing_status": pricing,
        "price_reaction": "東証寄り付き前のため未確認",
        "related_stocks": [],
        "related_sectors": sectors,
        "importance": importance,
        "confidence": "高",
        "source_url": source_url,
        "analysis": analysis,
        "today_watch": today_watch,
        "image_url": None,
        "image_alt": None,
        "image_credit": None,
        "image_source_url": None,
    }


def main() -> None:
    report = load("data/history/2026-09-27/report.json")
    japan = load("data/history/2026-09-27/japan-stocks.json")
    japan_market = load("data/japan-market.json")
    market = load("data/market.json")
    prior_market = load("data/history/2026-09-27/market.json")

    # Closed futures must not be silently rewritten by a later front-contract refresh.
    # Preserve the already validated same-session snapshot for the affected contracts.
    for key in ("silver", "copper", "brent"):
        current = market["markets"][key]
        prior = prior_market["markets"][key]
        if current.get("market_date") == prior.get("market_date"):
            market["markets"][key] = copy.deepcopy(prior)
    market["notes"]["same_date_stability"] = (
        "9月28日朝の再取得で同じ9月25日の先物値が変わったSilver・Copper・Brentは、"
        "前日までに検証済みの同日スナップショットを維持"
    )

    m = market["markets"]
    headline = (
        "寄り付き前の見方は強弱まちまち。金曜の株高とSOX高は支えだが、"
        "週末のイラン情勢を受けた原油初動と8時50分の日銀資料を確認する。"
    )
    top_materials = [
        "SOX +1.41% → 米半導体株の地合い改善 → 電機・精密に追い風候補",
        "ドル円157円台 → 金曜中に円高が進行 → 自動車・機械の上値を抑えやすい",
        "米国がイラン案を拒否 → 金曜の原油安後に判明 → 運輸・資源の見方は原油初動で決める",
        "米10年金利5.184% → 高PER株の割引率負担が残る → 情報通信・高PER株に向かい風",
        "米中会談は限定前進 → 関税・農業は改善、レアアースは未解決 → 機械・素材は選別",
    ]

    report.update(
        report_date=REPORT_DATE,
        target_market_date=TARGET_DATE,
        updated_at=UPDATED,
        report_type="daily",
        week_period=None,
    )
    report["quick_view"] = {
        "headline": headline,
        "top_news": [
            {"title": "寄り付き前は強弱まちまち。日米株高に週末の中東リスクが重なる"},
            {"title": "SOX+1.41%は電機・精密の支え。ドル円157円台は輸出株の重し"},
            {"title": "8時50分に日銀会合議事要旨と企業向けサービス価格指数"},
        ],
        "important_today": [
            "イラン案拒否後の原油初動",
            "8時50分の日銀資料後の円・銀行・不動産",
            "SOX高と円高のどちらを日本株が重く見るか",
        ],
    }
    report["executive_summary"] = {
        "headline": headline,
        "market_mood": "金曜は日米株が上昇したが、週末材料は現物市場に未反映。寄り付き前は方向を決め打ちしない。",
        "main_driver": "原油の初動、ドル円157円台、SOX高、8時50分の日銀資料",
        "winners": ["金曜の銀行", "金曜の電機・精密", "SOX高の恩恵を受ける半導体関連候補"],
        "losers": ["円高に弱い輸出株候補", "米金利上昇に弱い高PER株", "原油が反発する場合の運輸"],
        "important_today": ["原油", "日銀会合議事要旨", "企業向けサービス価格指数"],
        "watch_markets": ["WTI・Brent", "USD/JPY", "SOX", "銀行・不動産"],
        "current_environment": ["日経平均+1.30%", "TOPIX参考+1.29%", "SOX+1.41%", "ドル円157.243円", "米10年5.184%"],
    }
    report["main_story"] = {
        "title": "金曜の株高を、週末の原油リスクと日銀資料が試す",
        "fact": "金曜は日米株が上昇し原油は下落。その後、米国のイラン案拒否が伝わった。日銀は本日8時50分に7月会合議事要旨と8月企業向けサービス価格指数を公表予定。",
        "market_reaction": "週末材料に対する日本株現物と新しい原油日足の反応は、7時25分時点で未確認。",
        "importance_reason": "原油は運輸と資源、日銀資料は円・銀行・不動産の相対方向を変え得る。",
        "confidence": "高",
    }
    report["news"][1].update(
        title="米国がイラン案を拒否、原油安の追い風は再確認が必要",
        fact="トランプ米大統領はイランの7日間案を拒否したと表明。イランは外交解決を主張し、正式回答は仲介国経由で待つとしている。",
        published_at="2026-09-27",
        market_reaction="WTI -2.33%、Brent -2.14%は9月25日終値で、拒否表明後の新しい日足反応ではない。",
        analysis="原油反発なら運輸への追い風を撤回し、エネルギー資源を上方修正する。",
        source_url=REUTERS_IRAN,
    )
    report["news"][3].update(
        title="ドル円157円台と米長期金利上昇が株高の中の逆風",
        fact="USD/JPYは157.243円。週末の日次差は+0.04%だが、金曜中に158円台から157円台へ円高が進んだ。米10年債利回りは5.184%。",
        market_reaction="ドル指数は9月25日に-0.32%、米10年金利は上昇。",
        analysis="輸出株は円高、高PER株は金利高の影響を寄り付き後のTOPIX比で確認する。",
        published_at="2026-09-27 FX reference",
    )
    report["events"] = [
        {"event": "日銀会合議事要旨（7月30・31日会合）／企業向けサービス価格指数（8月）", "jst_time": "2026-09-28 08:50 JST", "consensus": "確認できず", "previous": "確認できず", "focus": "追加利上げの議論、サービス価格の粘着性", "affected_markets": ["円", "銀行", "不動産", "高PER株"], "importance": "★★★★★"},
        {"event": "米個人所得・支出（8月）", "jst_time": "2026-09-30 21:30 JST", "consensus": "確認できず", "previous": "確認できず", "focus": "PCE物価と消費", "affected_markets": ["米金利", "ドル", "日本株"], "importance": "★★★★★"},
        {"event": "日銀短観（9月）・9月会合の主な意見", "jst_time": "2026-10-01 08:50 JST", "consensus": "確認できず", "previous": "確認できず", "focus": "企業景況感、設備投資、物価見通し", "affected_markets": ["日本株", "円", "銀行"], "importance": "★★★★★"},
        {"event": "米雇用統計（9月）", "jst_time": "2026-10-02 21:30 JST", "consensus": "確認できず", "previous": "確認できず", "focus": "雇用者数、失業率、賃金", "affected_markets": ["米金利", "ドル", "世界株"], "importance": "★★★★★"},
    ]
    report["market_data"] = [market_row(m, key) for key in m]
    report["market_overview"] = [
        {"market": "日本株（9月25日終値）", "move": "日経平均 +1.30% / TOPIX参考 +1.29%", "relative_strength": "強い", "background": "主要指数がそろって上昇", "impact_on_japan": "金曜の地合いは支えだが、本日の方向は寄り付き後に再確認"},
        {"market": "米半導体・工業", "move": "SOX +1.41% / 米工業ETF +0.95%", "relative_strength": "強い", "background": "大型株中心のリスク選好", "impact_on_japan": "電機・精密、機械に追い風候補"},
        {"market": "為替・金利", "move": "USD/JPY 157.243円 / 米10年 5.184%", "relative_strength": "輸出・高PER株には重い", "background": "円高水準と長期金利上昇", "impact_on_japan": "自動車・高PER株の上値を抑えやすい"},
        {"market": "原油", "move": "WTI -2.33% / Brent -2.14%（9月25日）", "relative_strength": "金曜は下落", "background": "週末のイラン案拒否は未反映", "impact_on_japan": "原油初動まで運輸・資源の結論を保留"},
    ]
    report["changes_from_previous"] = [
        "週末の為替は157.243円で大きな追加変化なし",
        "イランは外交解決を主張したが、米国の拒否表明後の原油反応は未確認",
        "本日8時50分の日銀資料が、円・銀行・不動産の新しい国内材料",
        "Brentの同日再取得不整合を検出し、検証済み9月25日スナップショットを維持",
    ]
    report["japan_market_links"] = [
        {"pair": "SOX高 → 国内半導体", "fact": "SOX +1.41%", "usual_relation": "米半導体株の投資家心理が国内関連株へ波及しやすい", "consistency": "金曜の電機・精密ETFは+1.57%", "interpretation": "電機・精密に追い風候補", "confidence": "高"},
        {"pair": "ドル円157円台 → 輸出採算", "fact": "USD/JPY 157.243円", "usual_relation": "円高は海外売上の円換算と輸出採算を押し下げやすい", "consistency": "本日の日本株反応は未確認", "interpretation": "自動車・機械の上値を抑えやすい", "confidence": "高"},
        {"pair": "イラン情勢 → 原油 → 日本株", "fact": "米国は7日間案を拒否、イランは外交解決を主張", "usual_relation": "原油高は資源株に追い風、運輸に向かい風", "consistency": "拒否表明後の原油反応は未確認", "interpretation": "原油初動まで方向を保留", "confidence": "高"},
        {"pair": "日銀資料 → 円・国内金利", "fact": "8時50分に議事要旨とサービス価格を公表予定", "usual_relation": "追加利上げ観測の変化が円・銀行・不動産に波及しやすい", "consistency": "公表前", "interpretation": "内容と価格反応を確認後に判断", "confidence": "高"},
    ]
    report["commodities_crypto"] = {
        "commodities": {
            "gold": {"price": str(m["gold"]["price"]), "change": "+0.54%", "analysis": "小幅高。日本株の固定主要材料にはしない。"},
            "oil": {"price": "WTI 92.41 / Brent 104.32", "change": "WTI -2.33% / Brent -2.14%", "analysis": "9月25日終値。週末のイラン案拒否は未反映。"},
            "other": "Copper 6.6955（-0.34%）。日本株の主要材料には選ばない。",
        },
        "crypto": {"btc": f"{m['btc']['price']:.2f}（+0.23%）", "eth": f"{m['eth']['price']:.2f}（-0.33%）", "xrp": "確認できず", "basis_time": "2026-09-27日足", "assessment": "小動きで、日本株への波及は限定的。"},
    }
    report["monitoring_points"] = [
        {"target": "イラン情勢と原油", "current_view": "方向保留", "today_check": "拒否表明後のWTI・Brent初動", "view_change_condition": "原油急反発なら運輸追い風を撤回し、資源を上方修正"},
        {"target": "日銀資料", "current_view": "公表前", "today_check": "8時50分後の円・銀行・不動産", "view_change_condition": "利上げ前倒しを意識させる内容と円高がそろえば銀行優位を強める"},
        {"target": "SOXと電機・精密", "current_view": "追い風候補", "today_check": "電機・精密ETFのTOPIX比", "view_change_condition": "TOPIXを下回れば海外半導体高の波及を弱く見る"},
    ]
    report["final_conclusion"] = {
        "headline": headline,
        "winners": ["半導体・電機候補", "日銀資料が金利上昇を示す場合の銀行", "原油安が続く場合の運輸"],
        "losers": ["円高に弱い輸出株候補", "高PER株", "原油反発時の運輸"],
        "top_three": ["原油の初動", "8時50分の日銀資料", "電機・精密のTOPIX比"],
        "triggers": ["原油急反発", "ドル円156円台", "電機・精密のTOPIX比低下", "日銀資料後の円高・金利上昇"],
        "disclaimer": "寄り付き前のため、本日の日本株現物反応は未確認です。確認できない値は補完しません。",
    }
    report["japan_equities_preview"] = {
        "summary": headline,
        "top_materials": top_materials,
        "focus_sectors": ["電機・精密", "銀行", "運輸・物流", "エネルギー資源", "自動車・輸送機"],
        "top_stories": [],
        "total_story_count": 6,
    }
    report["data_quality"] = {
        "overall": "正常（注意事項あり）",
        "missing": ["OSE日経平均先物の限月付き正式値", "週末のイラン情勢を反映した原油・日本株の価格反応", "8時50分公表資料の内容"],
        "differences": ["米2年債は9月24日、米10年債は9月25日。長短金利差は算出しない", "TOPIXは指数そのものではなく1306 ETF参考値", "USD/JPY・暗号資産は9月27日、日本株・米株は9月25日"],
        "excluded": ["同一市場日の再取得で不整合となったBrent 97.44ドル", "34監視銘柄による日本市場全体の広がり判定", "各業種2銘柄によるセクター全体評価", "Copper・Goldの固定主要材料化"],
        "cautions": ["寄り付き前のため本日の日本株反応は未確認", "商品値は連続先物の参考日足", "週末ニュースは金曜終値に未反映"],
    }
    report["source_notes"] = [WHITE_HOUSE, REUTERS_IRAN, BOJ_SCHEDULE, BEA_SCHEDULE, BLS_SCHEDULE, "data/market.json", "data/japan-market.json"]

    japan.update(report_date=REPORT_DATE, target_market_date=TARGET_DATE, updated_at=UPDATED)
    japan["japan_quick_view"] = {
        "headline": headline,
        "top_materials": top_materials,
        "focus_sectors": ["電機・精密", "銀行", "運輸・物流", "エネルギー資源", "自動車・輸送機"],
        "unpriced_materials": ["米国のイラン案拒否後の原油反応", "8時50分の日銀資料", "本日の日本株現物"],
    }
    japan["top_stories"] = [
        story("運輸・資源", "原油初動で強弱が入れ替わる可能性", "原油・外交", "米国がイランの7日間案を拒否し、イランは外交解決を主張。金曜の原油終値には未反映。", "週末材料は未反映", ["運輸・物流", "エネルギー資源", "素材・化学"], "★★★★★", REUTERS_IRAN, "原油反発なら運輸の追い風を撤回し、資源を上方修正する。", "WTI・Brentの初動と業種ETF"),
        story("半導体・電機", "SOX+1.41%は追い風候補", "海外市場", "米半導体株は金曜に上昇。日本の電機・精密ETFも金曜+1.57%。", "金曜分は一部織り込み済み", ["電機・精密", "機械"], "★★★★★", "https://finance.yahoo.com/quote/%5ESOX/history/", "追加の追随余地は本日のTOPIX比で確認する。", "電機・精密ETFのTOPIX比"),
        story("銀行・不動産", "8時50分の日銀資料が国内の新材料", "金融政策", "日銀は7月会合議事要旨と8月企業向けサービス価格指数を8時50分に公表予定。", "公表前", ["銀行", "不動産", "情報通信・サービス"], "★★★★★", BOJ_SCHEDULE, "追加利上げ観測が強まる場合、銀行に追い風、不動産・高PER株に向かい風になりやすい。", "公表内容と円・国内金利・業種ETFの反応"),
        story("輸出株", "ドル円157円台は輸出株の重し", "為替", "USD/JPYは157.243円。週末の追加変化は小さいが、金曜中に158円台から円高が進んだ。", "本日の現物には未反映", ["自動車・輸送機", "機械"], "★★★★☆", "https://finance.yahoo.com/quote/JPY=X/history/", "米株高だけでなく為替の逆風を同時に見る。", "ドル円と外需型ETFのTOPIX比"),
    ]
    japan["important_stories"] = [
        story("中国関連株", "米中会談は限定前進、レアアースは未解決", "米中政策", "双方300億ドル分の非センシティブ品への有利な関税待遇、農業作業部会、石炭輸入目標を発表。レアアース供給不足は協議継続。", "金曜分は一部織り込み済み", ["機械", "鉄鋼・非鉄", "商社・卸売"], "★★★★☆", WHITE_HOUSE, "具体策と未解決点を分け、機械・素材を一括で強気にしない。", "中国市場と重要鉱物の続報"),
        story("金曜の業種ETF", "銀行+3.49%、電機・精密+1.57%、運輸+1.52%", "セクター", "TOPIX-17業種ETF自身の9月25日騰落。金融（銀行除く）は-0.72%、電力・ガスは-0.36%。", "金曜終値で確認済み", ["銀行", "電機・精密", "運輸・物流", "金融（銀行除く）"], "★★★★☆", "https://finance.yahoo.co.jp/quote/1631.T/history", "主要2銘柄ではなく業種ETF自身の価格・出来高・5日推移を使用。", "本日のTOPIX比と出来高"),
    ]
    japan["sector_implications"] = [
        {"driver": "SOX高", "affected_sectors": ["電機・精密"], "possible_impact": "追い風候補", "confirmation_condition": "電機・精密ETFがTOPIXを上回る"},
        {"driver": "ドル円157円台", "affected_sectors": ["自動車・輸送機", "機械"], "possible_impact": "上値を抑えやすい", "confirmation_condition": "円高継続と外需ETFのTOPIX比低下"},
        {"driver": "イラン情勢と原油", "affected_sectors": ["運輸・物流", "エネルギー資源"], "possible_impact": "初動次第で逆方向", "confirmation_condition": "原油と両業種ETFの同時確認"},
        {"driver": "日銀資料", "affected_sectors": ["銀行", "不動産"], "possible_impact": "内容次第", "confirmation_condition": "円・国内金利・業種ETFの反応"},
    ]
    japan["data_quality"] = {
        "overall": "正常（注意事項あり）",
        "missing": ["寄り付き後の日本株反応", "OSE先物の限月付き正式値", "TDnet全件の完全網羅"],
        "differences": ["日本株・米株は9月25日終値、USD/JPY・暗号資産は9月27日付", "TOPIXは1306 ETF参考値"],
        "unpriced": ["米国のイラン案拒否", "8時50分の日銀資料", "本日の日本株現物"],
        "cautions": ["Brentの同日再取得不整合は除外し検証済み値を維持", "34監視銘柄から日本市場全体を評価しない", "セクター全体を主要2銘柄で評価しない"],
    }
    japan["source_notes"] = report["source_notes"]

    # The market is still pre-open, so reuse the verified 9/25 cash-session
    # rows and refresh only the report-driven context. This avoids a second
    # Yahoo fetch and prevents the previous session from being scored as if it
    # were the result of today's scenario.
    japan_market["updated_at"] = UPDATED
    enrich_investor_view(japan_market, market, japan)
    japan_market["key_drivers"] = [
        item for item in japan_market.get("key_drivers", [])
        if item.get("driver") != "日銀資料"
    ][:4] + [{
        "driver": "日銀資料",
        "category": "金融政策・物価",
        "assessment": "公表前・方向保留",
        "status": "scheduled",
        "market_value": None,
        "change_pct": None,
        "transmission_path": "追加利上げ観測 → 円・国内金利 → 銀行・不動産・高PER株",
        "reason": "8時50分に7月会合議事要旨と8月企業向けサービス価格指数を公表予定。内容と価格反応が出る前は方向を決めません",
        "affected_sectors": ["銀行", "不動産", "情報通信・サービス"],
        "market_date": REPORT_DATE,
        "selection_factors": {
            "日本株現物への織り込み": "公表前",
            "日本株への波及範囲": 3,
            "影響業種数": 3,
            "ニュース重要度": 3,
            "値動き": 0,
        },
        "pricing_status": "日本株現物に未反映",
        "change_condition": "公表後の円・国内金利・銀行・不動産の反応がそろえば見方を修正する",
    }]
    japan_market["morning_summary"]["tailwinds"] = [
        "米国半導体株：電機・精密に追い風候補",
        "金曜の原油安：運輸に追い風候補（週末材料後の初動待ち）",
    ]
    japan_market["morning_summary"]["headwinds"] = [
        "ドル円157円台：輸出株の上値を抑えやすい",
        "米10年金利5.184%：高PER株に向かい風",
    ]

    output = ROOT / f"candidate-{REPORT_DATE}"
    output.mkdir(exist_ok=True)
    dump(output / "report.json", report)
    dump(output / "japan-stocks.json", japan)
    dump(output / "japan-market.json", japan_market)
    dump(output / "market.json", market)
    print(output)


if __name__ == "__main__":
    main()
