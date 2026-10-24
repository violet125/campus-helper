"""Deterministic deadline tools with local-only Markdown storage."""
from datetime import date, datetime
from pathlib import Path
import re
from threading import Lock
from zoneinfo import ZoneInfo

from campus import parse_day

WORKSPACE = Path(__file__).resolve().parent / "workspace"
_WRITE_LOCK = Lock()
_SHANGHAI = ZoneInfo("Asia/Shanghai")


def _today() -> date:
    return datetime.now(_SHANGHAI).date()


def _markdown_cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def calculate_days_until(deadline: str) -> dict:
    """计算距离截止日期还有几天；日期必须为 YYYY-MM-DD，今天为 0，逾期为负数。"""
    target = parse_day(deadline)
    today = _today()
    days_remaining = (target - today).days
    if days_remaining < 0:
        status = "overdue"
    elif days_remaining == 0:
        status = "today"
    else:
        status = "upcoming"
    return {
        "today": today.isoformat(),
        "deadline": target.isoformat(),
        "days_remaining": days_remaining,
        "status": status,
        "timezone": "Asia/Shanghai",
    }


def save_deadline(task_name: str, deadline: str) -> dict:
    """将作业或事项及其截止日期追加到本地 /workspace/deadlines.md。"""
    name = " ".join(task_name.split())
    if not name:
        raise ValueError("事项名称不能为空")
    if len(name) > 120:
        raise ValueError("事项名称不能超过 120 个字符")
    target = parse_day(deadline)
    today = _today()
    days_remaining = (target - today).days
    path = WORKSPACE / "deadlines.md"
    row = f"| {_markdown_cell(name)} | {target.isoformat()} | {days_remaining} |\n"
    with _WRITE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        needs_header = not path.exists() or path.stat().st_size == 0
        with path.open("a", encoding="utf-8", newline="\n") as file:
            if needs_header:
                file.write("# 作业与事项截止日期\n\n")
                file.write("| 事项 | 截止日期 | 保存时剩余天数 |\n")
                file.write("| --- | --- | ---: |\n")
            file.write(row)
    return {
        "saved": True,
        "file": "/workspace/deadlines.md",
        "task_name": name,
        "deadline": target.isoformat(),
        "days_remaining": days_remaining,
        "timezone": "Asia/Shanghai",
    }


def read_deadlines() -> list[dict]:
    """读取本地截止清单，并按当前上海日期重新计算倒计时。"""
    path = WORKSPACE / "deadlines.md"
    if not path.exists():
        return []

    entries = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = stripped[1:-1].split("|")
        date_index = next(
            (index for index in range(len(cells) - 1, -1, -1)
             if re.fullmatch(r"\s*\d{4}-\d{2}-\d{2}\s*", cells[index])),
            None,
        )
        if date_index is None:
            continue
        if date_index == 0:
            raise ValueError(f"{path.name} 第 {line_number} 行缺少事项名称")
        task_name = "|".join(cells[:date_index]).strip()
        task_name = re.sub(r"\\([\\|])", r"\1", task_name)
        if not task_name:
            raise ValueError(f"{path.name} 第 {line_number} 行事项名称为空")
        deadline = cells[date_index].strip()
        countdown = calculate_days_until(deadline)
        entries.append({
            "task_name": task_name,
            "deadline": deadline,
            "days_remaining": countdown["days_remaining"],
            "status": countdown["status"],
        })
    return entries
