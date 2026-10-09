"""Validate only explicitly reviewed articles; never approve the market/report bundle."""
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ("source_read", "facts_verified", "chronology", "fact_analysis_separation", "limitations")


def validate(news):
    errors = []
    if not isinstance(news, dict):
        return ["news must be an object"]
    try:
        day = datetime.strptime(news["report_date"], "%Y-%m-%d").date()
        updated = datetime.fromisoformat(news["updated_at"])
        if updated.utcoffset() is None or updated.date() != day:
            errors.append("updated_at must have timezone and match report_date")
    except (KeyError, ValueError, TypeError):
        return ["invalid report_date or updated_at"]
    if news.get("publication_mode") != "verified_news":
        errors.append("publication_mode must be verified_news")
    if news.get("coverage_status") != "partial":
        errors.append("this feed must disclose partial coverage")
    if not isinstance(news.get("coverage_note"), str) or not news["coverage_note"].strip():
        errors.append("coverage_note required")
    articles = news.get("articles")
    if not isinstance(articles, list) or not articles:
        return errors + ["at least one verified article required"]
    ids = set()
    for i, article in enumerate(articles):
        prefix = f"articles[{i}]"
        if not isinstance(article, dict):
            errors.append(f"{prefix}: object required")
            continue
        for key in ("id", "title", "fact", "analysis", "limitations", "publisher"):
            if not isinstance(article.get(key), str) or not article[key].strip():
                errors.append(f"{prefix}: {key} required")
        if article.get("id") in ids:
            errors.append(f"{prefix}: duplicate id")
        ids.add(article.get("id"))
        if article.get("verification_status") != "PASS":
            errors.append(f"{prefix}: article verification must PASS")
        if article.get("source_type") != "primary":
            errors.append(f"{prefix}: primary source required")
        for key in ("source_url", "verification_url"):
            url = urlparse(str(article.get(key, "")))
            if url.scheme != "https" or not url.hostname or url.username:
                errors.append(f"{prefix}: safe HTTPS {key} required")
        try:
            published = datetime.strptime(article["published_date"], "%Y-%m-%d").date()
            checked = datetime.fromisoformat(article["verified_at"])
            if published > day or checked.utcoffset() is None or checked > updated or checked.date() < published:
                errors.append(f"{prefix}: invalid chronology")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{prefix}: dates required")
        evidence = article.get("verification", {})
        for check in CHECKS:
            entry = evidence.get(check, {}) if isinstance(evidence, dict) else {}
            if entry.get("status") != "PASS" or not isinstance(entry.get("evidence"), str) or not entry["evidence"].strip():
                errors.append(f"{prefix}: evidence required for {check}")
        if article.get("market_reaction_status") != "unverified" or article.get("market_reaction") != "未確認":
            errors.append(f"{prefix}: this fact-only feed must not assert market reaction")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    news = json.loads((args.root / "data/news.json").read_text())
    errors = validate(news)
    for error in errors:
        print("ERROR:", error)
    print("Verified news:", "FAIL" if errors else "PASS", "(market/report gate unchanged)")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
