import json
import unittest
from pathlib import Path
from scripts.validate_news import validate, validate_collection

ROOT = Path(__file__).resolve().parents[1]


class VerifiedNewsTest(unittest.TestCase):
    def setUp(self):
        self.news = json.loads((ROOT / "data/news.json").read_text())

    def test_verified_feed_passes_without_market_status(self):
        self.assertEqual(validate(self.news), [])

    def test_unverified_fact_is_blocked(self):
        self.news["articles"][0]["verification_status"] = "MANUAL_REVIEW"
        self.assertTrue(validate(self.news))

    def test_empty_evidence_cannot_claim_pass(self):
        self.news["articles"][0]["verification"]["facts_verified"]["evidence"] = ""
        self.assertTrue(validate(self.news))

    def test_unsafe_url_is_blocked(self):
        self.news["articles"][0]["source_url"] = "javascript:alert(1)"
        self.assertTrue(validate(self.news))

    def test_future_fact_is_blocked(self):
        self.news["articles"][0]["published_date"] = "2099-01-01"
        self.assertTrue(validate(self.news))

    def test_market_reaction_requires_separate_review(self):
        self.news["articles"][0]["market_reaction"] = "株価上昇"
        self.assertTrue(validate(self.news))

    def test_both_pages_show_independent_feed(self):
        for filename in ("index.html", "japan-stocks.html"):
            page = (ROOT / filename).read_text()
            self.assertIn('id="verified-news"', page)
            self.assertIn('src="/assets/verified-news.js"', page)

    def retrospective(self):
        self.news["report_date"] = max(article["published_date"] for article in self.news["articles"])
        self.news["edition"] = "retrospective"
        self.news["collected_at"] = self.news["updated_at"]
        self.news["original_as_of_status"] = "not_reconstructed"

    def test_retrospective_actual_collection_time(self):
        self.retrospective()
        self.assertEqual(validate(self.news), [])

    def test_retrospective_cannot_claim_original_as_of(self):
        self.retrospective()
        self.news["original_as_of_status"] = "verified"
        self.assertTrue(validate(self.news))

    def test_retrospective_requires_collection_timestamp(self):
        self.retrospective()
        del self.news["collected_at"]
        self.assertTrue(validate(self.news))

    def test_all_indexed_archives_pass(self):
        self.assertEqual(validate_collection(ROOT), [])

    def test_history_does_not_fallback_to_latest(self):
        script = (ROOT / "assets/verified-news.js").read_text()
        self.assertIn('/data/history/${selected}', script)
        self.assertIn('news-date', script)
