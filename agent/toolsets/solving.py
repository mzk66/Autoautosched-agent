from agent.toolsets.validation import validate_problem
from domain.schema import SchedulingProblem, SolveResult
from solver.solver import solve_schedule as _solve_schedule


def solve_schedule(
    problem: SchedulingProblem,
) -> SolveResult:
    validation = validate_problem(problem)

    if not validation.can_solve:
        raise ValueError(
            "Cannot call solver with an invalid SchedulingProblem."
        )

    return _solve_schedule(problem)
