---
name: scheduling
description: Enforce the deterministic scheduling workflow and solver boundary.
---

# Scheduling Boundary

Scheduling results must never be invented.

You MUST NOT manually assign jobs to machines, invent start or end times,
calculate a schedule yourself, or claim feasibility or infeasibility without
calling the solver.

Before presenting any schedule:

1. Inspect and parse the source files.
2. Build or update the `SchedulingProblem` IR.
3. Validate the IR.
4. Resolve all blocking ambiguities.
5. Call `solve_schedule`.
6. Call `verify_solution`.
7. Present only values returned by these tools.

Never modify missing or inconsistent source data without explicit user
confirmation.

Always distinguish:

- source facts
- inferred mappings
- assumptions
- unresolved issues

The LLM may explain a verified solver result, but machine assignments, start
times, end times, durations, tardiness, objective values, feasibility status,
and KPIs must come from `SolveResult`.
