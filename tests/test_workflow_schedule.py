from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WorkflowScheduleTests(unittest.TestCase):
    def test_market_update_runs_weekdays_at_0620_jst(self):
        workflow = (ROOT / ".github/workflows/market-morning.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('cron: "20 21 * * 0-4"', workflow)
        self.assertNotIn('cron: "7 22 * * *"', workflow)

    def test_success_status_is_committed_only_after_validation(self):
        workflow = (ROOT / ".github/workflows/market-morning.yml").read_text(
            encoding="utf-8"
        )
        first_validation = workflow.index("Validate data before publishing")
        status_update = workflow.index("Record successful market update")
        final_validation = workflow.index("Validate final publish bundle")
        self.assertLess(first_validation, status_update)
        self.assertLess(status_update, final_validation)
        self.assertIn("git add data/status.json", workflow)


if __name__ == "__main__":
    unittest.main()
