#!/usr/bin/env python3
"""Verified TDnet company news used by the 2026-09-25..28 reports.

The Japan page keeps market/sector drivers in ``japan-market.json``.  Items in
``japan-stocks.json`` are deliberately limited to named listed companies with
an exchange ticker and a primary disclosure source.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


def _story(
    company: str,
    ticker: str,
    headline: str,
    category: str,
    fact: str,
    announced_at: str,
    timing: str,
    pricing_status: str,
    price_reaction: str,
    sectors: list[str],
    importance: str,
    source_url: str,
    analysis: str,
    watch: str,
) -> dict:
    return {
        "company": company,
        "ticker": ticker,
        "headline": headline,
        "category": category,
        "fact": fact,
        "announced_at": announced_at,
        "timing": timing,
        "market_pricing_status": pricing_status,
        "price_reaction": price_reaction,
        "related_stocks": [],
        "related_sectors": sectors,
        "importance": importance,
        "confidence": "高",
        "source_url": source_url,
        "analysis": analysis,
        "today_watch": watch,
        "image_url": None,
        "image_alt": None,
        "image_credit": None,
        "image_source_url": None,
    }


SEP25_TOP = [
    _story(
        "日本オラクル", "4716", "第1四半期は増収増益、営業利益22.7%増", "決算",
        "2027年5月期第1四半期は売上高748.61億円（前年同期比13.0%増）、営業利益259.18億円（22.7%増）。",
        "2026-09-24（TDnet）", "9月24日大引け後", "9月25日終値に反映済み",
        "9月25日は前日比6.3%上昇。", ["情報通信・サービス"], "★★★★★",
        "https://www.release.tdnet.info/inbs/140120260916537545.pdf",
        "利益成長を伴う増収が確認された。株価上昇も確認できるが、翌日以降の継続は別途見る。",
        "上昇が続くか、利益成長率と売上成長率の差が維持されるか",
    ),
    _story(
        "生化学工業", "4548", "通期予想を営業赤字へ下方修正、減配も発表", "業績修正・配当",
        "通期営業利益予想を20.5億円から20.5億円の赤字へ、純利益を22.5億円から18億円の赤字へ修正。年間配当予想は30円から20円へ。",
        "2026-09-24（TDnet）", "9月24日大引け後", "9月25日終値に反映済み",
        "9月25日終値は623円、前日比8.91%下落。", ["医薬品"], "★★★★★",
        "https://www.release.tdnet.info/inbs/140120260924539535.pdf",
        "利益見通しと還元の双方が悪化し、株価も下落した。売上減少の内訳と赤字幅の改善時期が焦点。",
        "会社計画の前提、費用削減策、配当方針の追加説明",
    ),
    _story(
        "清水建設", "1803", "自己株式取得枠を最大200億円へ拡大", "自社株買い",
        "自己株式取得の上限を600万株・100億円から1200万株・200億円へ拡大。転換社債型新株予約権付社債への対応も説明。",
        "2026-09-24（TDnet）", "9月24日大引け後", "9月25日終値に反映済み",
        "9月25日終値は2,210円、前日比5.98%下落。", ["建設・資材"], "★★★★★",
        "https://www.release.tdnet.info/inbs/140120260924539335.pdf",
        "取得枠拡大は還元強化だが、当日の株価は下落した。転換社債条件など他の材料も含めて反応を読む必要がある。",
        "実際の取得進捗と転換社債による希薄化懸念",
    ),
]

SEP25_IMPORTANT = [
    _story(
        "カバー", "5253", "上期営業利益予想を81.3%上方修正", "業績修正",
        "上期営業利益予想を19.3億円から35億円へ、純利益を13.5億円から23億円へ修正。通期予想は据え置き。",
        "2026-09-24（TDnet）", "9月24日大引け後", "9月25日終値に反映済み",
        "9月25日は下落。上方修正だけでは株価反応を説明できないため、期待との差は断定しない。", ["情報通信・サービス"], "★★★★☆",
        "https://www.release.tdnet.info/inbs/140120260924539536.pdf",
        "上期はスマートフォンゲームが寄与した一方、通期据え置き。修正幅だけでなく下期前提を確認する。",
        "通期据え置きの理由、ゲーム寄与の継続性、下期利益率",
    ),
]


NEXT_SESSION_TOP = [
    _story(
        "加賀電子", "8154", "通期純利益予想を31.8%上方修正、増配", "業績修正・配当",
        "通期売上高を6,600億円から7,600億円へ、純利益を220億円から290億円へ修正。年間配当予想は140円から160円へ。",
        "2026-09-25（TDnet）", "9月25日大引け後", "次回取引に未反映",
        "東証休場中または寄り付き前のため未確認。", ["商社・卸売", "電機・精密"], "★★★★★",
        "https://www.release.tdnet.info/inbs/140120260924539188.pdf",
        "新光商事の連結化と負ののれんが修正に含まれる。継続的な本業利益と一時要因を分けて見る。",
        "次回取引の株価・出来高、負ののれんを除く利益寄与",
    ),
    _story(
        "三十三フィナンシャルグループ", "7322", "通期利益予想を上方修正、年間配当50円へ", "業績修正・配当",
        "通期経常利益を214億円から245億円へ、純利益を150億円から170億円へ修正。年間配当予想は44円から50円へ。",
        "2026-09-25（TDnet）", "9月25日大引け後", "次回取引に未反映",
        "東証休場中または寄り付き前のため未確認。", ["銀行"], "★★★★★",
        "https://www.release.tdnet.info/inbs/140120260914536153.pdf",
        "利益と配当の同時上方修正。金利環境の追い風が貸出収益や利ざやにどう表れるかも確認する。",
        "次回取引の株価・出来高、修正の内訳と利ざや",
    ),
    _story(
        "Orchestra Holdings", "6533", "年間配当50円へ増配、株主優待も拡充", "配当・株主優待",
        "年間配当予想を30円から50円へ修正。200株以上の株主向けデジタルギフトを拡充し、記念優待も設定。",
        "2026-09-25（TDnet）", "9月25日大引け後", "次回取引に未反映",
        "東証休場中または寄り付き前のため未確認。", ["情報通信・サービス"], "★★★★★",
        "https://www.release.tdnet.info/inbs/140120260925540527.pdf",
        "還元強化は明確だが、優待コストと継続性を本業のキャッシュ創出力と合わせて見る。",
        "次回取引の株価・出来高、還元の継続性",
    ),
]

NEXT_SESSION_IMPORTANT = [
    _story(
        "東邦銀行", "8346", "年間配当予想を21円から26円へ増配", "配当",
        "業績予想の上方修正と利息収入の増加を踏まえ、年間配当予想を5円引き上げ。",
        "2026-09-25（TDnet）", "9月25日大引け後", "次回取引に未反映",
        "東証休場中または寄り付き前のため未確認。", ["銀行"], "★★★★☆",
        "https://www.release.tdnet.info/inbs/140120260924539703.pdf",
        "増配の背景に本業収益の改善があるかを、同時発表の業績修正と合わせて確認する。",
        "次回取引の反応、貸出金利息と有価証券収益の内訳",
    ),
    _story(
        "ナガオカ", "6239", "北米向けスクリーン内部装置を約7.7億円で受注", "受注",
        "北米のプロピレン製造プラント向けに約7.7億円を受注。納期は2027年9月、2028年1月、2029年12月。今期予想は据え置き。",
        "2026-09-25（TDnet）", "9月25日大引け後", "次回取引に未反映",
        "東証休場中または寄り付き前のため未確認。", ["機械"], "★★★★☆",
        "https://www.release.tdnet.info/inbs/140120260925540363.pdf",
        "受注額は確認できるが、納期が分散しており今期業績への寄与は限定的。受注残への寄与を長期で見る。",
        "次回取引の反応、売上計上時期と採算",
    ),
]


def apply_company_news(report: dict, japan: dict, report_date: str) -> None:
    """Replace sector/macro pseudo-stories with audited company disclosures."""
    if report_date == "2026-09-25":
        top, important = SEP25_TOP, SEP25_IMPORTANT
        reviewed_at = "2026-09-28 13:30 JST"
    elif report_date in {"2026-09-26", "2026-09-27", "2026-09-28"}:
        top, important = NEXT_SESSION_TOP, NEXT_SESSION_IMPORTANT
        reviewed_at = "2026-09-28 13:30 JST"
    else:
        raise ValueError(f"unsupported audit date: {report_date}")

    japan["top_stories"] = deepcopy(top)
    japan["important_stories"] = deepcopy(important)
    japan["other_stories"] = []
    japan["company_events"] = []
    total = len(top) + len(important)
    japan.setdefault("japan_quick_view", {})["individual_news_review"] = {
        "status": "reviewed",
        "reviewed_at": reviewed_at,
        "source": "TDnet・企業開示（一次情報）",
        "story_count": total,
        "scope": "直近の取引日大引け後までの重要開示",
    }
    preview = report.setdefault("japan_equities_preview", {})
    preview["top_stories"] = [
        {
            "company": item["company"],
            "ticker": item["ticker"],
            "headline": item["headline"],
            "importance": item["importance"],
            "market_pricing_status": item["market_pricing_status"],
        }
        for item in top[:3]
    ]
    preview["total_story_count"] = total
    cautions = japan.setdefault("data_quality", {}).setdefault("cautions", [])
    note = "個別株ニュースは2026年9月28日にTDnet一次情報で再監査"
    if note not in cautions:
        cautions.append(note)


def backfill(root: Path) -> None:
    for report_date in ("2026-09-25", "2026-09-26", "2026-09-27", "2026-09-28"):
        folder = root / "data" / "history" / report_date
        report_path = folder / "report.json"
        japan_path = folder / "japan-stocks.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        japan = json.loads(japan_path.read_text(encoding="utf-8"))
        apply_company_news(report, japan, report_date)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        japan_path.write_text(json.dumps(japan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    latest_report = json.loads((root / "data" / "report.json").read_text(encoding="utf-8"))
    latest_japan = json.loads((root / "data" / "japan-stocks.json").read_text(encoding="utf-8"))
    apply_company_news(latest_report, latest_japan, latest_report["report_date"])
    (root / "data" / "report.json").write_text(
        json.dumps(latest_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (root / "data" / "japan-stocks.json").write_text(
        json.dumps(latest_japan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    backfill(Path(__file__).resolve().parents[1])
