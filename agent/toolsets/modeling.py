from domain.normalizer import build_problem_ir as _build_problem_ir
from domain.workflow_schema import ParsedSchedulingData, ProblemBuildResult


def build_problem_ir(
    parsed: ParsedSchedulingData,
) -> ProblemBuildResult:
    return _build_problem_ir(parsed)
