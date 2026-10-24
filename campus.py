"""Deterministic campus business rules. Data is fictional and never a school API."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

SOURCE = "校园小帮手教学样例 v1（虚构，非学校官方数据）"
SERVICES = [
    {"id": "card", "name": "校园卡补办", "keywords": "饭卡 校园卡 丢卡 补卡 一卡通", "place": "学生服务中心 101", "weekdays": [0,1,2,3,4], "hours": [["09:00","11:30"],["13:30","16:30"]], "duration": 30, "materials": ["学生身份证明（演示仅列材料，不采集证件）", "校园卡挂失记录"], "steps": ["先通过学校官方渠道挂失", "携带所需材料到窗口核验", "按窗口实际规定办理"], "fee": "样例不提供收费标准，请向官方窗口核实"},
    {"id": "library", "name": "图书馆借还书", "keywords": "图书 图书馆 借书 还书 续借", "place": "图书馆一层服务台", "weekdays": [0,1,2,3,4,5,6], "hours": [["08:00","21:00"]], "duration": 20, "materials": ["校园卡或学校认可的身份凭证", "待归还图书（还书时）"], "steps": ["查看借阅状态", "到服务台或自助设备办理", "核对办理结果"], "fee": "逾期处理以学校官方规定为准"},
    {"id": "repair", "name": "宿舍报修咨询", "keywords": "宿舍 报修 维修 水电", "place": "后勤服务大厅", "weekdays": [0,1,2,3,4], "hours": [["08:30","11:30"],["13:00","17:00"]], "duration": 20, "materials": ["故障位置与描述（无需姓名或手机号）"], "steps": ["记录故障现象，勿自行拆修电器", "使用学校官方后勤渠道提交", "留意官方处理进度"], "fee": "以学校后勤部门说明为准"},
]
ROOMS = [
    {"id": "A201", "place": "教学楼 A201", "capacity": 40, "quiet": True, "accessible": False, "hours": [["08:00","21:00"]], "busy": [["09:00","11:00"],["14:00","16:00"]]},
    {"id": "A102", "place": "教学楼 A102", "capacity": 30, "quiet": True, "accessible": True, "hours": [["08:00","21:00"]], "busy": [["08:00","10:00"],["15:00","17:00"]]},
    {"id": "LIB2", "place": "图书馆二层自习区", "capacity": 80, "quiet": True, "accessible": True, "hours": [["08:00","21:00"]], "busy": []},
    {"id": "B103", "place": "教学楼 B103 讨论室", "capacity": 8, "quiet": False, "accessible": True, "hours": [["09:00","18:00"]], "busy": [["12:00","14:00"]]},
]

def minutes(value: str) -> int:
    """Parse strict HH:MM, rejecting malformed or out-of-range times."""
    if len(value) != 5 or value[2] != ":" or not value.replace(":", "").isdigit():
        raise ValueError("时间格式应为 HH:MM，例如 13:30")
    h, m = map(int, value.split(":"))
    if not 0 <= h <= 23 or not 0 <= m <= 59:
        raise ValueError("时间超出有效范围")
    return h * 60 + m

def clock(value: int) -> str:
    return f"{value//60:02d}:{value%60:02d}"

def parse_day(value: str) -> date:
    day = date.fromisoformat(value)
    if day.isoformat() != value:
        raise ValueError("日期格式应为 YYYY-MM-DD")
    return day

def interval(start: str, end: str) -> tuple[int, int]:
    a, b = minutes(start), minutes(end)
    if a >= b:
        raise ValueError("结束时间必须晚于开始时间；不支持跨日时段")
    return a, b

def envelope(**values) -> dict:
    return {"source": SOURCE, "notice": "演示数据；真实开放、空闲和办事制度以官方文件及现场为准。", **values}

def get_current_time() -> dict:
    """获取上海时区当前日期、时间和星期，解析今天、明天等相对日期前调用。"""
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    return {"datetime": now.isoformat(), "date": now.date().isoformat(), "tomorrow": (now.date()+timedelta(days=1)).isoformat(), "weekday": "星期"+"一二三四五六日"[now.weekday()], "timezone": "Asia/Shanghai"}

def search_services(query: str = "") -> dict:
    """按服务名称、关键词或 ID 查找办事指南；空字符串列出所有指南。"""
    q = query.strip().lower()
    matches = [dict(s) for s in SERVICES if not q or q in (s["id"]+s["name"]+s["keywords"]).lower()]
    return envelope(services=matches, count=len(matches))

def get_service_hours(service_id: str, day: str) -> dict:
    """查询某天服务窗口是否开放，日期 YYYY-MM-DD，周末会返回关闭。"""
    d = parse_day(day)
    service = next((s for s in SERVICES if s["id"] == service_id), None)
    if service is None:
        raise ValueError("未知服务 ID，请先调用 search_services")
    opened = d.weekday() in service["weekdays"]
    return envelope(service_id=service_id, day=day, open=opened, hours=service["hours"] if opened else [], holiday_policy="样例仅按星期判断，未接入节假日与临时停办通知")

def find_study_spaces(day: str, start: str, end: str, min_capacity: int = 1, quiet: bool = True, accessible: bool = False) -> dict:
    """查询指定日期、时段的样例自习空间，支持人数、安静与无障碍筛选；不创建预约。"""
    parse_day(day)
    a, b = interval(start, end)
    if min_capacity < 1 or min_capacity > 200:
        raise ValueError("人数应在 1 至 200 之间")
    matches = []
    for r in ROOMS:
        if r["capacity"] < min_capacity or (quiet and not r["quiet"]) or (accessible and not r["accessible"]):
            continue
        opened = any(minutes(x) <= a and b <= minutes(y) for x,y in r["hours"])
        occupied = any(a < minutes(y) and minutes(x) < b for x,y in r["busy"])
        if opened and not occupied:
            matches.append({k:v for k,v in r.items() if k not in ("hours", "busy")})
    return envelope(day=day, start=start, end=end, rooms=matches, count=len(matches), schedule="每日重复的虚构课表，不代表实时余位，也不保证一定有座")

def build_visit_plan(day: str, start: str, end: str, service_ids: list[str], study_minutes: int = 60, accessible: bool = False) -> dict:
    """按给定服务顺序，核对开放时段并生成无时间重叠的校园办事与自习计划。预留地点间步行 10 分钟（样例假设），无法安排的项目明确列出。"""
    d = parse_day(day)
    cursor, deadline = interval(start, end)
    if not 0 <= study_minutes <= 480:
        raise ValueError("自习时长须在 0 至 480 分钟之间")
    if len(service_ids) > 10 or len(set(service_ids)) != len(service_ids):
        raise ValueError("服务列表最多 10 项且不能重复")
    by_id = {s["id"]: s for s in SERVICES}
    if any(sid not in by_id for sid in service_ids):
        raise ValueError("存在未知服务 ID，请先查询指南")
    plan, unplanned = [], []
    for sid in service_ids:
        s = by_id[sid]
        if d.weekday() not in s["weekdays"]:
            unplanned.append({"name": s["name"], "reason": "当天窗口不开放"})
            continue
        ready = cursor + (10 if plan else 0)
        slot = next((max(ready, minutes(a)) for a,b in s["hours"] if max(ready, minutes(a))+s["duration"] <= min(minutes(b), deadline)), None)
        if slot is None:
            unplanned.append({"name": s["name"], "reason": "可用时间无法覆盖完整办理时长"})
            continue
        cursor = slot+s["duration"]
        plan.append({"start": clock(slot), "end": clock(cursor), "name": s["name"], "place": s["place"], "materials": s["materials"]})
    if study_minutes:
        ready = cursor+(10 if plan else 0)
        found = None
        for t in range(ready, deadline-study_minutes+1):
            spaces = find_study_spaces(day, clock(t), clock(t+study_minutes), accessible=accessible)["rooms"]
            if spaces:
                found = {"start": clock(t), "end": clock(t+study_minutes), "name": "自习", "place": spaces[0]["place"], "materials": ["学习资料"]}
                break
        if found:
            plan.append(found)
        else:
            unplanned.append({"name": "自习", "reason": "剩余时间或符合条件的空间不足"})
    return envelope(day=day, weekday="星期"+"一二三四五六日"[d.weekday()], requested_window=[start,end], itinerary=plan, unplanned=unplanned, assumptions=["按用户给定顺序安排，不保证全局最优", "不同地点间预留 10 分钟，仅作演示估计", "无障碍选项仅筛选自习空间，服务窗口设施须另行确认", "办理时长和每天重复的课表均为虚构，无预约、无提交行为"])
