# 存储负责人

- 人员：待填写
- 本轮具体任务：待填写
- 基线提交号：待填写
- 首轮任务建议：设计持久化与按用户隔离的存储，和集成负责人确认身份传入方式。

允许修改：storage/、domain/conversation.py。还可以新增 tests/test_storage_*.py 和维护 deliveries/storage/。

验收方向：记录重启可恢复、并发不覆盖；用户隔离需与认证联调，不能只靠页面过滤。

先阅读 AGENTS.md、README.md 和 CONTRIBUTING.md。公共接口或范围之外的修改先交集成负责人协调。

完成后新建任务子目录，交 REPORT.md 和 changes.patch。没有提供的服务地址、协议、身份信息等不要猜测；在报告中记录依赖和待联调事项。
