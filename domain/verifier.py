import math
from datetime import datetime, timedelta

from domain.schema import (
    Machine,
    SchedulingProblem,
    SolveResult,
)
from domain.workflow_schema import VerificationReport
from solver.model_builder import get_job_weight


SOLVED_STATUSES = {
    "OPTIMAL",
    "FEASIBLE",
}


def _overlaps(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
) -> bool:
    return start_a < end_b and start_b < end_a


def _within_working_calendar(
    machine: Machine,
    start_time: datetime,
    end_time: datetime,
) -> bool:
    candidate_dates = {
        start_time.date(),
        start_time.date() - timedelta(days=1),
    }

    for current_date in candidate_dates:
        work_start = datetime.combine(
            current_date,
            machine.daily_start,
        )
        work_end = datetime.combine(
            current_date,
            machine.daily_end,
        )

        if machine.daily_end_next_day:
            work_end += timedelta(days=1)

        if (
            start_time >= work_start
            and end_time <= work_end
        ):
            return True

    return False


def verify_solution(
    problem: SchedulingProblem,
    result: SolveResult,
) -> VerificationReport:
    errors = []
    checks = [
        "solver_status",
        "completion_requirements",
        "machine_compatibility",
        "processing_duration",
        "no_overlap",
        "maintenance",
        "working_calendar",
        "kpi_consistency",
    ]

    if result.status not in SOLVED_STATUSES:
        return VerificationReport(
            passed=False,
            errors=[
                "Solver 未返回可验证的可行排程。"
            ],
            checks=checks,
        )

    jobs = {
        job.id: job
        for job in problem.jobs
    }
    machines = {
        machine.id: machine
        for machine in problem.machines
    }
    tasks_by_job = {}
    tasks_by_machine = {}

    for task in result.schedule:
        tasks_by_job.setdefault(
            task.job,
            [],
        ).append(task)
        tasks_by_machine.setdefault(
            task.machine,
            [],
        ).append(task)

        job = jobs.get(task.job)
        machine = machines.get(task.machine)

        if job is None:
            errors.append(
                f"结果包含未知订单 {task.job}。"
            )
            continue

        if machine is None:
            errors.append(
                f"订单 {task.job} 被分配到未知设备 {task.machine}。"
            )
            continue

        if (
            job.product not in machine.supported_products
            or job.product not in machine.rates
        ):
            errors.append(
                f"订单 {task.job} 与设备 {task.machine} 不兼容。"
            )
            continue

        expected_duration = math.ceil(
            job.quantity
            / machine.rates[job.product]
            * 60
        )

        if task.duration_min != expected_duration:
            errors.append(
                f"订单 {task.job} 的 duration_min 与产能不一致。"
            )

        actual_duration = int(
            (
                task.end_time
                - task.start_time
            ).total_seconds()
            / 60
        )

        if (
            task.end_min - task.start_min
            != task.duration_min
            or actual_duration != task.duration_min
        ):
            errors.append(
                f"订单 {task.job} 的开始、结束和时长不一致。"
            )

        expected_tardiness = max(
            0,
            int(
                (
                    task.end_time
                    - job.due_time
                ).total_seconds()
                / 60
            ),
        )

        if task.tardiness_min != expected_tardiness:
            errors.append(
                f"订单 {task.job} 的 tardiness 不一致。"
            )

        if task.weight != get_job_weight(job):
            errors.append(
                f"订单 {task.job} 的权重不一致。"
            )

        if (
            task.weighted_tardiness
            != task.tardiness_min * task.weight
        ):
            errors.append(
                f"订单 {task.job} 的 weighted_tardiness 不一致。"
            )

        if not _within_working_calendar(
            machine,
            task.start_time,
            task.end_time,
        ):
            errors.append(
                f"订单 {task.job} 超出设备 {task.machine} 的工作日历。"
            )

        for maintenance in problem.maintenance:
            if (
                maintenance.machine_id == task.machine
                and _overlaps(
                    task.start_time,
                    task.end_time,
                    maintenance.start_time,
                    maintenance.end_time,
                )
            ):
                errors.append(
                    f"订单 {task.job} 与设备 {task.machine} 的检修窗口重叠。"
                )

    for job_id in jobs:
        count = len(
            tasks_by_job.get(job_id, [])
        )

        if count != 1:
            errors.append(
                f"订单 {job_id} 的排程记录数量为 {count}，应为 1。"
            )

    for machine_id, tasks in tasks_by_machine.items():
        sorted_tasks = sorted(
            tasks,
            key=lambda item: item.start_time,
        )

        for previous, current in zip(
            sorted_tasks,
            sorted_tasks[1:],
        ):
            if previous.end_time > current.start_time:
                errors.append(
                    f"设备 {machine_id} 上的订单 {previous.job} 与 {current.job} 重叠。"
                )

    weighted_tardiness = sum(
        task.weighted_tardiness
        for task in result.schedule
    )
    late_job_count = sum(
        task.tardiness_min > 0
        for task in result.schedule
    )
    vip_tasks = [
        task
        for task in result.schedule
        if task.customer_type == "VIP"
    ]
    vip_ontime_rate = (
        sum(
            task.tardiness_min == 0
            for task in vip_tasks
        )
        / len(vip_tasks)
        if vip_tasks
        else 1.0
    )

    if (
        result.total_weighted_tardiness
        != weighted_tardiness
    ):
        errors.append(
            "total_weighted_tardiness 与排程明细不一致。"
        )

    if result.late_job_count != late_job_count:
        errors.append(
            "late_job_count 与排程明细不一致。"
        )

    if (
        result.vip_ontime_rate is None
        or not math.isclose(
            result.vip_ontime_rate,
            vip_ontime_rate,
        )
    ):
        errors.append(
            "vip_ontime_rate 与排程明细不一致。"
        )

    if result.schedule:
        makespan = max(
            task.end_min
            for task in result.schedule
        )

        if result.makespan_min != makespan:
            errors.append(
                "makespan_min 与排程明细不一致。"
            )

    expected_objective = (
        weighted_tardiness * 1000
        + (result.makespan_min or 0)
    )

    if result.objective_value != expected_objective:
        errors.append(
            "objective_value 与 Solver 目标定义不一致。"
        )

    return VerificationReport(
        passed=not errors,
        errors=errors,
        checks=checks,
    )
