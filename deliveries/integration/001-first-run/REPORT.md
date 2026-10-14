# 修改报告

- 角色：integration（本次仓库维护）
- 任务：首次启动不依赖本地模型；状态：已验证
- 基线提交号：c8e6ef591d5c8f98bf1e389e3828b109738c2eaa
- 源码提交号：680562de58235f40405e5147757d65c47d51c5f5
- 完成内容：未配置时默认 mock，页面明确提示演示模式；可执行本地排程，不提供真实 AI 理解。
- 修改文件：README.md、agent/llm/factory.py、agent/llm/mock.py、web/settings.py；新增 tests/test_integration_first_run.py。
- 验证：autosched 环境执行 python -m pytest -q，25 项通过。新增测试在无 .env 且禁止模型 HTTP 请求的条件下验证页面、聊天提示及求解复核；未验证全新环境安装，未调用真实模型 API。
- 待配合：真实模型 API 和在线网站仍需后续接入。
- 集成结果：本地已接入，随当前分支推送。
