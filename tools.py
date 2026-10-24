"""Custom tools shared by UI, CLI and subagents."""
from campus import get_current_time, build_visit_plan
from deadline_tools import calculate_days_until, save_deadline

CUSTOM_TOOLS = [get_current_time, build_visit_plan, calculate_days_until, save_deadline]
