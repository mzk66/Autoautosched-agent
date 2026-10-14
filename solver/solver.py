from datetime import timedelta

from ortools.sat.python import cp_model

from domain.schema import (
    ScheduleItem,
    SchedulingProblem,
    SolveResult,
)
from domain.validator import validate_problem_report
from solver.model_builder import build_model


def solve_schedule(
    problem: SchedulingProblem,
) -> SolveResult:

    validation = validate_problem_report(
        problem
    )

    if not validation.can_solve:
        messages = "; ".join(
            issue.message
            for issue in validation.blocking_issues
        )
        raise ValueError(
            "SchedulingProblem validation failed: "
            + messages
        )

    # =========================================================
    # 1. Build
    # =========================================================

    model, artifacts = build_model(
        problem
    )

    # =========================================================
    # 2. Solve
    # =========================================================

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 10.0

    status = solver.solve(model)

    # =========================================================
    # 3. No solution
    # =========================================================

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):

        return SolveResult(
            status=solver.status_name(status),
        )

    # =========================================================
    # 4. Parse result
    # =========================================================

    schedule = []

    planning_start = artifacts[
        "planning_start"
    ]

    total_weighted_tardiness = 0

    for job in problem.jobs:

        selected_machine = None

        # 找机器
        for machine in problem.machines:

            key = (
                job.id,
                machine.id,
            )

            if key not in artifacts[
                "assignments"
            ]:
                continue

            assigned = artifacts[
                "assignments"
            ][key]

            if solver.value(
                assigned
            ):

                selected_machine = (
                    machine.id
                )

                break

        # 时间
        start_min = solver.value(
            artifacts[
                "starts"
            ][job.id]
        )

        end_min = solver.value(
            artifacts[
                "ends"
            ][job.id]
        )

        start_time = (
            planning_start
            + timedelta(
                minutes=start_min
            )
        )

        end_time = (
            planning_start
            + timedelta(
                minutes=end_min
            )
        )

        # 延期
        tardiness_min = solver.value(
            artifacts[
                "tardiness"
            ][job.id]
        )

        weight = artifacts[
            "weights"
        ][job.id]

        weighted_tardiness = (
            tardiness_min
            * weight
        )

        total_weighted_tardiness += (
            weighted_tardiness
        )

        if selected_machine is None:
            raise RuntimeError(
                f"Solver returned no machine for job {job.id}."
            )

        schedule.append(
            ScheduleItem(
                job=job.id,
                product=job.product,
                priority=job.priority,
                customer_type=job.customer_type,
                machine=selected_machine,
                start_min=start_min,
                end_min=end_min,
                start_time=start_time,
                end_time=end_time,
                due_time=job.due_time,
                duration_min=(
                    end_min - start_min
                ),
                tardiness_min=tardiness_min,
                weight=weight,
                weighted_tardiness=(
                    weighted_tardiness
                ),
            )
        )

    # =========================================================
    # 5. Sort
    # =========================================================

    schedule.sort(
        key=lambda x: (
            x.machine,
            x.start_min,
        )
    )

    # =========================================================
    # 6. KPI
    # =========================================================

    late_jobs = [
        task
        for task in schedule
        if task.tardiness_min > 0
    ]

    vip_jobs = [
        task
        for task in schedule
        if task.customer_type == "VIP"
    ]

    vip_on_time = [
        task
        for task in vip_jobs
        if task.tardiness_min == 0
    ]

    vip_ontime_rate = (
        len(vip_on_time)
        / len(vip_jobs)
        if vip_jobs
        else 1.0
    )

    # =========================================================
    # 7. Result
    # =========================================================

    makespan_min = solver.value(
        artifacts["makespan"]
    )

    return SolveResult(
        status=solver.status_name(status),
        planning_start=planning_start,
        makespan_min=makespan_min,
        objective_value=(
            total_weighted_tardiness * 1000
            + makespan_min
        ),
        total_weighted_tardiness=(
            total_weighted_tardiness
        ),
        late_job_count=len(late_jobs),
        vip_ontime_rate=vip_ontime_rate,
        schedule=schedule,
    )


# =============================================================
# CLI test
# =============================================================

if __name__ == "__main__":

    from domain.parser import (
        load_problem,
    )

    from domain.validator import (
        validate_problem,
    )

    problem = load_problem(
        "data/autosched_demo.xlsx"
    )

    errors = validate_problem(
        problem
    )

    if errors:

        print(
            "\nValidation failed:"
        )

        for error in errors:
            print("-", error)

        raise SystemExit(1)

    result = solve_schedule(
        problem
    )

    print(
        "\nStatus:",
        result.status,
    )

    if not result.schedule:
        raise SystemExit(0)

    print(
        "Planning start:",
        result.planning_start,
    )

    print(
        "Makespan:",
        result.makespan_min,
        "minutes",
    )

    print(
        "Weighted tardiness:",
        result.total_weighted_tardiness,
    )

    print(
        "Late jobs:",
        result.late_job_count,
    )

    print(
        "VIP on-time rate:",
        f"{result.vip_ontime_rate:.0%}",
    )

    print(
        "\nSchedule:\n"
    )

    for task in result.schedule:

        late_text = ""

        if task.tardiness_min > 0:

            late_text = (
                f" | LATE "
                f"{task.tardiness_min} min"
                f" × {task.weight}"
            )

        print(
            f"{task.job:>3} | "
            f"{task.product} | "
            f"{task.machine} | "
            f"{task.start_time} "
            f"→ {task.end_time} | "
            f"Due: {task.due_time}"
            f"{late_text}"
        )
