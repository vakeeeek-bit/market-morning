import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_publish import prepare  # noqa: E402
from scripts.validate_data import run as structural_run


class PreparePublishTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        shutil.copytree(ROOT / "data", self.root / "data")
        shutil.copytree(ROOT / "schemas", self.root / "schemas")
        self.source = Path(self.temporary.name) / "candidate"
        self.source.mkdir()
        for name in ("report.json", "japan-stocks.json", "research-evidence.json"):
            shutil.copy2(ROOT / "data" / name, self.source / name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_valid_bundle_is_published(self):
        report = json.loads((self.source / "report.json").read_text(encoding="utf-8"))
        report["title"] = "公開テスト"
        (self.source / "report.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )

        # These two tests isolate atomic copying; publication admission is tested separately.
        with patch('prepare_publish.run', side_effect=lambda root, **kwargs: structural_run(root)):
            prepare(self.source, self.root)

        published = json.loads((self.root / "data" / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(published["title"], "公開テスト")

    def test_optional_japan_market_is_published_with_bundle(self):
        shutil.copy2(ROOT / "data" / "japan-market.json", self.source / "japan-market.json")
        payload = json.loads((self.source / "japan-market.json").read_text(encoding="utf-8"))
        payload["updated_at"] = "2026-09-28 07:25 JST"
        (self.source / "japan-market.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

        with patch('prepare_publish.run', side_effect=lambda root, **kwargs: structural_run(root)):
            prepare(self.source, self.root)

        published = json.loads((self.root / "data" / "japan-market.json").read_text(encoding="utf-8"))
        self.assertEqual("2026-09-28 07:25 JST", published["updated_at"])

    def test_stale_review_bundle_is_not_publishable(self):
        before = (self.root / 'data/report.json').read_bytes()
        with self.assertRaisesRegex(ValueError, '公開ゲート|自動公開不可'):
            prepare(self.source, self.root)
        self.assertEqual(before, (self.root / 'data/report.json').read_bytes())


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

    def test_missing_research_evidence_is_rejected(self):
        (self.source / "research-evidence.json").unlink()
        with self.assertRaisesRegex(ValueError, "research-evidence.json"):
            prepare(self.source, self.root)

    def test_failed_quality_gate_does_not_modify_data(self):
        before = (self.root / "data" / "report.json").read_bytes()
        evidence_path = self.source / "research-evidence.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["quality_gates"]["counter_evidence_audit"] = "FAIL"
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")

        with self.assertRaises(ValueError):
            prepare(self.source, self.root)
        self.assertEqual((self.root / "data" / "report.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
