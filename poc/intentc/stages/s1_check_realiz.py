"""Stage 1: CheckRealiz (paper Section 3.6 step 1; algorithm and proof in Appendix B)."""

from __future__ import annotations

import z3

from intentc.contract import params
from intentc import syntax
from intentc.pipeline.context import Context


def check_realiz(ctx: Context) -> tuple[bool, str]:
    """CheckRealiz: the parameter constraints I are satisfiable (unsat core otherwise).

    Post is given by harnesses, so its consistency is not checked here. A Post that
    no program satisfies shows up as no candidate (and no baseline) being proved.
    Z3 unknown on I is a failed stage, not a green light.
    """
    ctx.baseline_code = ctx.contract.baseline.read_text(encoding="utf-8")
    sites = syntax.defines(ctx.baseline_code)
    for p in ctx.contract.parameters:
        if p.name not in sites:
            return False, f"parameter {p.name} is not a #define in the baseline"
    ctx.baseline_params = {p.name: sites[p.name].value for p in ctx.contract.parameters}
    s = z3.Solver()
    env = {p.name: z3.Int(p.name) for p in ctx.contract.parameters}
    tracked = {}
    for p in ctx.contract.parameters:
        s.add(env[p.name] >= 1, env[p.name] < 2 ** p.bits)
        for c in p.constraints:
            lit = z3.Bool(f"{p.name}: {c}")
            tracked[str(lit)] = c
            s.assert_and_track(params.compile_constraint(c, env, p.bits), lit)
    res = s.check()
    if res == z3.unsat:
        return False, f"contradictory parameter constraints: {[str(x) for x in s.unsat_core()]}"
    if res == z3.unknown:
        return False, "parameter constraints: solver returned unknown"
    return True, f"parameter constraints satisfiable; baseline parameters {ctx.baseline_params}"
