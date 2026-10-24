"""CLI using exactly the same Agent runtime and histories as web.py."""
import argparse
import asyncio
import json
from agent import AgentRuntime, safe_error

async def main():
    parser = argparse.ArgumentParser(description="校园小帮手")
    parser.add_argument("-c","--continue-last",action="store_true")
    parser.add_argument("-q","--question")
    args = parser.parse_args()
    runtime = AgentRuntime()
    try:
        print("正在加载模型、MCP、Skills 和会话存储…")
        await runtime.start()
        sessions = runtime.history.sessions()
        tid = sessions[0][0] if args.continue_last and sessions else runtime.history.new()
        print(json.dumps(runtime.info,ensure_ascii=False,indent=2))
        print("教学样例，非学校官方数据。输入 /help 查看命令。")
        while True:
            question = args.question or input("\n你：").strip()
            if not question:
                continue
            if question == "/exit":
                break
            if question == "/help":
                print("/sessions /load 编号 /history /new /info /exit")
            elif question == "/sessions":
                for i,(_,title) in enumerate(runtime.history.sessions(),1):
                    print(i,title)
            elif question.startswith("/load "):
                try:
                    index = int(question.split()[1])-1
                    sessions = runtime.history.sessions()
                    if not 0 <= index < len(sessions):
                        raise ValueError()
                    tid = sessions[index][0]
                    for m in runtime.history.messages(tid):
                        print(m["role"]+"："+m["content"])
                except (ValueError,IndexError):
                    print("无效编号，请先输入 /sessions")
            elif question == "/history":
                for m in runtime.history.messages(tid):
                    print(m["role"]+"："+m["content"])
            elif question == "/new":
                tid = runtime.history.new()
                print("已创建新会话")
            elif question == "/info":
                print(json.dumps(runtime.info,ensure_ascii=False,indent=2))
            else:
                async for event in runtime.stream_events(question,tid):
                    if event["type"] == "token":
                        print(event["text"],end="",flush=True)
                    elif event["type"] == "tool_call":
                        print(f"\n[{event['scope']}] {event['name']} {json.dumps(event['args'],ensure_ascii=False)}")
                    elif event["type"] == "tool_result":
                        print(f"\n  返回：{event['text'][:1200]}")
                    elif event["type"] == "answer":
                        print("\n最终答复："+event["text"])
                    elif event["type"] == "error":
                        print("\n"+event["text"])
            if args.question:
                break
    except (KeyboardInterrupt,EOFError):
        print("\n会话已保存。")
    except Exception as exc:
        print(safe_error(exc))
        return 1
    finally:
        await runtime.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
