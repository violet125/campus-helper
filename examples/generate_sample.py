"""Generate a clearly labeled rule-engine example without using a model or Key."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from campus import build_visit_plan

result = build_visit_plan("2026-10-27","13:30","17:30",["card","library"],60)
rows = ["# 校园办事与自习计划（规则示例）", "",
    "> 此文件由 examples/generate_sample.py 调用本地规则函数生成，不是在线模型或子代理生成的结果。校园资料全部为虚构样例，以学校官方文件与现场为准，不代表预约。", "",
    "## 日期与需求", "2026-10-27，13:30–17:30。按顺序补校园卡、还书、自习 60 分钟。", "",
    "## 时间表", "| 开始 | 结束 | 事项 | 地点 | 材料 |", "| --- | --- | --- | --- | --- |"]
for item in result["itinerary"]:
    rows.append(f"| {item['start']} | {item['end']} | {item['name']} | {item['place']} | {'；'.join(item['materials'])} |")
rows += ["", "## 未安排事项", str(result["unplanned"]) if result["unplanned"] else "无。", "", "## 假设"]
rows.extend("- "+item for item in result["assumptions"])
rows += ["", "## 数据来源", result["source"], "", "工具：build_visit_plan（内部调用 find_study_spaces）。", ""]
output = Path(__file__).with_name("示例计划.md")
output.write_text("\n".join(rows),encoding="utf-8")
print(output.name)
