"""No paid API calls. A scripted model tests the REAL graph and stdio MCP.

This does not establish real-model reasoning or provider availability.
"""
import asyncio
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field
import agent as module
import deadline_tools
from history import History

class ScriptedModel(BaseChatModel):
    responses: list = Field(default_factory=list)
    cursor: int = 0

    @property
    def _llm_type(self):
        return "integration-test-only"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self,messages,stop=None,run_manager=None,**kwargs):
        if self.cursor >= len(self.responses):
            message = AIMessage(content="已核验测试工具调用。")
        else:
            message = self.responses[self.cursor]
            self.cursor += 1
        return ChatResult(generations=[ChatGeneration(message=message)])

def call(name,args,index):
    return AIMessage(content="",tool_calls=[{"name":name,"args":args,"id":f"test_{index}","type":"tool_call"}])

class IntegrationTests(unittest.TestCase):
    def test_real_graph_mcp_skill_files_permissions_and_resume(self):
        asyncio.run(self._run())

    async def _run(self):
        original = module.ROOT
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copyfile(original/"AGENTS.md",root/"AGENTS.md")
            shutil.copytree(original/"skills",root/"skills")
            # MCP subprocess can import the actual local server and business rules.
            for name in ["mcp_server.py","campus.py","weather.py","mcp_servers.json"]:
                shutil.copyfile(original/name,root/name)
            data = root/"data"
            data.mkdir()
            (root/".env").write_text("SECRET_DO_NOT_EXPOSE=example",encoding="utf-8")
            responses = [
                call("get_current_time",{},1),
                call("calculate_days_until",{"deadline":"2026-10-27"},12),
                call("save_deadline",{"task_name":"高数作业","deadline":"2026-10-27"},13),
                call("read_file",{"file_path":"/workspace/deadlines.md"},14),
                call("search_services",{"query":"校园卡"},2),
                call("get_service_hours",{"service_id":"card","day":"2026-10-27"},3),
                call("find_study_spaces",{"day":"2026-10-27","start":"18:00","end":"20:00","accessible":True},4),
                call("read_file",{"file_path":"/skills/campus-planner/SKILL.md"},5),
                call("write_todos",{"todos":[{"content":"核查样例","status":"completed"}]},6),
                call("build_visit_plan",{"day":"2026-10-27","start":"13:30","end":"17:30","service_ids":["card","library"],"study_minutes":60},7),
                call("write_file",{"file_path":"/workspace/test.md","content":"# 测试计划\n虚构样例"},8),
                call("write_file",{"file_path":"/outside.md","content":"should be denied"},9),
                call("read_file",{"file_path":"/.env"},10),
                call("task",{"description":"审核：本计划全部为虚构样例，没有预约。请返回审核结论。","subagent_type":"critic"},11),
                AIMessage(content="审核完成：已标注虚构样例，没有声称真实预约。"),
                AIMessage(content="工具测试完成，文件在 /workspace/test.md。"),
            ]
            with patch.object(module,"ROOT",root),patch.object(module,"DATA",data),patch.object(module,"WORKSPACE",root/"workspace"),patch.object(deadline_tools,"WORKSPACE",root/"workspace"),patch.dict(os.environ,{"SUBAGENT_MODEL":"","MCP_CONFIG":"mcp_servers.json"}):
                runtime = module.AgentRuntime()
                runtime.history = History(data/"sessions.db")
                try:
                    await runtime.start(ScriptedModel(responses=responses))
                    self.assertEqual(set(runtime.info["mcp_tools"]),{"search_services","get_service_hours","find_study_spaces","get_weather_forecast"})
                    self.assertIn("calculate_days_until",runtime.info["custom_tools"])
                    self.assertIn("save_deadline",runtime.info["custom_tools"])
                    self.assertEqual(runtime.info["warnings"],[])
                    tid = runtime.history.new()
                    events = [e async for e in runtime.stream_events("执行集成测试",tid)]
                    self.assertFalse([e for e in events if e["type"]=="error"],events)
                    self.assertTrue(any(e["type"]=="token" for e in events),events)
                    self.assertTrue(any(e["type"]=="tool_call" for e in events),events)
                    self.assertTrue(any(e["type"]=="tool_result" for e in events),events)
                    self.assertTrue((root/"workspace"/"test.md").exists(),events)
                    self.assertFalse((data/"agent_context"/"outside.md").exists())
                    results = [e for e in events if e["type"]=="tool_result"]
                    self.assertEqual(len(results),14,events)
                    self.assertTrue((root/"workspace"/"deadlines.md").exists())
                    deadline_read = next(e["text"] for e in results if e["name"]=="read_file" and "高数作业" in e["text"])
                    self.assertIn("高数作业",deadline_read)
                    self.assertIn("审核完成",next(e["text"] for e in results if e["name"]=="task"))
                    self.assertIn("校园卡补办",next(e["text"] for e in results if e["name"]=="search_services"))
                    self.assertNotIn("SECRET_DO_NOT_EXPOSE",str(events))
                    self.assertTrue(any("denied" in e["text"].lower() for e in results))
                    state = await runtime.agent.aget_state({"configurable":{"thread_id":tid}})
                    self.assertGreater(len(state.values["messages"]),10)
                finally:
                    await runtime.close()
                # A fresh runtime must load the prior checkpoint and transcript.
                runtime2 = module.AgentRuntime()
                runtime2.history = History(data/"sessions.db")
                try:
                    await runtime2.start(ScriptedModel())
                    before = await runtime2.agent.aget_state({"configurable":{"thread_id":tid}})
                    self.assertGreater(len(before.values["messages"]),10)
                    events2 = [e async for e in runtime2.stream_events("继续",tid)]
                    self.assertEqual(events2[-1]["type"],"answer")
                    self.assertEqual(len(runtime2.history.messages(tid)),4)
                    await runtime2.delete(tid)
                    self.assertEqual(runtime2.history.sessions(),[])
                    cleared = await runtime2.agent.aget_state({"configurable":{"thread_id":tid}})
                    self.assertFalse(cleared.values)
                finally:
                    await runtime2.close()

if __name__ == "__main__":
    unittest.main()
