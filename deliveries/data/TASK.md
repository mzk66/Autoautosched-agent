# 数据与排程负责人

- 人员：待填写
- 本轮具体任务：待填写
- 基线提交号：待填写
- 首轮任务建议：维护共同样例，补齐输入校验和外部排程结果复核。

允许修改：domain/parsing/、domain/input_reader.py、domain/normalizer.py、domain/validator.py、domain/verifier.py、solver/、evals/cases/、agent/toolsets/data.py、agent/toolsets/validation.py。还可以新增 tests/test_data_*.py 和维护 deliveries/data/。

验收方向：坏数据阻止求解；正常数据完成本地对照；外部约束有对应复核或明确标记未覆盖。

先阅读 AGENTS.md、README.md 和 CONTRIBUTING.md。公共接口或范围之外的修改先交集成负责人协调。

完成后新建任务子目录，交 REPORT.md 和 changes.patch。没有提供的服务地址、协议、身份信息等不要猜测；在报告中记录依赖和待联调事项。
