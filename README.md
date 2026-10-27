# 校园小帮手 Campus Companion

**路径 A：基于 LangChain Deep Agents 的校园服务智能体。** 面向学生，把校园办事指南查询、自习空间筛选和时间规划组合为一次自然语言任务，生成可下载的 Markdown 行程。

> 本项目的校园地点、窗口时间、材料和课表均为开发者构造的**虚构教学样例**，不代表杉达学院或任何实际学校。没有连接教务系统，没有真实预约、挂失、支付或报修提交操作。实际制度与服务以官方文件、专业人员及现场为准。

## 1. 路径 A 对照

| 要求 | 实现位置与可演示行为 |
| --- | --- |
| OpenAI 兼容接口调用国产模型 | `agent.py / build_model()`，阿里百炼 `ChatOpenAI` |
| 开源 Agent 框架 | `create_deep_agent()`，底层 LangGraph 状态图 |
| 至少 2 个自定义工具或 MCP ≥2 工具 | 4 个自定义工具，1 个 MCP 服务器含 4 个工具 |
| Agent Skill | `skills/campus-planner/`、`skills/service-guide/`、`skills/deadline-tracker/`、`skills/weather-forecast/`，带 YAML 头 |
| 可交互界面 | `web.py` Streamlit，同时提供 `app.py` CLI |
| 多轮和会话保存 | `checkpoints.db` 保存模型上下文，`sessions.db` 保存界面记录 |
| 明确产出文件 | 按模板写入 `workspace/*.md`，网页预览与下载 |

加分能力：`researcher`/`critic` 子代理、Open-Meteo 联网天气查询、`AGENTS.md` 长期记忆、文件系统隔离、工具事件与文字流式展示、Windows 启动脚本。

## 2. 环境与安装（Windows PowerShell）

推荐 **Python 3.12**，支持版本范围以锁定依赖为准；本项目实际验证使用 Python 3.12。首次安装需联网。没有 API Key 也可打开网页的“样例数据与规则”，但智能对话需要百炼密钥。

解压后在包含本 README 的目录打开 PowerShell。以下命令不要求激活虚拟环境：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

如果没有 `py` 命令，用已安装且加入 PATH 的 `python -m venv .venv` 替代第一行。

在 `.env` 中填写自己的 `DASHSCOPE_API_KEY`，不要把真实值放进 README、聊天、截图或 Git。`.env.example` 只有占位符。

| 变量 | 默认值 / 用途 |
| --- | --- |
| `DASHSCOPE_API_KEY` | 必填，在本地 `.env` 填写 |
| `LLM_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL` | `qwen-plus`，应设为你的接口实际开通的模型 |
| `SUBAGENT_MODEL` | 空则继承主模型 |
| `LLM_TEMPERATURE` | `0.3` |
| `MCP_CONFIG` | `mcp_servers.json` |

课堂 README 使用的课程专用地址和 `qwen3.7-plus` 未提供可用凭据，因此这里使用百炼公开兼容接口与可配置模型名。若教师指定课程接口，请自行修改 URL 和模型，不要照抄无法访问的地址。代码不覆盖已有系统环境变量。

## 3. 启动

```powershell
# 网页版；绑定本机，不对局域网公开
.\.venv\Scripts\python.exe -m streamlit run web.py --server.address 127.0.0.1

# 命令行版（另开终端）
.\.venv\Scripts\python.exe app.py
.\.venv\Scripts\python.exe app.py -q "校园卡补办需要什么材料？请查样例指南。"
.\.venv\Scripts\python.exe app.py -c -q "它在 2026-11-01 开门吗？"
```

浏览器访问 `http://localhost:8501`。也可以运行 `powershell -ExecutionPolicy Bypass -File .\start.ps1`，该脚本只为本次进程指定策略，不修改系统策略。脚本创建环境、安装依赖并启动网页，不会覆盖已有 `.env`。

CLI 命令：`/sessions` 列会话、`/load 编号` 继续会话、`/history` 回放、`/new` 新建、`/info` 查看能力、`/help` 帮助、`/exit` 退出。

网页可新建、切换、重命名、确认删除会话。截止日期 Skill 仍可将事项保存到本地工作区，但主界面不再显示提醒右侧栏。URL 的 `?thread=` 保存会话标识。**删除会话同时删除检查点与聊天记录，但保留工作目录产物。** 本地 Web/CLI 共享数据，请不要同时对同一会话发起请求；没有多用户身份认证，勿公网部署。

修改 `.env`、依赖、代码或 MCP 配置后重启。`AGENTS.md` 和技能文件在每轮前刷新到隔离上下文目录。

## 4. 推荐演示话术

1. “校园卡丢了，补办需要什么材料？请查询样例指南。”
2. “2026-10-27 18:00 到 20:00，有适合两人安静自习的无障碍空间吗？”
3. “请规划 2026-10-27 13:30 到 17:30 的行程：先补校园卡，再还书，最后自习 60 分钟。请核查并生成 Markdown 文件。”
4. 在同一会话追问：“把日期改成 2026-11-01，其他要求不变，再检查哪些事情办不了。”
5. “请把计划写到 /outside.md。”预期模型拒绝或工具拦截，不能写到工作目录之外。
6. “今天是 2026-10-24，帮我记下周五要交高数作业。”预期先将“周五”消歧（本周还是下周），确认日期后调用 `save_deadline` 写入 `/workspace/deadlines.md`；追问“还剩几天”时调用 `calculate_days_until`，追问“我记了什么”时读取清单。
7. “查一下上海明天的天气，需要带伞吗？”预期先调用 `get_current_time`，再由 MCP 工具查询 Open-Meteo；没有网络时说明无法核实。天气查询会向 Open-Meteo 发送城市和日期，不发送身份信息。

第 3 条是主演示路径，复杂调用可能耗时几分钟，建议先试跑。第 4 条应指出周日校园卡窗口关闭。对话答案会逐 token 显示；“执行过程”会实时列出工具调用与完成状态，展开可核对执行顺序。演示时确认出现 MCP 查询、`write_todos`、`task`、`build_visit_plan`、`write_file`；如果模型没有主动使用 Skill，可明确追加“请先读取 campus-planner 技能并按步骤执行”。不要只展示最终文字。

## 5. 技术架构与目录

```text
web.py / app.py
       │ 共用 stream_events()
       ▼
agent.py  Deep Agents / LangGraph
       ├── ChatOpenAI：阿里百炼兼容接口
       ├── 自定义工具：get_current_time / build_visit_plan / calculate_days_until / save_deadline
       ├── MCP campus-info：指南 / 开放时间 / 自习空间 / 天气预报
       ├── Skills：campus-planner / service-guide / deadline-tracker / weather-forecast
       ├── 子代理：researcher 核查、critic 审核
       ├── AGENTS.md：明确维护的长期规则
       ├── 受限文件系统：仅 workspace 可写
       └── SQLite：模型检查点 + UI 会话记录
```

```text
campus-helper/
├── README.md                 使用说明与考查对照
├── presentation.html         10 页离线 HTML 汇报幻灯片
├── docs/答辩与演示.md         4+4 分钟讲稿、问答、提交清单
├── docs/验证说明.md           已验证内容与未验证边界
├── examples/示例计划.md       本地规则生成示例，不冒充在线模型结果
├── web.py / app.py            双界面
├── agent.py / runner.py       Agent 组装、流事件、后台事件循环
├── campus.py / tools.py       校园业务规则、自定义工具注册
├── deadline_tools.py          Asia/Shanghai 截止倒数与本地清单工具
├── mcp_server.py              4 个只读 MCP 工具
├── weather.py                 Open-Meteo 地理编码与天气预报调用
├── mcp_servers.json           MCP 配置，支持 enabled 开关
├── history.py                SQLite 会话 CRUD
├── AGENTS.md                 长期记忆
├── skills/                   4 个规范技能与计划模板
├── tests/                    规则测试与真实框架/MCP 集成测试
├── workspace/                Agent 产出，Git 忽略内容
├── data/                     启动后生成，Git 忽略
├── requirements.txt / requirements-lock.txt
├── .env.example / .gitignore
└── start.ps1
```

### 工具职责

| 工具 | 类型 | 输入 / 返回 |
| --- | --- | --- |
| `get_current_time` | 自定义 | 上海当前日期、星期、明日日期 |
| `build_visit_plan` | 自定义 | 日期、时段、服务 ID、自习时长；返回不重叠时间表、未安排事项和假设 |
| `calculate_days_until` | 自定义 | 截止日期；返回上海时区今天、剩余天数和逾期状态 |
| `save_deadline` | 自定义 | 事项名称与截止日期；追加到 `/workspace/deadlines.md`，不设置外部通知 |
| `get_weather_forecast` | MCP | 城市/地区与日期；查询 Open-Meteo 温度、天气代码和降水概率，判断是否建议带伞 |
| `search_services` | MCP | 名称、关键词或空查询；返回来源、地点、材料、步骤 |
| `get_service_hours` | MCP | 服务 ID、日期；检查星期与开放时间，未覆盖节假日 |
| `find_study_spaces` | MCP | 日期、起止时间、人数、安静、无障碍；筛选样例课表 |

`build_visit_plan` 遵循用户给定顺序，在开放区间内查找最早可行完整时段，地点间预留 10 分钟，再扫描可用自习时段。时间、容量和日期有明确校验；无结果返回原因。它是确定性规则，不是最短路径或全局最优算法。

天气查询经 `get_weather_forecast` 访问 Open-Meteo；需提供城市/地区和日期，范围限今天起未来 15 天。地点名称发送给 Open-Meteo 地理编码服务；不发送用户身份信息。服务不可用时不生成猜测结果。

### Skills、记忆、子代理

Skill 用 YAML `name`/`description` 声明用途，框架先加载描述，需要时才读取步骤和模板。长期记忆是每轮都需要遵守的规则。`researcher` 查询事实，`critic` 审核工具结果；子代理有独立上下文。主模型仍负责选择工具和组织回答。

### 文件权限与隐私

不把项目根目录挂给 Agent。仅将公开的 `AGENTS.md` 和 `skills/` 复制进 `data/agent_context/` 作为只读上下文，再将 `/workspace/` 映射到实际工作目录。框架 `FilesystemPermission` 限制写入，仅放行 `/workspace/**`。`.env`、数据库和 `.venv` 都在挂载范围外。

此措施保护模型工具能访问的文件，并不是操作系统级沙箱。配置 MCP 的人属于可信开发者，不要接入未知服务器。本项目不提供 shell 执行工具。网页历史及所有输出由本机各会话共用，不适合多租户环境。

## 6. 相对课堂 demo_5 的增量

- 从“课程助教”改成校园服务闭环，有独立的 `campus.py` 业务层。
- 新增窗口开放校验、课表冲突判定、容量与无障碍筛选、办理时间和步行间隔排程。
- MCP 提供校园查询及 Open-Meteo 天气查询能力，输出可核对的数据来源。
- 新编写校园规划和服务指南 Skills，产出明确的校园计划。
- 子代理改为核查校园资料与审核计划的职责，不只是更换名称。
- 增加无密钥规则查看页、未安排原因、日期/时段校验与周末失败场景。
- 用公开上下文挂载隔离敏感文件，验证工作区外写入被拒绝。
- 提供自动化测试、离线 HTML 汇报、演示讲稿与提交清单。

本实现参考用户提供的 demo_5 README 结构与能力设计，未获得课堂源码，不宣称逐行继承课堂实现。使用 AI 编程助手辅助生成与检查；提交者须理解代码并如实说明自己的修改、测试和演示工作。

## 7. 测试与验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

无需 API Key。集成测试用**脚本测试模型**驱动真实 Deep Agents 图与真实 stdio MCP 进程，检查工具、Skill 读取、待办、文件写入、权限拒绝、检查点重启恢复与删除。脚本模型仅存在于测试文件，网页和 CLI 不使用它。

这些测试不能证明在线模型推理和接口可用性。后续已使用本地密钥跑通真实查询及规划导出，发现并修正演示文件的星期错误。工具已新增 weekday 字段，模型输出仍需核对。具体记录见 `docs/验证说明.md`。

`requirements.txt` 固定直接依赖。若需重建本次验证的全部依赖版本，可使用 `requirements-lock.txt`（Python 3.12 / Windows）。

## 8. 汇报与 Git 提交

双击 `presentation.html`，可离线打开。方向键/空格翻页，`N` 显示讲稿，`F` 全屏，也可用底部按钮。封面姓名、学号留空待填写，请直接编辑 HTML 中的“待填写”。详细演示脚本在 `docs/答辩与演示.md`。

本地目录已初始化 Git（压缩包不含 `.git`）。发布到 GitHub/Gitee 需使用你自己的账号创建仓库，未替你发布。首次提交前检查：

```powershell
# 解压包首次使用时执行；原交付目录已有 .git 则无需重复
git init
git add .
git status
# 确认没有 .env、data、数据库、.venv 和真实身份信息
git commit -m "Initial campus service agent"
# 在自己的 GitHub/Gitee 账号创建仓库后按平台提示添加 remote 并 push
```

提交：项目仓库链接、`presentation.html`，并按教师要求在课堂群交付。若有两位作者，请如实填写分工。项目没有发布动作，也没有代发消息。

## 9. 常见问题

| 现象 | 处理 |
| --- | --- |
| 提示缺少密钥 | 创建 `.env`，本地填写 Key，重启 |
| 401 / 鉴权失败 | 检查 Key 与百炼地域、接口是否匹配 |
| 模型不存在 | 使用账号实际开通模型；课程模型可能需要课程地址 |
| MCP 加载失败 | 检查依赖、`mcp_servers.json`，确保 Python 指向同一环境 |
| 界面显示无空闲空间 | 换时段或降低筛选要求，不能让模型伪造余位 |
| 写入工作区外被拒绝 | 正常权限行为，请输出到 `/workspace/` |
| 修改代码未生效 | 停止 Streamlit，再启动后台运行时 |
| 端口占用 | 启动命令追加 `--server.port 8502` |
| 周末/节假日与学校实际不一致 | 本项目只用虚构星期规则，不是实时学校日历 |
| 复杂任务很慢 | 先用单项查询确认接口，再运行计划；子代理可配更快的可用模型 |

## 10. 参考资料

- 用户提供的《Demo 5：LangChain Deep Agents 智能体》README
- 用户提供的《开源 AI 技术实践》期末考查要求，路径 A
- [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview)
- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [Agent Skills 规范](https://agentskills.io)
- [阿里百炼兼容接口](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)
