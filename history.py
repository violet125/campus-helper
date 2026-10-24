"""UI transcripts are separate from LangGraph checkpoints."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parent
BLANK_TITLE = "新会话"

class History:
    def __init__(self, path=None):
        self.path = Path(path or ROOT / "data" / "sessions.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, title TEXT, updated TEXT);
            CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, thread TEXT, role TEXT, content TEXT, events TEXT);
            ''')
            columns = {row[1] for row in db.execute("PRAGMA table_info(sessions)")}
            for column in ("pinned", "archived"):
                if column not in columns:
                    db.execute(f"ALTER TABLE sessions ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def new(self):
        tid = uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO sessions(id,title,updated) VALUES (?,?,?)", (tid,BLANK_TITLE,datetime.now(timezone.utc).isoformat()))
        return tid

    def _empty_ids(self, db):
        return [row[0] for row in db.execute(
            "SELECT s.id FROM sessions s LEFT JOIN messages m ON m.thread=s.id "
            "WHERE s.title=? AND s.archived=0 AND s.pinned=0 GROUP BY s.id HAVING COUNT(m.id)=0 ORDER BY s.updated DESC",
            (BLANK_TITLE,),
        )]

    def collapse_blanks(self, keep=None):
        """Keep at most one empty untitled session in the sidebar."""
        with self.connect() as db:
            empty = self._empty_ids(db)
            if keep in empty:
                retain = keep
            else:
                retain = empty[0] if empty else None
            for tid in empty:
                if tid != retain:
                    db.execute("DELETE FROM messages WHERE thread=?", (tid,))
                    db.execute("DELETE FROM sessions WHERE id=?", (tid,))
            return retain

    def blank(self):
        """Reuse the empty untitled session, or create one."""
        existing = self.collapse_blanks()
        return existing or self.new()

    def sessions(self, archived=False):
        with self.connect() as db:
            return db.execute("SELECT id,title FROM sessions WHERE archived=? ORDER BY pinned DESC,updated DESC,id", (int(archived),)).fetchall()

    def flags(self, tid):
        with self.connect() as db:
            row = db.execute("SELECT pinned,archived FROM sessions WHERE id=?", (tid,)).fetchone()
            if row is None:
                raise ValueError("会话不存在")
            return {"pinned": bool(row[0]), "archived": bool(row[1])}

    def set_pinned(self, tid, value):
        with self.connect() as db:
            db.execute("UPDATE sessions SET pinned=? WHERE id=?", (int(value),tid))

    def set_archived(self, tid, value):
        with self.connect() as db:
            db.execute("UPDATE sessions SET archived=? WHERE id=?", (int(value),tid))

    def messages(self, tid):
        with self.connect() as db:
            return [{"role":r,"content":c,"events":json.loads(e)} for r,c,e in db.execute("SELECT role,content,events FROM messages WHERE thread=? ORDER BY id", (tid,))]

    def save(self, tid, role, content, events=None):
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM sessions WHERE id=?", (tid,)).fetchone():
                raise ValueError("会话不存在")
            db.execute("INSERT INTO messages(thread,role,content,events) VALUES (?,?,?,?)",(tid,role,content,json.dumps(events or [],ensure_ascii=False)))
            if role == "user":
                db.execute("UPDATE sessions SET title=? WHERE id=? AND title=?",(content[:28],tid,BLANK_TITLE))
            db.execute("UPDATE sessions SET updated=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),tid))

    def rename(self, tid, title):
        if not title.strip():
            raise ValueError("标题不能为空")
        with self.connect() as db:
            db.execute("UPDATE sessions SET title=? WHERE id=?",(title.strip()[:60],tid))

    def delete(self, tid):
        with self.connect() as db:
            db.execute("DELETE FROM messages WHERE thread=?",(tid,))
            db.execute("DELETE FROM sessions WHERE id=?",(tid,))
