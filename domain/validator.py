from domain.schema import SchedulingProblem
from domain.workflow_schema import (
    DataIssue,
    ValidationReport,
)


REQUIRED_CONSTRAINTS = {
    "machine_compatibility",
    "no_overlap",
    "maintenance",
    "working_calendar",
    "complete_each_job",
}
REQUIRED_OBJECTIVES = {
    "weighted_tardiness",
    "makespan",
}


def validate_problem_report(
    problem: SchedulingProblem,
) -> ValidationReport:
    report = ValidationReport()

    def error(
        code: str,
        message: str,
        field: str | None = None,
    ):
        report.errors.append(
            DataIssue(
                code=code,
                message=message,
                field=field,
            )
        )

    if not problem.jobs:
        error(
            "no_jobs",
            "SchedulingProblem 中没有订单。",
            "jobs",
        )

    if not problem.machines:
        error(
            "no_machines",
            "SchedulingProblem 中没有设备。",
            "machines",
        )

    job_ids = [job.id for job in problem.jobs]

    if len(job_ids) != len(set(job_ids)):
        error(
            "duplicate_job_id",
            "存在重复订单 ID。",
            "jobs",
        )

    machine_ids = [
        machine.id
        for machine in problem.machines
    ]

    if len(machine_ids) != len(set(machine_ids)):
        error(
            "duplicate_machine_id",
            "存在重复设备 ID。",
            "machines",
        )

    machine_id_set = set(machine_ids)

    for job in problem.jobs:
        if job.quantity <= 0:
            error(
                "invalid_quantity",
                f"订单 {job.id} 的数量必须大于 0。",
                f"jobs.{job.id}.quantity",
            )

        if job.priority not in {
            "high",
            "normal",
        }:
            error(
                "invalid_priority",
                f"订单 {job.id} 的 priority 必须明确为 high 或 normal。",
                f"jobs.{job.id}.priority",
            )

        if job.customer_type not in {
            "VIP",
            "normal",
        }:
            error(
                "invalid_customer_type",
                f"订单 {job.id} 的 customer_type 必须明确为 VIP 或 normal。",
                f"jobs.{job.id}.customer_type",
            )

        compatible = [
            machine
            for machine in problem.machines
            if (
                job.product in machine.supported_products
                and job.product in machine.rates
                and machine.rates[job.product] > 0
            )
        ]

        if not compatible:
            error(
                "no_compatible_machine",
                (
                    f"订单 {job.id} 的产品 {job.product} "
                    "没有具备有效产能的兼容设备。"
                ),
                f"jobs.{job.id}.product",
            )

    for machine in problem.machines:
        if not machine.supported_products:
            error(
                "empty_supported_products",
                f"设备 {machine.id} 没有可加工产品。",
                f"machines.{machine.id}.supported_products",
            )

        for product in machine.supported_products:
            if product not in machine.rates:
                error(
                    "missing_rate",
                    f"设备 {machine.id} 支持 {product}，但缺少产能。",
                    f"machines.{machine.id}.rates.{product}",
                )
            elif machine.rates[product] <= 0:
                error(
                    "invalid_rate",
                    f"设备 {machine.id} 的 {product} 产能必须大于 0。",
                    f"machines.{machine.id}.rates.{product}",
                )

        if (
            not machine.daily_end_next_day
            and machine.daily_start >= machine.daily_end
        ):
            error(
                "invalid_working_hours",
                f"设备 {machine.id} 的工作时间无效。",
                f"machines.{machine.id}.working_calendar",
            )

    for maintenance in problem.maintenance:
        if maintenance.machine_id not in machine_id_set:
            error(
                "unknown_maintenance_machine",
                (
                    "检修窗口引用了未知设备："
                    f"{maintenance.machine_id}。"
                ),
                "maintenance.machine_id",
            )

        if maintenance.start_time >= maintenance.end_time:
            error(
                "invalid_maintenance_window",
                (
                    f"设备 {maintenance.machine_id} 的检修窗口 "
                    "开始时间必须早于结束时间。"
                ),
                "maintenance",
            )

    constraint_kinds = {
        item.kind
        for item in problem.constraints
        if item.hard
    }
    missing_constraints = (
        REQUIRED_CONSTRAINTS
        - constraint_kinds
    )

    if missing_constraints:
        error(
            "missing_mandatory_constraints",
            (
                "缺少当前 Solver 必需约束："
                + ", ".join(
                    sorted(missing_constraints)
                )
            ),
            "constraints",
        )

    objective_kinds = {
        item.kind
        for item in problem.objectives
    }

    if objective_kinds != REQUIRED_OBJECTIVES:
        error(
            "unsupported_objectives",
            (
                "当前 Solver 仅支持 weighted_tardiness "
                "和 makespan 目标组合。"
            ),
            "objectives",
        )

    for item in problem.unresolved:
        report.unresolved.append(
            DataIssue(
                code="problem_unresolved",
                message=item,
                field="unresolved",
            )
        )

    return report


def validate_problem(
    problem: SchedulingProblem,
) -> list[str]:
    report = validate_problem_report(
        problem
    )
    return [
        issue.message
        for issue in report.blocking_issues
    ]


if __name__ == "__main__":
    from domain.parser import load_problem

    problem = load_problem(
        "data/autosched_demo.xlsx"
    )
    errors = validate_problem(problem)

    if errors:
        print("Validation failed:")

        for item in errors:
            print("-", item)
    else:
        print("Validation passed.")
