from domain.schema import SolveResult
from domain.workflow_schema import DataIssue, ParsedSchedulingData, TaskContext, ValidationReport


def _numbered_issues(
    issues: list[DataIssue],
) -> str:
    """将问题按原顺序转成从 1 开始的编号列表；空列表返回空字符串。

    展示时只使用面向用户的 message，code、source、field 等元数据仍保留在报告中。
    """
    return "\n".join(
        f"{index}. {issue.message}"
        for index, issue in enumerate(
            issues,
            start=1,
        )
    )



def build_task_context(
    parsed: ParsedSchedulingData,
    validation: ValidationReport,
) -> TaskContext:
    """从解析数据和校验报告构造用于展示的任务上下文。

    汇总数据规模、目标、约束以及信息来源，让用户在求解前确认任务理解。
    此处的目标和约束是说明文本，不会在这里修改问题模型或求解器的数学约束。
    """
    # 优先展示源数据声明的目标；未提供目标时，展示系统的默认优化目标描述。
    source_goals = [
        rule.description
        for rule in parsed.objectives
    ]
    goals = source_goals or [
        "最小化加权延期",
        "在延期目标之后最小化完工时间",
    ]
    source_constraints = [
        rule.description
        for rule in parsed.constraints
    ]
    # 合并基础约束与源文件中的约束描述，按文本去重并保留首次出现的顺序。
    # 这里直接汇总 parsed.constraints，不再按规则的 hard 或 supported 属性筛选。
    hard_constraints = list(
        dict.fromkeys(
            [
                "订单必须且只能分配到一台兼容设备",
                "同一设备上的生产、检修和停机时间不得重叠",
                "生产必须位于设备工作日历内",
                *source_constraints,
            ]
        )
    )

    return TaskContext(
        data_summary={
            "jobs": len(parsed.jobs),
            "machines": len(parsed.machines),
            "maintenance": len(parsed.maintenance),
            "constraints": len(parsed.constraints),
            "objectives": len(parsed.objectives),
        },
        goals=goals,
        hard_constraints=hard_constraints,
        expected_outputs=[
            "可导出的排程明细",
            "关键 KPI 汇总",
            "约束校验结果",
        ],
        # 分开保留源事实、推断映射和假设，方便界面说明每条信息的依据。
        # 这些内容仅传递给上下文，不会在此自动接受推断或补全缺失数据。
        source_facts=parsed.source_facts,
        inferred_mappings=parsed.inferred_mappings,
        assumptions=parsed.assumptions,
        # 此字段承载的是全部阻塞项，既可能包含校验错误，也可能包含待澄清项。
        unresolved_issues=validation.blocking_issues,
    )



def format_inspection_result(
    context: TaskContext,
    validation: ValidationReport,
) -> str:
    """生成 inspect 分支的任务理解摘要，不执行求解。

    存在阻塞项时显示 CLARIFYING 并列出需澄清的问题；
    无阻塞项时显示 READY_FOR_CONFIRMATION，提示用户确认后再求解。
    这里的大写阶段用于展示，WorkflowResult.stage 使用对应的小写值。
    """
    issues = validation.blocking_issues
    summary = context.data_summary
    stage = (
        "CLARIFYING"
        if issues
        else "READY_FOR_CONFIRMATION"
    )
    lines = [
        "任务理解完成。",
        "",
        f"当前阶段：{stage}",
        "",
        "任务摘要：",
        f"- 业务场景：{context.business_scenario}",
        (
            "- 已读取："
            f"{summary.get('jobs', 0)} 个订单、"
            f"{summary.get('machines', 0)} 台设备、"
            f"{summary.get('maintenance', 0)} 个检修窗口"
        ),
        "",
        "优化目标：",
        *[f"- {goal}" for goal in context.goals],
        "",
        "硬约束：",
        *[
            f"- {constraint}"
            for constraint in context.hard_constraints
        ],
        "",
        "期望输出：",
        *[
            f"- {output}"
            for output in context.expected_outputs
        ],
        "",
        "信息分类：",
        f"- source_facts: {len(context.source_facts)} 条",
        (
            "- inferred_mappings: "
            f"{len(context.inferred_mappings)} 条"
        ),
        f"- assumptions: {len(context.assumptions)} 条",
        f"- unresolved_issues: {len(issues)} 条",
    ]

    # 警告和非阻塞的待确认项不会进入此列表，也不会阻止进入等待确认阶段。
    if issues:
        lines.extend(
            [
                "",
                f"需要澄清 {len(issues)} 项：",
                "",
                _numbered_issues(issues),
                "",
                "请修正源文件或逐项明确这些信息。",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "当前上下文已具备求解条件。",
                "请回复“确认并排程”进入 Solver。",
            ]
        )

    lines.extend(
        [
            "",
            "当前没有修改任何原始文件，也没有调用 Solver。",
        ]
    )
    return "\n".join(lines)



def format_blocked_result(
    validation: ValidationReport,
) -> str:
    """为求解前被拦截的请求生成澄清提示。

    调用方在问题构建失败或存在阻塞项时使用此提示，并提前结束本轮工具链。
    此处只渲染报告里的问题，不尝试自动修复数据或调用 Solver。
    """
    issues = validation.blocking_issues

    return "\n".join(
        [
            "当前阶段：CLARIFYING",
            "",
            f"在开始排程前，需要确认 {len(issues)} 项：",
            "",
            _numbered_issues(issues),
            "",
            "请修正源文件或逐项明确这些信息。本轮未调用 Solver。",
        ]
    )



def format_solver_result(
    result: SolveResult,
    scenario_version: int = 1,
) -> str:
    """将已通过复核的求解结果格式化为 KPI 摘要和 Markdown 排程表。

    参数：
        result：Solver 返回的结构化结果，时间、设备分配和 KPI 均直接取自其中。
        scenario_version：调用方指定的方案版本号，用于区分多轮排程。
    注意：
        本函数不自行复核，却会输出 Verification: PASSED；调用方必须先确认
        Solver 状态可行且 verification.passed 为真，再使用此格式化函数。
    """
    # makespan_min 表示相对计划起点的最终完工分钟数；
    # total_weighted_tardiness 是按订单权重累计的延期，objective_value 是目标函数值。
    lines = [
        f"方案 V{scenario_version} 排程完成。",
        "",
        "核心结果：",
        f"- Solver status: {result.status}",
        "- Verification: PASSED",
        f"- Objective value: {result.objective_value}",
        (
            "- Weighted tardiness: "
            f"{result.total_weighted_tardiness}"
        ),
        f"- Makespan: {result.makespan_min} min",
        f"- Late jobs: {result.late_job_count}",
        (
            # None 或 0 均显示为 0.0%；这是界面的显示兜底，不会修改原始指标。
            "- VIP on-time rate: "
            f"{(result.vip_ontime_rate or 0):.1%}"
        ),
        "",
        "排程明细：",
        "",
        "| 订单 | 机器 | 开始时间 | 结束时间 | 时长(min) | 延期(min) |",
        "|---|---|---|---|---:|---:|",
    ]

    # 保留求解器返回的明细顺序，将日期时间显示到分钟，不在展示层重新计算排程。
    for task in result.schedule:
        lines.append(
            "| "
            f"{task.job} | {task.machine} | "
            f"{task.start_time:%Y-%m-%d %H:%M} | "
            f"{task.end_time:%Y-%m-%d %H:%M} | "
            f"{task.duration_min} | {task.tardiness_min} |"
        )

    return "\n".join(lines)
