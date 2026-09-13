import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_publish import prepare  # noqa: E402


class PreparePublishTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        shutil.copytree(ROOT / "data", self.root / "data")
        shutil.copytree(ROOT / "schemas", self.root / "schemas")
        self.source = Path(self.temporary.name) / "candidate"
        self.source.mkdir()
        for name in ("report.json", "japan-stocks.json"):
            shutil.copy2(ROOT / "data" / name, self.source / name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_valid_bundle_is_published(self):
        report = json.loads((self.source / "report.json").read_text(encoding="utf-8"))
        report["title"] = "公開テスト"
        (self.source / "report.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )

        prepare(self.source, self.root)

        published = json.loads((self.root / "data" / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(published["title"], "公開テスト")

    def test_mismatched_bundle_does_not_modify_data(self):
        before = (self.root / "data" / "report.json").read_bytes()
        japan = json.loads((self.source / "japan-stocks.json").read_text(encoding="utf-8"))
        japan["report_date"] = "2000-01-01"
        (self.source / "japan-stocks.json").write_text(
            json.dumps(japan, ensure_ascii=False), encoding="utf-8"
        )

        with self.assertRaises(ValueError):
            prepare(self.source, self.root)

        self.assertEqual((self.root / "data" / "report.json").read_bytes(), before)

    def test_missing_required_file_is_rejected(self):
        (self.source / "japan-stocks.json").unlink()
        with self.assertRaises(ValueError):
            prepare(self.source, self.root)


if __name__ == "__main__":
    unittest.main()
