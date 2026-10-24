"""Keep MCP and SQLite on one persistent asyncio loop across Streamlit reruns."""
import asyncio
import atexit
import queue
import threading
from agent import AgentRuntime, safe_error, DATA
from history import History
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

class WebRunner:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.runtime = None
        self.init_lock = None
        atexit.register(self.close)

    async def ensure(self):
        if self.init_lock is None:
            self.init_lock = asyncio.Lock()
        async with self.init_lock:
            if self.runtime is None:
                runtime = AgentRuntime()
                try:
                    await runtime.start()
                except Exception:
                    await runtime.close()
                    raise
                self.runtime = runtime
        return self.runtime

    def submit(self, question, tid):
        result = queue.Queue()
        async def run():
            try:
                runtime = await self.ensure()
                result.put({"type":"info","info":runtime.info})
                async for event in runtime.stream_events(question, tid):
                    result.put(event)
            except Exception as exc:
                result.put({"type":"error","text":safe_error(exc)})
            finally:
                result.put(None)
        asyncio.run_coroutine_threadsafe(run(),self.loop)
        return result

    def delete(self, tid):
        async def run():
            if self.runtime:
                await self.runtime.delete(tid)
            else:
                DATA.mkdir(exist_ok=True)
                async with AsyncSqliteSaver.from_conn_string(str(DATA / "checkpoints.db")) as saver:
                    await saver.setup()
                    await saver.adelete_thread(tid)
                History().delete(tid)
        return asyncio.run_coroutine_threadsafe(run(),self.loop).result(timeout=45)

    def close(self):
        if self.loop.is_running():
            if self.runtime:
                try:
                    asyncio.run_coroutine_threadsafe(self.runtime.close(),self.loop).result(timeout=5)
                except Exception:
                    pass
            self.loop.call_soon_threadsafe(self.loop.stop)
