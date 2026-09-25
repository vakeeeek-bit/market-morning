import ast
import importlib
import types
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd


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

    def test_saved_close_fills_missing_intermediate_market_day(self):
        module = importlib.import_module("scripts.update_market")
        history = pd.DataFrame(
            {"Close": [100.0, 120.0]},
            index=pd.to_datetime(["2026-09-21", "2026-09-23"]),
        )
        original_yf = module.yf
        module.yf = types.SimpleNamespace(
            Ticker=lambda ticker: types.SimpleNamespace(history=lambda **kwargs: history)
        )
        try:
            result = module.get_market_data(
                {"name": "Test", "ticker": "TEST"},
                {
                    "name": "Test",
                    "ticker": "TEST",
                    "price": 110.0,
                    "status": "取得成功",
                    "market_date": "2026-09-22",
                },
            )
        finally:
            module.yf = original_yf

        self.assertEqual("2026-09-22", result["previous_market_date"])
        self.assertEqual(110.0, result["previous"])
        self.assertEqual(9.09, result["change_pct"])

    def test_fred_publication_lag_is_explicit(self):
        module = importlib.import_module("scripts.update_market")
        markets = {
            "sp500": {"market_date": "2026-09-23"},
            "us2y": {"market_date": "2026-09-22", "status": "取得成功"},
        }
        module.mark_fred_publication_lag(markets)
        self.assertIn("FRED DGS2", markets["us2y"]["stale_reason"])


if __name__ == "__main__":
    unittest.main()
