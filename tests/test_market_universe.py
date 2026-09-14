import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_symbols():
    tree = ast.parse((ROOT / "scripts" / "update_market.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "SYMBOLS" for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("SYMBOLS定義が見つかりません")


class MarketUniverseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.symbols = load_symbols()

    def test_required_us_indices_and_commodities_are_configured(self):
        required = {"nasdaq100", "sox", "wti", "brent", "copper"}
        self.assertTrue(required.issubset(self.symbols))

    def test_all_eleven_us_sector_proxies_are_configured(self):
        expected = {
            "sector_xlc",
            "sector_xly",
            "sector_xlp",
            "sector_xle",
            "sector_xlf",
            "sector_xlv",
            "sector_xli",
            "sector_xlb",
            "sector_xlre",
            "sector_xlk",
            "sector_xlu",
        }
        self.assertEqual(expected, {key for key in self.symbols if key.startswith("sector_")})


if __name__ == "__main__":
    unittest.main()
