from pydantic import ValidationError

from domain.schema import (
    Job,
    Machine,
    Maintenance,
    SchedulingProblem,
)
from domain.workflow_schema import (
    DataIssue,
    ParsedSchedulingData,
    ProblemBuildResult,
    ValidationReport,
)


def _deduplicate_issues(
    issues: list[DataIssue],
) -> list[DataIssue]:
    seen = set()
    result = []

    for issue in issues:
        key = (
            issue.code,
            issue.message,
            issue.source,
            issue.field,
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(issue)

    return result


def _prebuild_report(
    parsed: ParsedSchedulingData,
) -> ValidationReport:
    report = ValidationReport(
        unresolved=list(
            parsed.unresolved_issues
        )
    )

    for mapping in parsed.inferred_mappings:
        if mapping.blocking and not mapping.applied:
            report.unresolved.append(
                DataIssue(
                    code="unconfirmed_mapping",
                    message=(
                        f"请确认 {mapping.field}: "
                        f"{mapping.source_value} 是否应映射为 "
                        f"{mapping.proposed_value}。"
                    ),
                    source=mapping.source,
                    field=mapping.field,
                )
            )

    if not parsed.jobs:
        report.errors.append(
            DataIssue(
                code="no_jobs",
                message="没有识别到订单数据。",
                field="jobs",
            )
        )

    if not parsed.machines:
        report.errors.append(
            DataIssue(
                code="no_machines",
                message="没有识别到设备数据。",
                field="machines",
            )
        )

    job_ids = [
        item.id
        for item in parsed.jobs
        if item.id is not None
    ]

    if len(job_ids) != len(set(job_ids)):
        report.errors.append(
            DataIssue(
                code="duplicate_job_id",
                message="多个来源中存在重复订单 ID，请确认应使用哪一份数据。",
                field="jobs",
            )
        )

    machine_ids = [
        item.id
        for item in parsed.machines
        if item.id is not None
    ]

    if len(machine_ids) != len(set(machine_ids)):
        report.errors.append(
            DataIssue(
                code="duplicate_machine_id",
                message="多个来源中存在重复设备 ID，请确认应使用哪一份数据。",
                field="machines",
            )
        )

    exact_machine_ids = set(machine_ids)

    for item in parsed.maintenance:
        if (
            item.machine_id is not None
            and item.machine_id not in exact_machine_ids
        ):
            report.errors.append(
                DataIssue(
                    code="unknown_maintenance_machine",
                    message=(
                        f"检修记录引用了未知设备 {item.machine_id}。"
                    ),
                    source=item.source,
                    field="maintenance.machine_id",
                )
            )

    report.errors = _deduplicate_issues(
        report.errors
    )
    report.unresolved = _deduplicate_issues(
        report.unresolved
    )
    return report


def build_problem_ir(
    parsed: ParsedSchedulingData,
) -> ProblemBuildResult:
    report = _prebuild_report(parsed)

    if not report.can_solve:
        return ProblemBuildResult(
            validation=report
        )

    try:
        problem = SchedulingProblem(
            jobs=[
                Job(
                    id=item.id,
                    product=item.product,
                    quantity=item.quantity,
                    due_time=item.due_time,
                    priority=item.priority,
                    customer_type=item.customer_type,
                )
                for item in parsed.jobs
            ],
            machines=[
                Machine(
                    id=item.id,
                    supported_products=(
                        item.supported_products
                    ),
                    rates=item.rates,
                    daily_start=item.daily_start,
                    daily_end=item.daily_end,
                    daily_end_next_day=(
                        item.daily_end_next_day
                    ),
                )
                for item in parsed.machines
            ],
            maintenance=[
                Maintenance(
                    machine_id=item.machine_id,
                    start_time=item.start_time,
                    end_time=item.end_time,
                    note=item.note,
                )
                for item in parsed.maintenance
            ],
            assumptions=parsed.assumptions,
        )
    except ValidationError as exc:
        report.errors.append(
            DataIssue(
                code="ir_schema_error",
                message=(
                    "无法构建 SchedulingProblem："
                    f"{exc.errors(include_url=False)}"
                ),
                field="problem_ir",
            )
        )
        return ProblemBuildResult(
            validation=report
        )

    return ProblemBuildResult(
        problem=problem,
        validation=report,
    )
