import tempfile
import unittest
from pathlib import Path
from campus import build_visit_plan, find_study_spaces, get_service_hours, minutes, search_services
from history import History

class CampusTests(unittest.TestCase):
    def test_plan_fits_and_has_transfer(self):
        p = build_visit_plan("2026-10-27","13:30","17:30",["card","library"],60)
        self.assertEqual(len(p["itinerary"]),3)
        self.assertEqual(p["weekday"],"星期二")
        self.assertEqual(p["unplanned"],[])
        for a,b in zip(p["itinerary"],p["itinerary"][1:]):
            self.assertGreaterEqual(minutes(b["start"])-minutes(a["end"]),10)
        self.assertEqual(p["itinerary"][0]["start"],"13:30")

    def test_weekend_closed(self):
        self.assertFalse(get_service_hours("card","2026-11-01")["open"])
        p = build_visit_plan("2026-11-01","13:30","17:00",["card"],60)
        self.assertEqual(p["unplanned"][0]["reason"],"当天窗口不开放")
        self.assertEqual(p["itinerary"][0]["name"],"自习")

    def test_lunch_break(self):
        p = build_visit_plan("2026-10-27","11:20","14:30",["card"],0)
        self.assertEqual(p["itinerary"][0]["start"],"13:30")

    def test_insufficient_time(self):
        p = build_visit_plan("2026-10-27","16:20","16:30",["card"],60)
        self.assertEqual(p["itinerary"],[])
        self.assertEqual(len(p["unplanned"]),2)

    def test_room_overlap_and_accessibility(self):
        rooms = find_study_spaces("2026-10-27","14:30","15:30",accessible=True)["rooms"]
        self.assertEqual([r["id"] for r in rooms],["LIB2"])
        rooms = find_study_spaces("2026-10-27","16:00","17:00")["rooms"]
        self.assertIn("A201",[r["id"] for r in rooms])

    def test_no_rooms(self):
        self.assertEqual(find_study_spaces("2026-10-27","22:00","23:00")["count"],0)

    def test_unknown_service(self):
        self.assertEqual(search_services("不存在")["count"],0)
        with self.assertRaises(ValueError):
            build_visit_plan("2026-10-27","13:30","17:30",["invalid"])

    def test_validation(self):
        for a,b in [("25:00","26:00"),("9:00","10:00"),("18:00","17:00"),("10:99","12:00")]:
            with self.subTest(start=a):
                with self.assertRaises(ValueError):
                    find_study_spaces("2026-10-27",a,b)
        with self.assertRaises(ValueError):
            find_study_spaces("2026-02-30","10:00","12:00")
        with self.assertRaises(ValueError):
            build_visit_plan("2026-10-27","13:00","17:00",["card","card"])

    def test_shared_history_and_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"sessions.db"
            a,b = History(path),History(path)
            tid = a.new()
            a.save(tid,"user","帮我安排自习")
            self.assertEqual(b.messages(tid)[0]["content"],"帮我安排自习")
            b.rename(tid,"自习计划")
            self.assertEqual(a.sessions()[0][1],"自习计划")
            b.delete(tid)
            self.assertEqual(a.sessions(),[])
            self.assertEqual(a.messages(tid),[])

    def test_blank_session_is_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            history = History(Path(temp)/"sessions.db")
            first = history.new()
            second = history.new()
            third = history.new()
            history.save(first,"user","校园卡补办")
            kept = history.blank()
            ids = {sid for sid,_ in history.sessions()}
            self.assertEqual(len(ids),2)
            self.assertIn(first,ids)
            self.assertIn(kept,{second,third})
            self.assertNotEqual(kept,first)
            self.assertEqual(history.blank(),kept)
            self.assertEqual(len(history.sessions()),2)

if __name__ == "__main__":
    unittest.main()
