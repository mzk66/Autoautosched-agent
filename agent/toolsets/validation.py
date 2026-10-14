from domain.schema import SchedulingProblem, SolveResult
from domain.validator import validate_problem_report
from domain.verifier import verify_solution as _verify_solution
from domain.workflow_schema import ValidationReport, VerificationReport


def validate_problem(
    problem: SchedulingProblem,
) -> ValidationReport:
    return validate_problem_report(
        problem
    )


def verify_solution(
    problem: SchedulingProblem,
    result: SolveResult,
) -> VerificationReport:
    return _verify_solution(
        problem,
        result,
    )
