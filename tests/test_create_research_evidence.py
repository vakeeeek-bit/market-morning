import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CreateResearchEvidenceTests(unittest.TestCase):
    def test_generated_worksheet_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "research-evidence.json"
            subprocess.run(
                ["python", "scripts/create_research_evidence.py", "--output", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            value = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(all(row["status"] == "未調査" for row in value["research_coverage"]["items"]))
            self.assertTrue(all(status == "FAIL" for status in value["quality_gates"].values()))


if __name__ == "__main__":
    unittest.main()
