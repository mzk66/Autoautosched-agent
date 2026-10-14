# 模型负责人

- 人员：待填写
- 本轮具体任务：待填写
- 基线提交号：待填写
- 首轮任务建议：接外部模型 API，完善错误反馈，保持聊天输出边界。

允许修改：agent/llm/、agent/chat.py、agent/prompts.py、agent/extractor.py、agent/routing.py。还可以新增 tests/test_model_*.py 和维护 deliveries/model/。

验收方向：真实服务可聊天；配置不泄露；调用失败可解释；不伪造排程。

先阅读 AGENTS.md、README.md 和 CONTRIBUTING.md。公共接口或范围之外的修改先交集成负责人协调。

完成后新建任务子目录，交 REPORT.md 和 changes.patch。没有提供的服务地址、协议、身份信息等不要猜测；在报告中记录依赖和待联调事项。
