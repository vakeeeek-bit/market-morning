#!/usr/bin/env python3
"""Add the audited CXMT finding and theme history to the Oct. 14 report.

This patch deliberately preserves the current canonical market snapshot and its
target date.  Reuters observations are used as external reaction evidence, not
as replacements for canonical prices.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NOW = datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
CXMT_OFFICIAL = "https://www.cxmt.com/news.html"
REUTERS_CXMT = "https://www.reuters.com/world/china/us-chip-stocks-extend-slide-china-memory-report-ai-spending-jitters-hit-sector-2026-10-13/"
REUTERS_US = "https://www.reuters.com/business/sp-500-futures-muted-investors-await-big-bank-earnings-chip-weakness-weighs-2026-10-13/"
REUTERS_ASIA = "https://www.reuters.com/world/china/global-markets-global-markets-2026-10-14/"


def load(name: str) -> dict:
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def save(name: str, value: dict) -> None:
    (DATA / f"{name}.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def verification() -> dict:
    return {
        "source_read": {"status": "PASS", "evidence": "CXMT公式企業ニュースとReuters報道を実読"},
        "facts_verified": {"status": "PASS", "evidence": "会社発表と市場報道の役割を分離"},
        "chronology": {"status": "PASS", "evidence": "9月20日発表、10月9〜10日発言、12〜14日反応を分離"},
        "fact_analysis_separation": {"status": "PASS", "evidence": "技術発表、計画、株価反応、解釈を分離"},
        "limitations": {"status": "PASS", "evidence": "量産歩留まり・顧客認定・単独因果を断定しない"},
    }


report = load("report")
news = load("news")
display = load("news-display")
evidence = load("research-evidence")

if report.get("report_date") != "2026-10-14":
    raise ValueError("This patch is restricted to the 2026-10-14 report")

report["updated_at"] = NOW
report["quick_view"]["headline"] = "注釈付き暫定版｜CPI前の半導体警戒に、中国メモリー競争を追加して選別"
report["quick_view"]["top_news"] = [
    {"title": "今夜21:30 JSTの米CPIは未発表、結果を先取りしない"},
    {"title": "CXMTの4F²計画は重要な競争材料。ただし商用量産・顧客認定は未確認"},
    {"title": "半導体安は中国要因だけでなく、AI投資採算・金利・利益確定との複合"},
]
important = report["quick_view"].setdefault("important_today", [])
cxmt_watch = "CXMT計画と米韓日のメモリー・装置株反応を分けて確認"
if cxmt_watch not in important:
    important.insert(1, cxmt_watch)

report["executive_summary"].update({
    "headline": report["quick_view"]["headline"],
    "main_driver": "米CPI待ち、半導体のAI投資採算と中国競争、国内個別開示",
})
environment_note = "CXMT競争は重要な追加要因。ただし正本市場値を置換せず、単独主因と断定しない"
current_environment = report["executive_summary"].setdefault("current_environment", [])
if environment_note not in current_environment:
    current_environment.append(environment_note)

cxmt_story = {
    "title": "CXMT計画と半導体安：中国競争は追加要因、単独主因ではない",
    "fact": "CXMTは9月20日に第5世代DRAM技術基盤の量産開始を公表。10月9〜10日の会議では4F² DDR5 RDIMMの年内投入計画が示されたと報じられたが、仕様・歩留まり・顧客認定・大規模量産は未確認。",
    "source_url": REUTERS_CXMT,
    "published_at": "2026-10-13",
    "market_reaction": "Reutersによる外部照合では13日にSamsung・SK Hynix、Micron、キオクシア、東京エレクトロンが下落。一方、米SOXの下げは限定的で、14日午前は韓国半導体が反発。",
    "analysis": "中国競争を重要な追加要因へ引き上げる。ただしAI投資採算、金利・資本コスト、利益確定も同時に作用しており、寄与率や単独因果は断定しない。",
    "related_assets": ["CXMT", "Micron", "Samsung", "SK Hynix", "キオクシア", "東京エレクトロン", "SOX"],
    "related_japan_sectors": ["電機・精密", "機械"],
    "importance": "高",
}
replaced = False
for index, item in enumerate(report.get("news", [])):
    if item.get("title") in {
        "10月13日の海外半導体安は正本未反映",
        cxmt_story["title"],
    }:
        report["news"][index] = cxmt_story
        replaced = True
        break
if not replaced:
    report.setdefault("news", []).insert(0, cxmt_story)

report["what_changed"] = {
    "previous_view": "半導体安をAI投資回収・金利・需給中心に警戒していた。",
    "new_information": "CXMTの技術基盤発表、4F²製品計画報道、米韓日のメモリー・装置株反応を追加確認した。",
    "revision": "中国競争を重要な追加要因へ引き上げたが、商用量産と寄与率が未確認のため単独主因とはしない。",
}
report["monitoring_points"] = [
    {"target": "キオクシア・東京エレクトロン", "reason": "中国競争懸念の日本株伝達", "view_change_condition": "下落分の回復とTOPIX比の改善が複数日続く"},
    {"target": "Samsung・SK Hynix・Micron", "reason": "メモリー競争の国際比較", "view_change_condition": "複数市場で反発が続けば即時業績影響を引き下げる"},
    {"target": "米金利・ドル", "reason": "CPI後の資本コスト", "view_change_condition": "金利・ドルが同時上昇すれば高PER株の逆風を強める"},
    {"target": "CXMT製品情報", "reason": "計画と商用量産の差", "view_change_condition": "仕様・歩留まり・顧客認定・出荷量が確認されれば競争評価を更新する"},
]

report["market_context_themes"] = [
    {
        "theme": "半導体・中国競争",
        "initial_view": {"date": "2026-10-09", "text": "AI需要と米半導体動向を中心に、日本の半導体を選別していた。"},
        "new_fact": {"date": "2026-10-12", "text": "CXMTの4F² DDR5 RDIMM年内投入計画が報じられた。商用量産・顧客認定は未確認。"},
        "market_reaction": {"date": "2026-10-13", "text": "米韓日のメモリー・装置株が下落。ただし米SOXの下げは限定的で、14日午前は韓国勢が反発。"},
        "current_view": "中国競争は重要な追加要因。AI投資採算・金利・利益確定との複合で、単独主因とは断定しない。",
        "japan_impact": "キオクシアと製造装置を重点監視。反発の広がりが確認できれば短期逆風を引き下げる。",
        "counter_evidence": "4F²の仕様・歩留まり・顧客認定が未確認で、SOX全体の下げは限定的。",
        "source_ids": ["cxmt-g5-official-20260920", "cxmt-4f2-market-20261013", "reuters-us-market-20261013", "reuters-asia-rebound-20261014"],
    },
    {
        "theme": "米金利・インフレ",
        "initial_view": {"date": "2026-10-08", "text": "FRB高官発言からインフレ警戒とデータ依存を確認していた。"},
        "new_fact": {"date": "2026-10-14", "text": "9月CPIは21:30 JST公表予定で、日次レポート作成時点では未発表。"},
        "market_reaction": {"date": "2026-10-14", "text": "結果への市場反応はまだ発生していない。"},
        "current_view": "CPI後の金利・ドル反応を待つ。発表前に利上げ方向を断定しない。",
        "japan_impact": "銀行、高PERグロース、不動産はCPI後の米金利で再評価する。",
        "counter_evidence": "半導体の選別売りは金利だけでは説明できない。",
        "source_ids": ["waller-sep-20261008", "oct14-0"],
    },
    {
        "theme": "原油・地政学",
        "initial_view": {"date": "2026-10-05", "text": "米国の軽油税支払い延期検討を供給・物価の補助材料として確認した。"},
        "new_fact": {"date": "2026-10-12", "text": "供給懸念で原油高が再び市場の材料になった。"},
        "market_reaction": {"date": "2026-10-12", "text": "エネルギー株が相対優位となり、半導体と主要指数は方向が分かれた。"},
        "current_view": "原油高を株全体の方向ではなく、資源優位と燃料コストの差として読む。",
        "japan_impact": "資源・商社に追い風候補、空運・陸運・化学・小売にコスト警戒。",
        "counter_evidence": "契約定義を確認できない商品価格は方向判断の数値根拠から除外する。",
        "source_ids": ["wh-diesel-tax-20261005", "reuters-us-market-20261012"],
    },
    {
        "theme": "日本株・個別選別",
        "initial_view": {"date": "2026-10-09", "text": "休場前の一次資料を中心に、会社固有材料を継続監視していた。"},
        "new_fact": {"date": "2026-10-13", "text": "カナデンの業績修正、オリンパスのFDA警告、リソー教育のTOBが公表された。"},
        "market_reaction": {"date": "2026-10-14", "text": "日次レポート作成時点で各材料の国内終値反応は未確認。"},
        "current_view": "指数や半導体テーマに一括せず、実需・規制・TOBを会社固有材料として分ける。",
        "japan_impact": "電源設備、医療機器、教育は同じ方向へ束ねず、開示条件と価格反応を個別確認する。",
        "counter_evidence": "カナデンの需要改善はAI関連全体を一律否定する見方への反証。",
        "source_ids": ["oct14-4", "oct14-5", "oct14-6"],
    },
]
report["market_context_sources"] = {
    "cxmt-4f2-market-20261013": {"id": "cxmt-4f2-market-20261013", "title": "CXMTの4F²計画報道でメモリー株に競争警戒", "publisher": "Reuters", "published_date": "2026-10-13", "source_url": REUTERS_CXMT},
    "reuters-us-market-20261013": {"id": "reuters-us-market-20261013", "title": "米株：半導体安を受け主要指数は小幅安", "publisher": "Reuters", "published_date": "2026-10-13", "source_url": REUTERS_US},
    "reuters-asia-rebound-20261014": {"id": "reuters-asia-rebound-20261014", "title": "アジア株：半導体売り一服、米CPIを待つ", "publisher": "Reuters", "published_date": "2026-10-14", "source_url": REUTERS_ASIA},
}

official_article = {
    "id": "cxmt-g5-official-20260920",
    "title": "CXMT：第5世代DRAM技術基盤の量産開始を発表",
    "published_date": "2026-09-20",
    "verified_at": NOW,
    "source_type": "primary",
    "publisher": "CXMT",
    "source_url": CXMT_OFFICIAL,
    "verification_url": CXMT_OFFICIAL,
    "verification_status": "PASS",
    "fact": "CXMTは9月20日、第5世代DRAM技術基盤の量産開始と24Gb LPDDR5X製品を発表した。会社説明では旧世代比でウエハー当たりの総ダイ数が50%以上増える。",
    "analysis": "中国DRAMの供給能力・価格競争を継続監視する起点。会社公表値であり、歩留まり・顧客認定・世界シェアの即時変化は確認できない。",
    "limitations": "4F² DDR5 RDIMMの商用量産・顧客認定を示す発表ではない。",
    "market_reaction_status": "unverified",
    "market_reaction": "未確認",
    "verification": verification(),
}
articles = {item["id"]: item for item in news.get("articles", [])}
articles[official_article["id"]] = official_article
news["updated_at"] = NOW
news["coverage_note"] = "新規確認7件と既存記事にCXMT一次情報を追加。競争要因は単独主因とせず、最新ニュース日と正本市場日を分離。"
news["articles"] = list(articles.values())
display.setdefault("items", {})[official_article["id"]] = {
    "primary_page": "world",
    "priority": 94,
    "attention_points": ["会社公表の量産開始。4F²サーバー製品の商用量産確認ではない。"],
}

coverage_item = {
    "id": "china_competitor_and_supply",
    "label": "中国競合技術・供給能力",
    "tier": "Critical",
    "status": "取得済",
    "evidence": "CXMTの9月20日技術基盤発表、10月9〜10日の4F²計画、12〜14日の市場反応を分離",
    "attempts": [{"method": "一次情報・金融報道・市場反応照合", "result": "計画と商用量産を区別し、米韓日の反応差を確認", "source_urls": [CXMT_OFFICIAL, REUTERS_CXMT, REUTERS_ASIA], "checked_at": NOW}],
    "impact_if_unavailable": "半導体下落要因の重要な競争圧力を見落とす",
    "publication_use": "selected",
}
coverage_items = evidence["research_coverage"].setdefault("items", [])
coverage_items[:] = [item for item in coverage_items if item.get("id") != coverage_item["id"]]
coverage_items.insert(0, coverage_item)
for direction in evidence["research_coverage"].get("directions", []):
    if direction.get("id") in {"cross_news", "reverse_from_anomalies"}:
        addition = "CXMT競争情報と米韓日の同業反応を追加照合"
        if addition not in direction["evidence"]:
            direction["evidence"] += "／" + addition

evidence["updated_at"] = NOW
scope_addition = "CXMTの発表・計画・各国反応を追加検証し、中国要因を単独主因としない。"
if scope_addition not in evidence["scope_note"]:
    evidence["scope_note"] += " " + scope_addition
cxmt_material = {
    "headline": "CXMT競争懸念と半導体株の選別",
    "fact": {"text": cxmt_story["fact"], "source_urls": [CXMT_OFFICIAL, REUTERS_CXMT, REUTERS_US], "verification_status": "PASS"},
    "observed_market_reaction": {"text": cxmt_story["market_reaction"], "assets_checked": cxmt_story["related_assets"]},
    "market_internals": {"text": "メモリー・製造装置の下げが半導体指数全体より大きい"},
    "market_pricing": {"status": "partially_priced", "text": "13日に売られ、14日午前は一部反発"},
    "interpretation": {"text": cxmt_story["analysis"], "confidence": "supported", "evidence": "米韓日の同業株反応", "uncertainty": "量産歩留まり・顧客認定と材料別寄与率は未確認"},
    "japan_transmission": {"economic_channel": "中国DRAMの供給拡大懸念→価格決定力低下懸念→メモリー・装置株の評価低下", "intermediate_reactions": ["Samsung・SK Hynix", "Micron・SOX", "キオクシア・東京エレクトロン"], "affected_sectors": ["電機・精密", "機械"], "pricing_in_japan": "13日の外部照合ではキオクシア・東京エレクトロンが下落", "assessment": "短期逆風。ただし正本未反映と14日反発を明示"},
    "conflict_resolution": "CXMT単独説とAI採算・金利・需給を比較し、指数と個別株の差を重視",
    "counter_evidence": ["米SOXの下げは限定的", "14日午前は韓国半導体が反発", "商用量産能力は未確認"],
    "change_conditions": ["4F²製品の仕様・歩留まり・顧客認定", "同業株の反発継続"],
    "chronology_check": "PASS",
}
materials = evidence["analysis_quality"]["materials"]
materials[:] = [item for item in materials if item.get("headline") != cxmt_material["headline"]]
materials.insert(0, cxmt_material)
evidence["previous_day_change"] = {
    "status": "PASS",
    "prior_view": "AI投資回収・金利・需給を中心に半導体を警戒",
    "new_events": ["CXMTの4F²計画報道", "米韓日のメモリー・装置株下落", "14日午前の韓国半導体反発"],
    "changed": ["中国競争を重要な追加要因へ引き上げ"],
    "unchanged": ["正本市場日の差", "商品契約定義不足", "レーティング非網羅"],
    "japan_revision": "キオクシア・製造装置の競争圧力を追加し、単独因果は除外",
}
unresolved = evidence["publication_decision"].setdefault("unresolved_items", [])
unresolved[:] = [item for item in unresolved if item.get("id") != "cxmt-commercial-readiness"]
unresolved.append({
    "id": "cxmt-commercial-readiness",
    "status": "QUALIFIED",
    "missing": "4F² DDR5 RDIMMの仕様・歩留まり・顧客認定・出荷量",
    "impact": "中国要因を単独主因や即時業績悪化と断定しない",
    "last_checked_at": NOW,
    "next_action": "CXMT公式・顧客認定・出荷情報を継続確認",
    "attempts": [{"method": "CXMT公式とReuters確認", "result": "技術基盤と計画は確認、商用量産能力は未確認", "source_urls": [CXMT_OFFICIAL, REUTERS_CXMT], "checked_at": NOW}],
    "affected_components": ["ai_report", "japan_stocks"],
    "excluded_claims": ["CXMTが技術優位を確立", "半導体安の単独主因"],
    "excluded_from_publication": True,
})

save("report", report)
save("news", news)
save("news-display", display)
save("research-evidence", evidence)
print("patched 2026-10-14 report with audited CXMT context")
