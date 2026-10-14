from datetime import datetime, time
import json
from pathlib import Path

import pytest

from agent import tools
from agent.workflow import (
    format_solver_result,
    run_scheduling_workflow,
)
from domain.conversation import Conversation
from domain.input_bundle import (
    InputFile,
    SheetPreview,
)
from domain.input_reader import (
    build_excel_input_file,
)
from domain.schema import (
    Job,
    Machine,
    Maintenance,
    SchedulingProblem,
)
from domain.workflow_schema import ScenarioRecord
from domain.validator import (
    validate_problem_report,
)


def make_input_file(
    due_time="2026-09-22 18:00:00",
) -> InputFile:
    order_row = {
        "order_id": "O01",
        "product": "A",
        "quantity": 120,
        "due_time": due_time,
        "priority": "normal",
        "customer_type": "normal",
    }
    machine_row = {
        "machine_id": "M1",
        "supported_products": "A",
        "rate_A": 30,
        "daily_start": "08:00",
        "daily_end": "20:00",
    }

    return InputFile(
        name="case.xlsx",
        file_type="xlsx",
        size_bytes=100,
        sheets=[
            SheetPreview(
                name="Orders",
                columns=list(order_row),
                row_count=1,
                records=[order_row],
            ),
            SheetPreview(
                name="Machines",
                columns=list(machine_row),
                row_count=1,
                records=[machine_row],
            ),
        ],
    )


def test_missing_due_time_never_calls_solver():
    calls = []

    def forbidden_solver(problem):
        calls.append(problem)
        raise AssertionError(
            "Solver must not be called."
        )

    result = run_scheduling_workflow(
        action="solve",
        input_files=[
            make_input_file(due_time=None)
        ],
        solve_fn=forbidden_solver,
    )

    assert calls == []
    assert "solve_schedule" not in result.tool_calls
    assert result.solver_result is None
    assert "due_time" in result.response_text


def test_unknown_maintenance_machine_is_rejected():
    problem = SchedulingProblem(
        jobs=[
            Job(
                id="O01",
                product="A",
                quantity=120,
                due_time=datetime(
                    2026,
                    9,
                    22,
                    18,
                ),
                priority="normal",
                customer_type="normal",
            )
        ],
        machines=[
            Machine(
                id="M1",
                supported_products=["A"],
                rates={"A": 30},
                daily_start=time(8),
                daily_end=time(20),
            )
        ],
        maintenance=[
            Maintenance(
                machine_id="M404",
                start_time=datetime(
                    2026,
                    9,
                    22,
                    10,
                ),
                end_time=datetime(
                    2026,
                    9,
                    22,
                    11,
                ),
            )
        ],
    )

    report = validate_problem_report(
        problem
    )

    assert report.can_solve is False
    assert any(
        issue.code
        == "unknown_maintenance_machine"
        for issue in report.errors
    )

    with pytest.raises(ValueError):
        tools.solve_schedule(problem)


def test_normal_data_parse_validate_solve_verify():
    content = open(
        "data/autosched_demo.xlsx",
        "rb",
    ).read()
    input_file = build_excel_input_file(
        name="autosched_demo.xlsx",
        file_type="xlsx",
        content=content,
        max_rows_per_sheet=30,
    )

    parsed = tools.parse_data([input_file])
    built = tools.build_problem_ir(parsed)

    assert built.problem is not None

    validation = tools.validate_problem(
        built.problem
    )
    assert validation.can_solve is True

    result = tools.solve_schedule(
        built.problem
    )
    verification = tools.verify_solution(
        built.problem,
        result,
    )

    assert result.status in {
        "OPTIMAL",
        "FEASIBLE",
    }
    assert len(result.schedule) == len(
        built.problem.jobs
    )
    assert verification.passed is True


def test_schedule_text_contains_only_solve_result_rows():
    workflow = run_scheduling_workflow(
        action="solve",
        input_files=[make_input_file()],
    )

    assert workflow.solver_result is not None
    assert workflow.verification_result is not None
    assert workflow.verification_result.passed

    text = format_solver_result(
        workflow.solver_result
    )
    rendered_rows = []

    for line in text.splitlines():
        if not line.startswith("| O"):
            continue

        cells = [
            cell.strip()
            for cell in line.strip("|").split("|")
        ]
        rendered_rows.append(
            tuple(cells[:4])
        )

    expected_rows = [
        (
            item.job,
            item.machine,
            item.start_time.strftime(
                "%Y-%m-%d %H:%M"
            ),
            item.end_time.strftime(
                "%Y-%m-%d %H:%M"
            ),
        )
        for item in workflow.solver_result.schedule
    ]

    assert rendered_rows == expected_rows


BEHAVIOR_CASES = json.loads(
    Path(
        "evals/cases/scheduling_behavior.json"
    ).read_text(encoding="utf-8")
)


@pytest.mark.parametrize(
    "case",
    BEHAVIOR_CASES,
    ids=lambda case: case["id"],
)
def test_scheduling_behavior_contract(case):
    due_time = (
        None
        if case["fixture"] == "missing_due_time"
        else "2026-09-22 18:00:00"
    )
    calls = []

    def tracked_solver(problem):
        calls.append(problem)
        return tools.solve_schedule(problem)

    result = run_scheduling_workflow(
        action=case["action"],
        input_files=[make_input_file(due_time)],
        solve_fn=tracked_solver,
    )

    assert result.stage == case["expected_stage"]
    assert bool(calls) is case["solver_called"]
    assert result.task_context is not None

    for phrase in case["expected_phrases"]:
        assert phrase in result.response_text


def test_conversation_preserves_scenario_versions():
    first = run_scheduling_workflow(
        action="solve",
        input_files=[make_input_file()],
        scenario_version=1,
    )
    second = run_scheduling_workflow(
        action="solve",
        input_files=[make_input_file()],
        scenario_version=2,
    )
    conversation = Conversation()

    for workflow in [first, second]:
        assert workflow.solver_result is not None
        assert workflow.verification_result is not None
        conversation.record_scenario(
            ScenarioRecord(
                version=workflow.scenario_version,
                solver_status=workflow.solver_result.status,
                verification_passed=(
                    workflow.verification_result.passed
                ),
                result=workflow.solver_result,
            )
        )

    restored = Conversation.model_validate(
        conversation.model_dump(mode="json")
    )

    assert [
        item.version
        for item in restored.scenario_history
    ] == [1, 2]
    assert all(
        item.verification_passed
        for item in restored.scenario_history
    )
