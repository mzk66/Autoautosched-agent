from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field


class Job(BaseModel):
    id: str
    product: str
    quantity: float
    due_time: datetime
    priority: str | None = None
    customer_type: str | None = None


class Machine(BaseModel):
    id: str
    supported_products: list[str]
    rates: dict[str, float]
    daily_start: time
    daily_end: time
    daily_end_next_day: bool = False


class Maintenance(BaseModel):
    machine_id: str
    start_time: datetime
    end_time: datetime
    note: str | None = None


class ConstraintSpec(BaseModel):
    kind: Literal[
        "machine_compatibility",
        "no_overlap",
        "maintenance",
        "working_calendar",
        "complete_each_job",
    ]
    hard: bool = True


class ObjectiveSpec(BaseModel):
    kind: Literal[
        "weighted_tardiness",
        "makespan",
    ]
    priority: int


def default_constraints() -> list[ConstraintSpec]:
    return [
        ConstraintSpec(
            kind="machine_compatibility"
        ),
        ConstraintSpec(
            kind="no_overlap"
        ),
        ConstraintSpec(
            kind="maintenance"
        ),
        ConstraintSpec(
            kind="working_calendar"
        ),
        ConstraintSpec(
            kind="complete_each_job"
        ),
    ]


def default_objectives() -> list[ObjectiveSpec]:
    return [
        ObjectiveSpec(
            kind="weighted_tardiness",
            priority=1,
        ),
        ObjectiveSpec(
            kind="makespan",
            priority=2,
        ),
    ]


class SchedulingProblem(BaseModel):
    jobs: list[Job]
    machines: list[Machine]
    maintenance: list[Maintenance]
    constraints: list[ConstraintSpec] = Field(
        default_factory=default_constraints
    )
    objectives: list[ObjectiveSpec] = Field(
        default_factory=default_objectives
    )
    assumptions: list[str] = Field(
        default_factory=list
    )
    unresolved: list[str] = Field(
        default_factory=list
    )


class ScheduleItem(BaseModel):
    job: str
    product: str
    priority: str | None = None
    customer_type: str | None = None
    machine: str
    start_min: int
    end_min: int
    start_time: datetime
    end_time: datetime
    due_time: datetime
    duration_min: int
    tardiness_min: int
    weight: int
    weighted_tardiness: int


class SolveResult(BaseModel):
    status: str
    planning_start: datetime | None = None
    makespan_min: int | None = None
    objective_value: int | None = None
    total_weighted_tardiness: int | None = None
    late_job_count: int | None = None
    vip_ontime_rate: float | None = None
    schedule: list[ScheduleItem] = Field(
        default_factory=list
    )
