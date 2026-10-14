"""排程流程：检查、标准化、校验、求解、复核。"""

from collections.abc import Callable

from agent import tools
from agent.routing import classify_scheduling_action, enforce_llm_boundary
from agent.reporting import (
    build_task_context, format_inspection_result, format_blocked_result, format_solver_result,
)
from domain.input_bundle import InputFile
from domain.workflow_schema import ValidationReport, WorkflowResult

SOLVED_STATUSES = {"OPTIMAL", "FEASIBLE"}


def _merge_validation(
    base: ValidationReport,
    extra: ValidationReport,
) -> ValidationReport:
    """合并问题构建和问题校验两个阶段的报告，保留各自的问题顺序。

    三类列表分别拼接，不去重，也不修改传入报告。
    是否阻塞求解由 ValidationReport 决定：所有 errors，以及 unresolved 中
    blocking=True 的项都会阻塞；warnings 本身不会阻塞。
    """
    return ValidationReport(
        errors=base.errors + extra.errors,
        warnings=base.warnings + extra.warnings,
        unresolved=(
            base.unresolved
            + extra.unresolved
        ),
    )



def run_scheduling_workflow(
    action: str,
    input_files: list[InputFile],
    solve_fn: Callable = tools.solve_schedule,
    scenario_version: int = 1,
) -> WorkflowResult:
    """执行一轮确定性的排程工作流，返回回复文本和完整的阶段数据。

    参数：
        action：约定传入 "inspect" 或 "solve"。当前实现仅显式区分 "inspect"，
            其他值均进入求解分支，因此调用方应先使用意图分类或自行校验动作。
        input_files：输入读取层生成的文件对象，内含表格记录、文本摘录及读取错误。
        solve_fn：接收 SchedulingProblem 并返回 SolveResult 的可调用对象；
            默认使用正式求解工具，也允许测试注入替身以验证流程。
        scenario_version：由调用方管理的方案版本；本函数只传递它，不递增或保存历史。

    返回阶段：
        clarifying：仍需修正或澄清数据，本轮未求解。
        ready_for_confirmation：检查已完成且无阻塞项，等待用户发出求解请求。
        completed：求解已结束，可能得到通过复核的排程，也可能未返回可行解。
        failed：求解器声称返回可行解，但独立复核未通过，不在回复中发布排程表。

    本函数同步执行，不在求解中途返回 solving/verifying 阶段，也不捕获工具异常；
    异常由调用方处理。结构化返回值中的 solver_result 即使复核失败也会保留，
    展示时应遵守 verification_result，而不能把原始求解结果直接当作已验证方案。
    """
    # 1. 记录将调用的工具名称，并检查文件概况。
    # tool_calls 只追踪工作流层面的调用顺序，不记录工具内部调用、参数或执行状态。
    tool_calls = ["inspect_files"]
    inspection = tools.inspect_files(
        input_files
    )

    # 2. 从文件内容解析订单、设备、检修、目标与约束，同时保留来源和待确认信息。
    # inspection 是供展示的独立检查结果；解析器仍直接接收原始 input_files。
    tool_calls.append("parse_data")
    parsed = tools.parse_data(
        input_files
    )

    # 3. 将宽松的解析结果标准化为 SchedulingProblem，并收集构建阶段的校验问题。
    # IR 是中间表示；数据不足或无效时，build_result.problem 可能为 None。
    tool_calls.append("build_problem_ir")
    build_result = tools.build_problem_ir(
        parsed
    )
    validation = build_result.validation

    # 4. 只有成功构建问题对象后，才继续检查该对象的业务一致性和求解前置条件。
    # 将这一步的报告与构建报告合并，避免丢失任何阶段发现的问题。
    if build_result.problem is not None:
        tool_calls.append("validate_problem")
        validation = _merge_validation(
            validation,
            tools.validate_problem(
                build_result.problem
            ),
        )

    # 两种动作都生成同样的任务摘要；即使数据被阻塞，用户也能看到已理解的内容。
    task_context = build_task_context(
        parsed,
        validation,
    )

    # 5a. 检查动作到此结束：已经解析和校验，但不会调用 Solver 或 Verifier。
    # ready_for_confirmation 表示当前检查无阻塞项，界面会提示用户继续确认。
    if action == "inspect":
        stage = (
            "clarifying"
            if validation.blocking_issues
            else "ready_for_confirmation"
        )
        return WorkflowResult(
            action="inspect",
            stage=stage,
            scenario_version=scenario_version,
            response_text=format_inspection_result(
                task_context,
                validation,
            ),
            task_context=task_context,
            inspection=inspection,
            parsed_data=parsed,
            problem_ir=build_result.problem,
            validation_report=validation,
            tool_calls=tool_calls,
        )

    # 5b. 求解入口同时要求“有问题对象”和“报告允许求解”，任一不满足都提前返回。
    # warnings 不会令 can_solve 变成 False；阻塞依据由 ValidationReport 统一定义。
    if (
        build_result.problem is None
        or not validation.can_solve
    ):
        return WorkflowResult(
            action="solve",
            stage="clarifying",
            scenario_version=scenario_version,
            response_text=format_blocked_result(
                validation
            ),
            task_context=task_context,
            inspection=inspection,
            parsed_data=parsed,
            problem_ir=build_result.problem,
            validation_report=validation,
            tool_calls=tool_calls,
        )

    # 6. 通过前置校验后执行注入的求解函数。即使使用测试替身，日志仍记录标准工具名。
    tool_calls.append("solve_schedule")
    solver_result = solve_fn(
        build_result.problem
    )

    # 7. 以原问题独立复核 Solver 输出，检查订单完成、设备兼容、工时、重叠和 KPI 等。
    # 此调用发生在状态分支之前；未返回可行解时也会调用 Verifier，得到未通过报告。
    tool_calls.append("verify_solution")
    verification = tools.verify_solution(
        build_result.problem,
        solver_result,
    )

    # 8. 优先根据 Solver 状态决定回复。
    # 未返回可行解时，本轮求解仍已结束，阶段为 completed；这不代表已证明问题无解。
    if solver_result.status not in SOLVED_STATUSES:
        stage = "completed"
        response_text = "\n".join(
            [
                f"方案 V{scenario_version} 求解结束。",
                "",
                f"Solver status: {solver_result.status}",
                "Verification: 没有可行排程可供验证",
                "",
                "Solver 未返回排程表。该状态直接来自 Solver。",
            ]
        )
    elif verification.passed:
        # 只有“状态可行 + 独立复核通过”同时成立时，才生成包含排程表的成功回复。
        stage = "completed"
        response_text = format_solver_result(
            solver_result,
            scenario_version=scenario_version,
        )
    else:
        # 求解器返回可行状态，但明细或指标未通过复核：说明错误并停止发布排程表。
        stage = "failed"
        response_text = "\n".join(
            [
                "Solver 已返回结果，但 Verification 未通过。",
                "",
                *[
                    f"- {error}"
                    for error in verification.errors
                ],
                "",
                "为避免展示未经验证的排程，本轮未发布排程表。",
            ]
        )

    # 9. 一并返回中间产物和最终报告，便于界面调试、审阅及由调用方维护方案历史。
    # 复核失败时仍保留 solver_result 作为诊断依据，不代表它已经获准展示为有效方案。
    return WorkflowResult(
        action="solve",
        stage=stage,
        scenario_version=scenario_version,
        response_text=response_text,
        task_context=task_context,
        inspection=inspection,
        parsed_data=parsed,
        problem_ir=build_result.problem,
        validation_report=validation,
        tool_calls=tool_calls,
        solver_result=solver_result,
        verification_result=verification,
    )
