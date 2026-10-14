import math
from datetime import datetime, timedelta

from ortools.sat.python import cp_model

from domain.schema import SchedulingProblem


def get_job_weight(job) -> int:
    weight = 1

    if job.priority == "high":
        weight *= 2

    if job.customer_type == "VIP":
        weight *= 3

    return weight


def to_minute(dt: datetime, planning_start: datetime) -> int:
    return int(
        (dt - planning_start).total_seconds()
        / 60
    )


def get_work_end(
    machine,
    current_date,
) -> datetime:
    work_end = datetime.combine(
        current_date,
        machine.daily_end,
    )

    if machine.daily_end_next_day:
        work_end += timedelta(days=1)

    return work_end


def build_model(problem: SchedulingProblem):

    model = cp_model.CpModel()

    # =========================================================
    # 1. Planning start
    # =========================================================

    all_dates = [
        job.due_time.date()
        for job in problem.jobs
    ]

    all_dates += [
        m.start_time.date()
        for m in problem.maintenance
    ]

    start_date = min(all_dates)

    earliest_start = min(
        machine.daily_start
        for machine in problem.machines
    )

    planning_start = datetime.combine(
        start_date,
        earliest_start,
    )

    # =========================================================
    # 2. Horizon
    # =========================================================

    processing_buffer = 0

    for job in problem.jobs:

        durations = []

        for machine in problem.machines:

            if (
                job.product in machine.supported_products
                and job.product in machine.rates
            ):

                duration = math.ceil(
                    job.quantity
                    / machine.rates[job.product]
                    * 60
                )

                durations.append(duration)

        processing_buffer += max(durations)

    latest_events = [
        job.due_time
        for job in problem.jobs
    ]

    latest_events += [
        m.end_time
        for m in problem.maintenance
    ]

    latest_event = max(latest_events)

    event_offset = math.ceil(
        (
            latest_event - planning_start
        ).total_seconds()
        / 60
    )

    # 多留一点空间，避免排程跨几天后 horizon 不够
    horizon = (
        event_offset
        + processing_buffer
        + 3 * 24 * 60
    )

    horizon_end = (
        planning_start
        + timedelta(minutes=horizon)
    )

    # =========================================================
    # 3. Variables
    # =========================================================

    starts = {}
    ends = {}

    assignments = {}

    tardiness = {}
    weights = {}

    machine_intervals = {
        machine.id: []
        for machine in problem.machines
    }

    # =========================================================
    # 4. Working calendar
    #
    # 把非工作时间作为固定 interval 加入机器
    # =========================================================

    for machine in problem.machines:

        current_date = planning_start.date()

        while datetime.combine(
            current_date,
            machine.daily_start,
        ) < horizon_end:

            work_start = datetime.combine(
                current_date,
                machine.daily_start,
            )

            work_end = get_work_end(
                machine,
                current_date,
            )

            next_work_start = datetime.combine(
                current_date + timedelta(days=1),
                machine.daily_start,
            )

            # -------------------------------------------------
            # 如果该机器当天开始时间晚于整个 planning_start
            # 则 planning_start → daily_start 也是停机
            # -------------------------------------------------

            if current_date == planning_start.date():

                before_start = max(
                    0,
                    to_minute(
                        planning_start,
                        planning_start,
                    ),
                )

                before_end = to_minute(
                    work_start,
                    planning_start,
                )

                if before_end > before_start:

                    interval = model.new_interval_var(
                        before_start,
                        before_end - before_start,
                        before_end,
                        (
                            f"off_before_"
                            f"{machine.id}_"
                            f"{current_date}"
                        ),
                    )

                    machine_intervals[
                        machine.id
                    ].append(interval)

            # -------------------------------------------------
            # 每晚：
            #
            # daily_end → 次日 daily_start
            # -------------------------------------------------

            off_start = to_minute(
                work_end,
                planning_start,
            )

            off_end = to_minute(
                next_work_start,
                planning_start,
            )

            # 裁剪到 horizon
            off_start = max(
                0,
                off_start,
            )

            off_end = min(
                horizon,
                off_end,
            )

            if off_end > off_start:

                interval = model.new_interval_var(
                    off_start,
                    off_end - off_start,
                    off_end,
                    (
                        f"off_night_"
                        f"{machine.id}_"
                        f"{current_date}"
                    ),
                )

                machine_intervals[
                    machine.id
                ].append(interval)

            current_date += timedelta(
                days=1
            )

    # =========================================================
    # 5. Maintenance
    # =========================================================

    for maintenance in problem.maintenance:

        start_offset = to_minute(
            maintenance.start_time,
            planning_start,
        )

        end_offset = to_minute(
            maintenance.end_time,
            planning_start,
        )

        duration = (
            end_offset
            - start_offset
        )

        interval = model.new_interval_var(
            start_offset,
            duration,
            end_offset,
            (
                f"maintenance_"
                f"{maintenance.machine_id}_"
                f"{start_offset}"
            ),
        )

        machine_intervals[
            maintenance.machine_id
        ].append(interval)

    # =========================================================
    # 6. Jobs
    # =========================================================

    for job in problem.jobs:

        start = model.new_int_var(
            0,
            horizon,
            f"start_{job.id}",
        )

        end = model.new_int_var(
            0,
            horizon,
            f"end_{job.id}",
        )

        starts[job.id] = start
        ends[job.id] = end

        compatible_assignments = []

        # -----------------------------------------------------
        # Machine assignment
        # -----------------------------------------------------

        for machine in problem.machines:

            if job.product not in machine.supported_products:
                continue

            if job.product not in machine.rates:
                continue

            duration = math.ceil(
                job.quantity
                / machine.rates[job.product]
                * 60
            )

            assigned = model.new_bool_var(
                f"assign_{job.id}_{machine.id}"
            )

            assignments[
                (job.id, machine.id)
            ] = assigned

            compatible_assignments.append(
                assigned
            )

            model.add(
                end == start + duration
            ).only_enforce_if(
                assigned
            )

            interval = (
                model.new_optional_interval_var(
                    start,
                    duration,
                    end,
                    assigned,
                    (
                        f"interval_"
                        f"{job.id}_"
                        f"{machine.id}"
                    ),
                )
            )

            machine_intervals[
                machine.id
            ].append(interval)

        model.add_exactly_one(
            compatible_assignments
        )

        # =====================================================
        # 7. Tardiness
        # =====================================================

        due_min = to_minute(
            job.due_time,
            planning_start,
        )

        tardy = model.new_int_var(
            0,
            horizon,
            f"tardiness_{job.id}",
        )

        model.add(
            tardy >= end - due_min
        )

        tardiness[job.id] = tardy

        weights[job.id] = (
            get_job_weight(job)
        )

    # =========================================================
    # 8. NoOverlap
    #
    # production + maintenance + off-hours
    # 全部一起检查
    # =========================================================

    for machine_id, intervals \
            in machine_intervals.items():

        if intervals:

            model.add_no_overlap(
                intervals
            )

    # =========================================================
    # 9. Makespan
    # =========================================================

    makespan = model.new_int_var(
        0,
        horizon,
        "makespan",
    )

    model.add_max_equality(
        makespan,
        list(ends.values()),
    )

    # =========================================================
    # 10. Objective
    # =========================================================

    weighted_tardiness = sum(
        weights[job.id]
        * tardiness[job.id]
        for job in problem.jobs
    )

    model.minimize(
        weighted_tardiness * 1000
        + makespan
    )

    # =========================================================
    # 11. Artifacts
    # =========================================================

    artifacts = {
        "starts": starts,
        "ends": ends,
        "assignments": assignments,

        "tardiness": tardiness,
        "weights": weights,

        "makespan": makespan,

        "horizon": horizon,
        "planning_start": planning_start,
    }

    return model, artifacts
