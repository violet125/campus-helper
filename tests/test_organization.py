import sqlite3,tempfile,unittest
from pathlib import Path
from history import History
class OrganizationTests(unittest.TestCase):
    def test_migration_pin_archive_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'history.db'
            with sqlite3.connect(p) as db:
                db.execute('CREATE TABLE sessions(id TEXT PRIMARY KEY,title TEXT,updated TEXT)')
                db.execute('INSERT INTO sessions VALUES (?,?,?)',('old','existing','2026-01-01'))
            db.close()
            h=History(p)
            h.save('old','user','keep this message')
            new=h.new()
            h.set_pinned('old',True)
            self.assertEqual(h.sessions()[0][0],'old')
            h.set_archived('old',True)
            self.assertNotIn('old',dict(h.sessions()))
            self.assertIn('old',dict(h.sessions(archived=True)))
            h=History(p)
            self.assertTrue(h.flags('old')['pinned'])
            self.assertEqual(h.messages('old')[0]['content'],'keep this message')
            h.set_archived('old',False)
            self.assertEqual(h.sessions()[0][0],'old')
            h.set_pinned('old',False)
            self.assertFalse(h.flags('old')['pinned'])
    def test_blank_cleanup_preserves_archived_and_pinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=History(Path(tmp)/'history.db')
            a,b=h.new(),h.new()
            h.set_archived(a,True)
            h.set_pinned(b,True)
            h.blank()
            self.assertIn(a,dict(h.sessions(True)))
            self.assertIn(b,dict(h.sessions()))
