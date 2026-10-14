from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field

from domain.schema import SchedulingProblem, SolveResult

TaskStage = Literal[
    "understanding",
    "clarifying",
    "ready_for_confirmation",
    "solving",
    "verifying",
    "completed",
    "failed",
]


class DataIssue(BaseModel):
    code: str
    message: str
    blocking: bool = True
    source: str | None = None
    field: str | None = None


class InferredMapping(BaseModel):
    field: str
    source_value: str
    proposed_value: str
    reason: str
    applied: bool = False
    blocking: bool = True
    source: str | None = None


class ParsedJob(BaseModel):
    source: str
    id: str | None = None
    product: str | None = None
    quantity: float | None = None
    due_time: datetime | None = None
    priority: str | None = None
    customer_type: str | None = None


class ParsedMachine(BaseModel):
    source: str
    id: str | None = None
    supported_products: list[str] = Field(
        default_factory=list
    )
    rates: dict[str, float] = Field(
        default_factory=dict
    )
    daily_start: time | None = None
    daily_end: time | None = None
    daily_end_next_day: bool = False


class ParsedMaintenance(BaseModel):
    source: str
    machine_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    note: str | None = None


class ParsedRule(BaseModel):
    source: str
    id: str | None = None
    rule_type: str | None = None
    description: str
    hard: bool | None = None
    supported: bool = False


class FileInspection(BaseModel):
    file_count: int = 0
    sheet_count: int = 0
    source_facts: list[str] = Field(
        default_factory=list
    )
    issues: list[DataIssue] = Field(
        default_factory=list
    )


class ParsedSchedulingData(BaseModel):
    jobs: list[ParsedJob] = Field(
        default_factory=list
    )
    machines: list[ParsedMachine] = Field(
        default_factory=list
    )
    maintenance: list[ParsedMaintenance] = Field(
        default_factory=list
    )
    constraints: list[ParsedRule] = Field(
        default_factory=list
    )
    objectives: list[ParsedRule] = Field(
        default_factory=list
    )
    source_facts: list[str] = Field(
        default_factory=list
    )
    inferred_mappings: list[InferredMapping] = Field(
        default_factory=list
    )
    assumptions: list[str] = Field(
        default_factory=list
    )
    unresolved_issues: list[DataIssue] = Field(
        default_factory=list
    )


class ValidationReport(BaseModel):
    errors: list[DataIssue] = Field(
        default_factory=list
    )
    warnings: list[DataIssue] = Field(
        default_factory=list
    )
    unresolved: list[DataIssue] = Field(
        default_factory=list
    )

    @property
    def blocking_issues(self) -> list[DataIssue]:
        return self.errors + [
            issue
            for issue in self.unresolved
            if issue.blocking
        ]

    @property
    def can_solve(self) -> bool:
        return not self.blocking_issues


class ProblemBuildResult(BaseModel):
    problem: SchedulingProblem | None = None
    validation: ValidationReport = Field(
        default_factory=ValidationReport
    )


class VerificationReport(BaseModel):
    passed: bool
    errors: list[str] = Field(
        default_factory=list
    )
    checks: list[str] = Field(
        default_factory=list
    )


class TaskContext(BaseModel):
    business_scenario: str = "单工序生产排程"
    data_summary: dict[str, int] = Field(
        default_factory=dict
    )
    goals: list[str] = Field(
        default_factory=list
    )
    hard_constraints: list[str] = Field(
        default_factory=list
    )
    expected_outputs: list[str] = Field(
        default_factory=list
    )
    source_facts: list[str] = Field(
        default_factory=list
    )
    inferred_mappings: list[InferredMapping] = Field(
        default_factory=list
    )
    assumptions: list[str] = Field(
        default_factory=list
    )
    unresolved_issues: list[DataIssue] = Field(
        default_factory=list
    )


class ScenarioRecord(BaseModel):
    version: int
    created_at: datetime = Field(
        default_factory=datetime.now
    )
    solver_status: str
    verification_passed: bool
    result: SolveResult


class WorkflowResult(BaseModel):
    action: Literal["inspect", "solve"]
    stage: TaskStage
    scenario_version: int = 1
    response_text: str
    task_context: TaskContext | None = None
    inspection: FileInspection | None = None
    parsed_data: ParsedSchedulingData | None = None
    problem_ir: SchedulingProblem | None = None
    validation_report: ValidationReport | None = None
    tool_calls: list[str] = Field(
        default_factory=list
    )
    solver_result: SolveResult | None = None
    verification_result: VerificationReport | None = None
