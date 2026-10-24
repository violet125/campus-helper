---
name: campus-planner
description: 当用户要规划校园办事、自习行程，或导出校园计划时使用。核查指南、生成时间表、审核结果，并按模板输出 Markdown。
---

# 校园办事与自习规划

1. 确认日期、起止时间、所需服务、自习时长及无障碍需求。不够明确先提问，不代填身份信息。
2. 遇到今天、明天先用 get_current_time 换算日期。
3. 调用 write_todos，列出核查、排程、审核、按需导出四步。
4. 使用 task 委派 researcher，通过 search_services、get_service_hours 和 find_study_spaces 核查样例资料。MCP 不可用时说明缺失，不能声称核查成功。
5. 调用 build_visit_plan，传入服务 ID、日期和时段。时间安排以这个确定性工具的输出为准。
6. 使用 task 委派 critic 审核完整工具结果。不要为了通过审核而编造开放时间。
7. 如用户要求文件，读取 /skills/campus-planner/template.md，用工具结果填充，然后 write_file 到 /workspace/plan-日期-简短唯一后缀.md。避免覆盖旧文件。
8. 列出未安排事项、假设与来源。完成后更新待办。只在写入成功后报告文件路径。

不要声称完成预约，不收集个人隐私，不把虚构样例当作学校实时信息。
