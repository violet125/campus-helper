"""Streamlit campus assistant. Run: python -m streamlit run web.py"""
import os
import queue
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from campus import build_visit_plan, search_services, find_study_spaces
from history import BLANK_TITLE, History
from runner import WebRunner
from agent import safe_error

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
st.set_page_config(page_title="campus-helper", page_icon=":material/school:", layout="wide")
st.markdown("<style>" + (ROOT / "assets" / "theme.css").read_text(encoding="utf-8") + "</style>",unsafe_allow_html=True)

@st.cache_resource
def get_runner():
    return WebRunner()

history = History()
history.collapse_blanks(keep=st.query_params.get("thread") or st.session_state.get("tid"))
sessions = history.sessions()
ids = {tid for tid,_ in sessions}
requested = st.query_params.get("thread")
if "tid" not in st.session_state or st.session_state.tid not in ids:
    named = [sid for sid,title in sessions if title != BLANK_TITLE]
    if requested in ids:
        st.session_state.tid = requested
    elif named:
        st.session_state.tid = named[0]
    elif sessions:
        st.session_state.tid = sessions[0][0]
    else:
        st.session_state.tid = history.blank()
if requested in ids and requested != st.session_state.tid:
    st.session_state.tid = requested
tid = st.session_state.tid
if st.query_params.get("thread") != tid:
    st.query_params["thread"] = tid
messages = history.messages(tid)

def switch(new_tid):
    st.session_state.tid = new_tid
    st.query_params["thread"] = new_tid
    st.rerun()

with st.sidebar:
    st.markdown("## campus-helper")
    st.caption("校园办事 · 自习规划")
    if st.button("＋ 新对话",width="stretch"):
        st.session_state["main_tabs"] = "对话与规划"
        switch(history.blank())
    st.markdown("### 历史会话")
    pinned_ids = {sid for sid, _ in sessions if history.flags(sid)["pinned"]}
    for sid,title in history.sessions():
        if st.button(("置顶 · " if sid in pinned_ids else "")+("● " if sid == tid else "")+title,key=sid,width="stretch"):
            switch(sid)
    archived_sessions = history.sessions(archived=True)
    with st.expander(f"已归档（{len(archived_sessions)}）"):
        if not archived_sessions:
            st.caption("暂无归档会话")
        for archived_id, archived_title in archived_sessions:
            st.caption(archived_title)
            if st.button("恢复对话", key="restore_"+archived_id, width="stretch"):
                history.set_archived(archived_id, False)
                switch(archived_id)
    with st.expander("管理当前会话"):
        flags = history.flags(tid)
        if st.button("取消置顶" if flags["pinned"] else "置顶对话", key="pin_"+tid, width="stretch"):
            history.set_pinned(tid, not flags["pinned"])
            st.rerun()
        if st.button("归档对话", key="archive_"+tid, width="stretch"):
            history.set_archived(tid, True)
            switch(history.blank())
        with st.form("rename_"+tid):
            title = st.text_input("会话名称",value=dict(history.sessions()).get(tid,"新会话"),key="title_"+tid)
            rename_clicked = st.form_submit_button("保存名称")
        if rename_clicked:
            if title.strip():
                history.rename(tid,title)
                st.rerun()
            else:
                st.warning("请输入名称")
        with st.form("delete_form_"+tid):
            confirmed = st.checkbox("确认删除聊天和模型上下文（产出文件保留）",key="delete_"+tid)
            delete_clicked = st.form_submit_button("删除当前会话")
        if delete_clicked and not confirmed:
            st.warning("请先勾选确认删除。")
        if delete_clicked and confirmed:
            try:
                get_runner().delete(tid)
                switch(history.blank())
            except Exception as exc:
                st.error(safe_error(exc))
    with st.expander("工具与能力"):
        st.write("模型：",os.getenv("LLM_MODEL","qwen-plus"))
        st.write("框架：Deep Agents / LangGraph")
        st.write("自定义：时间查询、行程规划、截止日期提醒")
        st.write("MCP：指南、开放时间、自习空间、天气预报")
        st.write("Skills：campus-planner、service-guide、deadline-tracker、weather-forecast")
        st.write("子代理：researcher、critic")
        if "runtime_info" in st.session_state:
            st.json(st.session_state.runtime_info,expanded=False)

if not messages:
    st.markdown("<style>[data-testid=stTabs] [role=tablist] {display:none!important}</style>", unsafe_allow_html=True)

chat_tab, data_tab, file_tab = st.tabs(["对话与规划","样例数据与规则","产出文件"], key="main_tabs", on_change="rerun")
with data_tab:
    st.subheader("可核查的样例数据")
    st.write("本页直接运行本地业务函数，可在没有 API Key 时检查规则。智能对话仍需真实模型，不会用预设回复冒充。")
    st.json(search_services(),expanded=False)
    with st.form("local_rules"):
        day = st.date_input("计划日期")
        c1,c2 = st.columns(2)
        start = c1.text_input("开始时间", "13:30")
        end = c2.text_input("结束时间", "17:30")
        services = st.multiselect("服务",["card","library","repair"],default=["card","library"],format_func=lambda x:{"card":"校园卡补办","library":"图书借还","repair":"宿舍报修咨询"}[x])
        study = st.number_input("自习分钟数",0,480,60,10)
        accessible = st.checkbox("自习空间需要无障碍设施")
        run_rules = st.form_submit_button("核验本地规则")
    if run_rules:
        try:
            result = build_visit_plan(day.isoformat(),start,end,services,study,accessible)
            st.session_state["rule_result"] = result
            st.session_state.pop("rule_error", None)
        except ValueError as exc:
            st.session_state.pop("rule_result", None)
            st.session_state["rule_error"] = str(exc)
    if "rule_error" in st.session_state:
        st.error(st.session_state["rule_error"])
    if "rule_result" in st.session_state:
        result = st.session_state["rule_result"]
        st.dataframe(result["itinerary"],width="stretch")
        st.json(result,expanded=False)

with file_tab:
    st.subheader("生成的 Markdown 计划")
    st.caption("本机各会话共用工作目录。删除聊天不会删除这里的文件。")
    workspace = ROOT / "workspace"
    workspace.mkdir(exist_ok=True)
    files = [p for p in workspace.rglob("*.md") if p.resolve().is_relative_to(workspace.resolve()) and p.is_file()]
    if not files:
        st.info("在对话中提出“生成 Markdown 计划”后，文件会出现在这里。")
    for path in sorted(files):
        name = str(path.relative_to(workspace))
        with st.expander(name):
            if path.stat().st_size > 2_000_000:
                st.warning("文件超过 2 MB，请在本地工作目录打开。")
                continue
            body = path.read_text(encoding="utf-8",errors="replace")
            st.markdown(body)
            st.download_button("下载计划",body,file_name=path.name,mime="text/markdown",key="file_"+name)

key_ready = os.getenv("DASHSCOPE_API_KEY","").strip() not in ("","your-api-key-here")
# Keep chat_input at the root so Streamlit mounts it in its native fixed bottom container.
typed = st.chat_input("告诉我日期、空闲时段和要办的事…", key="chat_prompt", disabled=not key_ready) if chat_tab.open else None

with chat_tab:
    if not key_ready:
        st.info("启用智能对话：复制 .env.example 为 .env，在本地填入 DASHSCOPE_API_KEY 后重启。现在可先查看“样例数据与规则”。")
    prompt = None
    welcome = st.empty()
    if not messages and not typed:
        welcome.markdown('<div class="chat-welcome">ask me something</div>', unsafe_allow_html=True)
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    prompt = typed or prompt
    if prompt:
        welcome.empty()
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            output = st.empty()
            saved_answer = False
            streamed_text = ""
            had_error = False
            q = get_runner().submit(prompt,tid)
            with st.status("执行过程：正在启动 Agent…", expanded=True) as execution:
                while True:
                    try:
                        event = q.get(timeout=1)
                    except queue.Empty:
                        continue
                    if event is None:
                        break
                    if event["type"] == "token":
                        streamed_text += event["text"]
                        output.markdown(streamed_text)
                    elif event["type"] == "tool_call":
                        execution.write(f"调用工具 · {event['scope']} · `{event['name']}`")
                    elif event["type"] == "tool_result":
                        if event.get("status") == "error":
                            execution.write(f"工具返回错误 · {event['scope']} · `{event['name']}`")
                        else:
                            execution.write(f"工具完成 · {event['scope']} · `{event['name']}`")
                    elif event["type"] == "answer":
                        saved_answer = True
                        output.markdown(event["text"])
                    elif event["type"] == "info":
                        st.session_state.runtime_info = event["info"]
                        for warning in event["info"]["warnings"]:
                            execution.write(f"运行提示：{warning}")
                    elif event["type"] == "todos" and event.get("scope") == "主 Agent":
                        st.session_state.latest_todos = event["items"]
                        execution.write(f"主 Agent 更新待办 · {len(event['items'])} 项")
                    elif event["type"] == "error":
                        had_error = True
                        st.error(event["text"])
                execution.update(
                    label="执行未完成" if had_error else "执行完成",
                    state="error" if had_error else "complete",
                    expanded=had_error,
                )
        if saved_answer:
            st.rerun()
