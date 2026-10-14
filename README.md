# AutoSched Agent

自动排程助手：用户上传资料、提出需求，系统调用建模和求解工具，复核后展示结果，最终通过网站交付。

## 现在做什么

目前已有本地网页、文件读取、数据校验、本地求解和会话保存。

下一步依次完成：

1. 接外部大模型 API，以及 MCP 自动建模、排程求解接口。
2. 跑通“上传 → 确认需求 → 建模 → 求解 → 复核 → 展示”。
3. 完善交互和结果下载，增加登录、用户数据隔离，部署网站。

MCP 和多人登录尚未实现。第一轮先让一份共同样例跑通完整流程。

## 怎么运行

克隆仓库后，在根目录执行：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m streamlit run app.py
```

Windows PowerShell 激活用 `.venv\Scripts\Activate.ps1`，复制配置用 `Copy-Item .env.example .env`。

打开终端给出的网址。上传 `data/autosched_demo.xlsx`，先发送“检查数据”，再发送“开始排程”。默认 mock 不调用真实模型；接真实模型时填写 `.env` 中的 `LLM_*` 配置，或修改侧边栏设置。

测试：`python -m pytest -q`。依赖尚未锁定完整版本；缺少依赖时先确认安装和 Python 环境。

## 代码在哪里

| 位置 | 用途与核心文件 |
| --- | --- |
| `app.py` | 启动程序 |
| `web/` | 页面；`chat.py` 聊天，`files.py` 上传，`results.py` 结果，`conversations.py` 会话，`settings.py` 设置 |
| `storage/conversations.py` | 会话读写，后续接数据库 |
| `services/turns.py` | 处理一轮用户消息、调用流程、记录方案 |
| `agent/llm/`、`agent/chat.py` | 模型调用和聊天上下文；`prompts.py` 提示词，`extractor.py` 草稿抽取 |
| `agent/workflow.py` | 控制检查、求解和复核顺序；`routing.py` 判断意图，`reporting.py` 组织回复 |
| `agent/toolsets/` | 工具实现；`modeling.py` 建模，`solving.py` 求解，`data.py` 数据，`validation.py` 校验 |
| `domain/` | `schema.py` 公共数据结构，`parsing/` 按订单、设备、规则解析，`validator.py` 校验，`verifier.py` 复核，`conversation.py` 会话模型 |
| `solver/` | `model_builder.py` 本地建模，`solver.py` 本地求解 |
| `tests/`、`evals/cases/` | 自动测试和行为案例 |
| `data/`、`skills/scheduling/` | 演示样例、运行会话，以及排程规则说明 |
| `deliveries/` | 各负责人任务卡、代码补丁和修改报告 |

页面调用业务流程，流程调用工具，工具调用数据和求解模块。`agent/tools.py`、`domain/parser.py` 是统一导入入口，具体功能在子模块里修改。

排程必须由求解器生成并通过复核。目前会话共用本地 JSON 文件，上线前必须完成用户隔离。密钥和运行数据不上传。

## 怎么合作

看 [分工约定](CONTRIBUTING.md)，认领角色，让自己的 AI 读取 [AGENTS.md](AGENTS.md) 和对应任务卡。只改指定范围，完成后交代码补丁和报告，由集成负责人统一接入。
