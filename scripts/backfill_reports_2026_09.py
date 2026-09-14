#!/usr/bin/env python3
"""Reconstruct missing September 2026 reports from archived market snapshots.

The generated files are historical reconstructions. They intentionally omit
unverified company-level disclosures instead of guessing them.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history"


CONFIG = {
    "2026-09-04": {
        "target": "2026-09-03",
        "type": "daily",
        "headline": "米金利低下と大型テック高で米国株が反発。日本株は円高と原油高への耐性を確認する局面。",
        "driver": "FRB高官発言後の米国債利回り低下とソフトウェア・大型テック株の上昇",
        "facts": [
            "9月3日の米国株はS&P500が1.06%、NASDAQ総合が1.40%、NYダウが1.18%上昇した。",
            "米10年債利回りは4.762%。WTIは91.75ドルと高水準を維持した。",
            "USD/JPYは155.852円。前日比では円高方向だった。",
        ],
        "materials": ["米国株の全面反発", "米長期金利の低下", "円高方向のUSD/JPY", "90ドル台のWTI", "Copperの上昇"],
        "sectors": ["半導体・電気機器", "情報・通信", "自動車", "資源", "航空・運輸"],
        "sources": [
            "https://www.marketwatch.com/livecoverage/stock-market-today-dow-s-p-500-nasdaq-oil-prices-bond-yields-ease-ism-services-pmi",
            "https://finance.yahoo.com/markets/stocks/articles/stock-market-today-sept-3-134812608.html",
        ],
    },
    "2026-09-06": {
        "target": "2026-09-04",
        "type": "weekly",
        "headline": "原油・金利上昇で始まった週は米株が乱高下。強い米雇用統計で利上げ警戒が再燃した。",
        "driver": "中東情勢による原油高と、強い米雇用統計を受けた金融引き締め観測",
        "facts": [
            "週前半は原油と国債利回りの上昇が株式を圧迫し、9月3日は金利低下で米株が反発した。",
            "9月4日は米雇用者数が16.2万人増と報じられ、米主要株価指数は反落した。",
            "9月4日時点で米10年債利回りは4.784%、WTIは91.48ドルだった。",
        ],
        "materials": ["中東情勢と原油高", "強い米雇用統計", "米金利の高止まり", "週後半の米株反落", "円相場の変動"],
        "sectors": ["資源", "金融", "半導体", "自動車", "運輸"],
        "sources": [
            "https://www.investopedia.com/markets-news-september-4-2026-stocks-close-lower-hot-jobs-report-11816963",
            "https://www.edwardjones.com/us-en/market-news-insights/stock-market-news/daily-market-recap",
            "https://www.reuters.com/business/wall-st-futures-kick-off-september-under-pressure-yields-oil-prices-rise-2026-09-01/",
        ],
    },
    "2026-09-07": {
        "target": "2026-09-04",
        "type": "daily",
        "headline": "強い米雇用統計でFedの利上げ警戒が再燃。日本株は円安支援と金利上昇圧力の綱引き。",
        "driver": "米雇用統計を受けた政策金利見通しの上方修正",
        "facts": [
            "9月4日のS&P500は0.38%、NASDAQ総合は0.29%、NYダウは0.51%下落した。",
            "米10年債利回りは4.784%、USD/JPYは156.244円だった。",
            "日本株の直近市場日9月4日は日経225が1.26%上昇した。",
        ],
        "materials": ["米雇用統計の上振れ", "Fed利上げ警戒", "米株の反落", "156円台のUSD/JPY", "日本株の直近上昇"],
        "sectors": ["銀行・保険", "自動車", "半導体", "不動産", "資源"],
        "sources": [
            "https://www.investopedia.com/markets-news-september-4-2026-stocks-close-lower-hot-jobs-report-11816963",
            "https://www.edwardjones.com/us-en/market-news-insights/stock-market-news/daily-market-recap",
        ],
    },
    "2026-09-08": {
        "target": "2026-09-07",
        "type": "daily",
        "headline": "米国休場で海外の価格発見は限定的。円高進行と日本株の高値圏で選別色が強まりやすい。",
        "driver": "米レーバーデー休場とUSD/JPYの154円台への円高",
        "facts": [
            "米国株の最新終値は9月4日で、9月7日はレーバーデーのため休場だった。",
            "USD/JPYは154.279円となり、前回取得値から円高方向へ動いた。",
            "日本株の最新取得日は9月4日で、日経225は1.26%上昇していた。",
        ],
        "materials": ["米国市場休場", "154円台への円高", "日本株の高値警戒", "90ドル台のWTI", "Copper高"],
        "sectors": ["自動車", "機械", "内需", "資源", "半導体"],
        "sources": [
            "https://www.investopedia.com/markets-news-september-4-2026-stocks-close-lower-hot-jobs-report-11816963",
        ],
    },
    "2026-09-10": {
        "target": "2026-09-09",
        "type": "daily",
        "headline": "原油100ドル突破と米金利上昇で世界株が続落。日本株は資源高とコスト増の二極化。",
        "driver": "中東の供給不安による原油100ドル突破とインフレ懸念",
        "facts": [
            "9月9日のS&P500は0.48%、NASDAQ総合は0.64%、NYダウは0.77%下落した。",
            "Brentは101.21ドル、WTIは96ドル台まで上昇したと報じられた。",
            "米10年債利回りは4.837%、USD/JPYは153.428円だった。",
        ],
        "materials": ["原油100ドル突破", "米長期金利上昇", "米主要指数の続落", "153円台のUSD/JPY", "インフレ再加速懸念"],
        "sectors": ["石油・鉱業", "商社", "航空・運輸", "自動車", "グロース"],
        "sources": [
            "https://www.marketscreener.com/news/wall-street-dips-as-100-oil-inflation-worries-weigh-on-investors-ce785bd9d080ff27",
            "https://www.lse.co.uk/news/global-markets-wall-street-dips-as-100-oil-inflation-worries-weigh-on-investors-85xjj6q08zklmto.html",
        ],
    },
    "2026-09-11": {
        "target": "2026-09-10",
        "type": "daily",
        "headline": "原油急騰と米金利4.9%台で株式の評価圧力が強まる。日本株は資源株以外に逆風。",
        "driver": "Brentの6%上昇、米生産者物価、Fed利上げ観測の強まり",
        "facts": [
            "9月10日のS&P500は0.58%、NASDAQ総合は0.65%、NYダウは0.60%下落した。",
            "WTIは103.96ドルへ8.24%上昇し、米10年債利回りは4.944%だった。",
            "NVIDIAは2.3%、Micronは4.7%下落したとReutersが報じた。",
        ],
        "materials": ["原油の急騰", "米10年金利4.9%台", "米PPIとインフレ懸念", "半導体株安", "Fed利上げ観測"],
        "sectors": ["石油・鉱業", "銀行", "半導体", "航空・運輸", "不動産"],
        "sources": [
            "https://wealthinsights.metrobank.com.ph/news/us-stocks-sandp-500-ends-down-as-treasury-yields-rise-and-traders-fret-about-inflation",
            "https://www.investing.com/news/economy-news/trading-day-inflation-palpitations-4896968",
        ],
    },
    "2026-09-13": {
        "target": "2026-09-11",
        "type": "weekly",
        "headline": "原油100ドル超と金利上昇が週を支配。金曜は反発したが、インフレと中東リスクは残存。",
        "driver": "中東の供給障害、米物価指標、Fed利上げ観測",
        "facts": [
            "週中にBrentが100ドルを超え、米10年債利回りは4.9%台へ上昇した。",
            "9月11日はS&P500が0.86%、NASDAQ総合が0.96%、NYダウが0.98%反発した。",
            "8月米CPIは前月比0.4%と報じられ、Fed利上げ観測を支えた。",
        ],
        "materials": ["中東の供給障害", "原油100ドル超", "米CPI", "Fed利上げ観測", "金曜の米株反発"],
        "sectors": ["資源", "金融", "半導体", "運輸", "内需"],
        "sources": [
            "https://www.kitco.com/news/off-the-wire/2026-09-11/wall-street-jumps-oil-lower-ahead-fed-vote-next-week",
            "https://www.lse.co.uk/news/global-markets-bonds-stocks-selloff-pauses-as-oil-retreats-from-multi-month-high-d6ks9tlw6ltbggb.html",
        ],
    },
    "2026-09-14": {
        "target": "2026-09-11",
        "type": "daily",
        "headline": "米株反発後も週末のサウジ供給不安で原油が再上昇。日本株は資源高・円高・金利高を警戒。",
        "driver": "サウジ東西パイプライン停止と主要中銀の利上げ観測",
        "facts": [
            "9月11日の米国株は主要3指数が0.9%前後上昇した。",
            "週末の攻撃でサウジの東西パイプラインが停止し、供給不安が再燃した。",
            "9月14日朝の取得値はWTI 103.26ドル、米10年債利回り4.975%、USD/JPY 153.608円だった。",
        ],
        "materials": ["サウジ供給不安", "原油再上昇", "米金利4.9%台", "153円台のUSD/JPY", "Fed・日銀会合"],
        "sectors": ["石油・鉱業", "商社", "航空・運輸", "自動車", "半導体"],
        "sources": [
            "https://www.reuters.com/business/energy/saudi-pipeline-outage-threatens-loss-4-global-oil-supply-2026-09-13/",
            "https://www.reuters.com/world/china/global-markets-global-markets-2026-09-13/",
            "https://www.kitco.com/news/off-the-wire/2026-09-11/wall-street-jumps-oil-lower-ahead-fed-vote-next-week",
        ],
    },
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def market_rows(market: dict) -> list[dict]:
    keys = ("sp500", "nasdaq", "nasdaq100", "dow", "russell2000", "nikkei225", "topix", "dxy", "usdjpy", "us2y", "us10y", "gold", "silver", "copper", "wti", "brent", "btc", "eth")
    rows = []
    for key in keys:
        item = market.get("markets", {}).get(key)
        if not item:
            continue
        rows.append({
            "market": item.get("name", key),
            "price": str(item.get("price", "確認できず")),
            "change": f"{item.get('change_pct')}%" if item.get("change_pct") is not None else "確認できず",
            "basis_time": item.get("market_date", "確認できず"),
            "source": market.get("source", "確認できず"),
            "confidence": "B",
            "status": item.get("status", "確認できず"),
        })
    return rows


def make_bundle(report_date: str, cfg: dict, market: dict) -> tuple[dict, dict]:
    top_news = [{"title": text} for text in cfg["facts"]]
    scenarios = [
        {"name": "基本シナリオ", "conditions": "原油・金利・為替が直近レンジ内", "impact_on_japan": "指数より業種間格差を重視", "strong_sectors": cfg["sectors"][:2], "weak_sectors": cfg["sectors"][-2:], "invalidation": "原油、米金利、USD/JPYのうち二つ以上が明確に反転"},
        {"name": "改善シナリオ", "conditions": "原油と米金利が低下し、株式の騰落が改善", "impact_on_japan": "輸出・グロースを含む反発余地", "strong_sectors": cfg["sectors"][1:3], "weak_sectors": [], "invalidation": "供給不安またはインフレ懸念が再燃"},
        {"name": "悪化シナリオ", "conditions": "原油と米金利が同時上昇", "impact_on_japan": "資源以外のコスト・評価面に逆風", "strong_sectors": cfg["sectors"][:1], "weak_sectors": cfg["sectors"][2:], "invalidation": "政策対応や緊張緩和で原油が反落"},
    ]
    report = {
        "report_date": report_date,
        "target_market_date": cfg["target"],
        "updated_at": f"{report_date} historical reconstruction",
        "report_type": cfg["type"],
        "week_period": None,
        "quick_view": {"headline": cfg["headline"], "top_news": top_news, "important_today": cfg["materials"][:3]},
        "executive_summary": {"headline": cfg["headline"], "market_mood": "確認済みの市場データに基づく過去日再構成", "main_driver": cfg["driver"], "winners": cfg["sectors"][:2], "losers": cfg["sectors"][-2:], "important_today": cfg["materials"][:3], "watch_markets": ["USD/JPY", "米10年債", "WTI・Brent"], "current_environment": ["過去日再構成"]},
        "news": [{"title": f"確認材料{i+1}", "fact": fact, "published_at": cfg["target"], "market_reaction": "履歴市場データに反映", "analysis": cfg["driver"], "related_assets": [], "related_japan_sectors": cfg["sectors"], "importance": "★★★★☆", "source_url": cfg["sources"][min(i, len(cfg["sources"])-1)]} for i, fact in enumerate(cfg["facts"])],
        "scenarios": scenarios,
        "market_data": market_rows(market),
        "market_overview": [{"market": "クロスアセット", "move": cfg["facts"][0], "relative_strength": "履歴値参照", "background": cfg["driver"], "impact_on_japan": cfg["headline"]}],
        "japan_equities_preview": {"summary": "過去日再構成。個別企業の適時開示は未復元。", "top_materials": cfg["materials"], "focus_sectors": cfg["sectors"], "top_stories": [], "total_story_count": 0},
        "monitoring_points": [{"target": item, "current_view": "過去日時点の重要材料", "today_check": "当時の市場反応を確認", "view_change_condition": "関連する価格・政策材料が反転"} for item in cfg["materials"][:3]],
        "data_quality": {"overall": "C", "missing": ["当日朝時点の個別企業適時開示", "一部の公式終値・在庫データ"], "differences": ["再作成時点で取得できた記事と履歴市場データを使用"], "excluded": ["確認不能な個別株材料"], "cautions": ["過去日再構成版", "後知恵を避けるため対象日後の材料は原則不使用", "数値は保存済みmarket.jsonを優先"]},
        "final_conclusion": {"headline": cfg["headline"], "winners": cfg["sectors"][:2], "losers": cfg["sectors"][-2:], "top_three": cfg["materials"][:3], "triggers": ["原油の方向", "米金利の方向", "USD/JPYの方向"], "disclaimer": "本レポートは市場情報の整理を目的とし、特定の金融商品の売買を推奨するものではありません。"},
        "source_notes": cfg["sources"] + ["保存済み data/history/{}/market.json".format(report_date)],
    }
    japan = {
        "report_date": report_date,
        "target_market_date": cfg["target"],
        "updated_at": f"{report_date} historical reconstruction",
        "report_type": "japan_stocks",
        "japan_quick_view": {"headline": cfg["headline"], "top_materials": cfg["materials"], "focus_sectors": cfg["sectors"], "unpriced_materials": ["個別企業適時開示は未復元"]},
        "top_stories": [],
        "important_stories": [],
        "other_stories": [],
        "sector_implications": [{"driver": cfg["driver"], "affected_sectors": cfg["sectors"], "possible_impact": cfg["headline"], "confirmation_condition": "当時の為替・金利・商品と株価反応を照合"}],
        "data_quality": {"overall": "C", "missing": ["当日朝時点の個別企業適時開示"], "differences": [], "unpriced": [], "cautions": ["過去日再構成版", "証券コードを推測していない"]},
        "source_notes": cfg["sources"],
    }
    return report, japan


def refresh_index() -> None:
    # Import the canonical index builder rather than maintaining a second format.
    import sys
    sys.path.insert(0, str(ROOT))
    from archive_daily import refresh_history_index
    refresh_history_index()


def main() -> None:
    for report_date, cfg in CONFIG.items():
        folder = HISTORY / report_date
        market_path = folder / "market.json"
        if not market_path.exists():
            raise FileNotFoundError(market_path)
        report, japan = make_bundle(report_date, cfg, load(market_path))
        dump(folder / "report.json", report)
        dump(folder / "japan-stocks.json", japan)

    # The 9 September report already existed; only its history copy was missing.
    nine = HISTORY / "2026-09-09"
    shutil.copy2(ROOT / "data" / "report.json", nine / "report.json")
    shutil.copy2(ROOT / "data" / "japan-stocks.json", nine / "japan-stocks.json")
    refresh_index()


if __name__ == "__main__":
    main()
