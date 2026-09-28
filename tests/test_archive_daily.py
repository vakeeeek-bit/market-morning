import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import archive_daily  # noqa: E402


class ArchiveDailyWeekendTests(unittest.TestCase):
    def test_weekend_report_can_archive_with_unchanged_market_date(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "data", root / "data")
            report_path = root / "data" / "report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["report_date"] = "2026-09-26"
            report["report_type"] = "weekend"
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

            replacements = {
                "ROOT": root,
                "DATA_DIR": root / "data",
                "REPORT_PATH": report_path,
                "MARKET_PATH": root / "data" / "market.json",
                "JAPAN_STOCKS_PATH": root / "data" / "japan-stocks.json",
                "JAPAN_MARKET_PATH": root / "data" / "japan-market.json",
                "RESEARCH_EVIDENCE_PATH": root / "data" / "research-evidence.json",
                "HISTORY_DIR": root / "data" / "history",
                "INDEX_PATH": root / "data" / "history" / "index.json",
            }
            with mock.patch.multiple(archive_daily, **replacements), mock.patch.object(archive_daily, "backfill_from_git"):
                archive_daily.main()

            self.assertTrue((root / "data" / "history" / "2026-09-26" / "report.json").exists())
            self.assertTrue((root / "data" / "history" / "2026-09-26" / "market.json").exists())
            self.assertTrue((root / "data" / "history" / "2026-09-28" / "research-evidence.json").exists())


if __name__ == "__main__":
    unittest.main()
