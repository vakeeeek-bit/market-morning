#!/usr/bin/env python3
"""Keep Japan company-news and analyst-research states explicit.

Verified company articles carrying both company and ticker metadata are copied
from news.json. Empty arrays are retained only with a visible collection state;
absence is never presented as "no changes" unless a source explicitly proves it.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JAPAN_PATH = ROOT / "data" / "japan-stocks.json"
NEWS_PATH = ROOT / "data" / "news.json"


def story_from_article(article: dict) -> dict | None:
    if article.get("verification_status") != "PASS":
        return None
    company = article.get("company")
    ticker = article.get("ticker")
    if not company or not ticker:
        return None
    return {
        "company": company,
        "ticker": ticker,
        "headline": article.get("title", "確認済み企業開示"),
        "fact": article.get("fact", ""),
        "source_url": article.get("source_url", ""),
        "analysis": article.get("analysis", ""),
        "category": article.get("category", "企業固有材料"),
        "related_sectors": article.get("related_sectors", []),
        "today_watch": article.get("today_watch", article.get("limitations", "追加開示と株価反応")),
        "announced_at": article.get("published_date", ""),
        "timing": article.get("timing", "公表時刻と市場反応を分離"),
        "market_pricing_status": article.get("market_pricing_status", "株価への反映は未確認"),
        "price_reaction": article.get("market_reaction", "未確認"),
        "related_stocks": article.get("related_stocks", []),
        "importance": article.get("importance", "high"),
        "confidence": "supported",
    }


def normalize(japan: dict, news: dict) -> dict:
    groups = ["top_stories", "important_stories", "other_stories"]
    for key in groups:
        if not isinstance(japan.get(key), list):
            japan[key] = []
    existing = {
        (item.get("ticker"), item.get("headline"))
        for key in groups for item in japan[key] if isinstance(item, dict)
    }
    for article in news.get("articles", []):
        story = story_from_article(article)
        if story and (story["ticker"], story["headline"]) not in existing:
            japan["important_stories"].append(story)
            existing.add((story["ticker"], story["headline"]))

    story_count = sum(len(japan[key]) for key in groups)
    quick = japan.setdefault("japan_quick_view", {})
    quick["individual_news_review"] = {
        "status": "reviewed" if story_count else "partial",
        "story_count": story_count,
        "scope": (
            "一次資料を確認した企業固有材料のみ掲載。件数合わせは行わない"
            if story_count
            else "確認済み企業固有材料は0件。未調査や取得不能を『材料なし』とは扱わない"
        ),
    }

    ratings = japan.get("analyst_rating_changes")
    if not isinstance(ratings, dict):
        ratings = {}
        japan["analyst_rating_changes"] = ratings
    ratings["items"] = ratings.get("items") if isinstance(ratings.get("items"), list) else []
    ratings.setdefault("coverage_status", "取得不能（公開情報では網羅不可）")
    ratings.setdefault("headline", "確認できた重要変更のみ掲載")
    ratings.setdefault("summary", "契約データ未導入。公開情報で確認できない日は『変更なし』と断定しません。")
    reviews = ratings.get("source_review") if isinstance(ratings.get("source_review"), list) else []
    normalized_reviews = []
    for source in reviews:
        name = source.get("name") or source.get("source") or "公開情報"
        source_url = source.get("url", "")
        if not source_url and "IFIS" in name:
            source_url = "https://kabuyoho.jp/"
        normalized_reviews.append({
            "name": name,
            "url": source_url,
            "result": source.get("result", "確認できず"),
            "coverage": source.get("coverage", "公開範囲のみ・全件網羅不可"),
            "freshness": source.get("freshness", "当日確認状況をJSONに記録"),
            "automation": source.get("automation", "契約API未導入"),
            "rights": source.get("rights", "確認できた事実だけを掲載"),
        })
    if not normalized_reviews:
        normalized_reviews.append({
            "name": "公開情報・IFIS等",
            "url": "https://kabuyoho.jp/",
            "result": "無料公開範囲では全証券会社・目標株価・EPS変更を網羅できず",
            "coverage": "公開範囲のみ・全件網羅不可",
            "freshness": "日次レポート作成時に確認",
            "automation": "契約API未導入",
            "rights": "確認できた重要変更だけを掲載",
        })
    ratings["source_review"] = normalized_reviews
    return japan


def main() -> None:
    japan = json.loads(JAPAN_PATH.read_text(encoding="utf-8"))
    news = json.loads(NEWS_PATH.read_text(encoding="utf-8")) if NEWS_PATH.exists() else {}
    JAPAN_PATH.write_text(
        json.dumps(normalize(japan, news), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print("日本株の個別ニュース・評価変更の取得状態を正規化しました")


if __name__ == "__main__":
    main()
