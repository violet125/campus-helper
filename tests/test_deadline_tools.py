import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import deadline_tools


class DeadlineToolsTests(unittest.TestCase):
    def setUp(self):
        self.today = datetime(2026, 10, 24)
        self.clock = patch.object(
            deadline_tools,
            "datetime",
            SimpleNamespace(now=lambda tz: self.today.replace(tzinfo=tz)),
        )
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_calculate_days_until_handles_future_today_and_overdue(self):
        self.assertEqual(deadline_tools.calculate_days_until("2026-10-30")["days_remaining"], 6)
        today = deadline_tools.calculate_days_until("2026-10-24")
        self.assertEqual((today["days_remaining"], today["status"]), (0, "today"))
        overdue = deadline_tools.calculate_days_until("2026-10-23")
        self.assertEqual((overdue["days_remaining"], overdue["status"]), (-1, "overdue"))
        self.assertEqual(today["timezone"], "Asia/Shanghai")

    def test_invalid_dates_are_rejected(self):
        for value in ("2026-02-30", "2026-1-01"):
            with self.subTest(deadline=value), self.assertRaises(ValueError):
                deadline_tools.calculate_days_until(value)

    def test_save_appends_only_to_deadlines_file_and_escapes_table_cells(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(deadline_tools, "WORKSPACE", Path(temp)):
                result = deadline_tools.save_deadline("  高数作业 | 期中  ", "2026-10-30")
                deadline_tools.save_deadline("英语报告", "2026-10-24")
                entries = deadline_tools.read_deadlines()
            content = (Path(temp) / "deadlines.md").read_text(encoding="utf-8")

        self.assertTrue(result["saved"])
        self.assertEqual(result["file"], "/workspace/deadlines.md")
        self.assertIn("高数作业 \\| 期中", content)
        self.assertIn("| 事项 | 截止日期 | 保存时剩余天数 |", content)
        self.assertEqual(entries[0]["task_name"], "高数作业 | 期中")
        self.assertEqual(entries[0]["days_remaining"], 6)
        self.assertEqual(entries[1]["days_remaining"], 0)
        self.assertEqual(content.count("# 作业与事项截止日期"), 1)

    def test_read_deadlines_recalculates_saved_countdown_for_today(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            with patch.object(deadline_tools, "WORKSPACE", workspace):
                deadline_tools.save_deadline("高数作业", "2026-10-30")
                with patch.object(
                    deadline_tools,
                    "datetime",
                    SimpleNamespace(now=lambda tz: datetime(2026, 10, 29).replace(tzinfo=tz)),
                ):
                    entries = deadline_tools.read_deadlines()

        self.assertEqual(entries[0]["days_remaining"], 1)
        self.assertEqual(entries[0]["status"], "upcoming")

    def test_save_rejects_empty_or_overlong_task_names(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(deadline_tools, "WORKSPACE", Path(temp)):
            with self.assertRaises(ValueError):
                deadline_tools.save_deadline(" \n ", "2026-10-30")
            with self.assertRaises(ValueError):
                deadline_tools.save_deadline("作业" * 61, "2026-10-30")
            self.assertFalse((Path(temp) / "deadlines.md").exists())


if __name__ == "__main__":
    unittest.main()
