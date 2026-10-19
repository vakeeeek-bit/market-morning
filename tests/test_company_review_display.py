"""Keep the schema's company-review scope visible after normalization."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CompanyReviewDisplayTests(unittest.TestCase):
    def test_schema_scope_is_preferred_with_legacy_fallback(self):
        page = (ROOT / 'japan-stocks.html').read_text(encoding='utf-8')
        self.assertIn('text(review.scope || review.source)', page)
        self.assertNotIn('text(review.source)}｜掲載', page)


if __name__ == '__main__':
    unittest.main()
