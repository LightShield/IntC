"""Stage 3: Baseline-Directed CEGIS (paper Section 3.6 step 3; algorithm and proof in Appendix B)."""

from __future__ import annotations

import z3

from intentc.contract import params
from intentc import syntax
from intentc.pipeline.context import Candidate, Context
from intentc.syntax import Sketch
from intentc.verify.verifier import all_proved, verify_candidate


def cegis(ctx: Context, sk: Sketch, max_tries: int | None = None,
          extra_constraints: tuple[str, ...] = ()) -> Candidate | None:
    """Algorithm B.1, enumerative form: propose parameter values in order of
    distance to the baseline (extra holes: smallest that meets side constraints),
    verify each with CBMC, exclude refuted valuations. Returns the first proved
    candidate, or None. Counterexample inputs are logged and not used as
    constraints on later proposals."""
    cap = ctx.contract.cegis_max_tries if max_tries is None else max_tries
    ps = list(ctx.contract.parameters)
    env = {p.name: z3.Int(p.name) for p in ps}
    bits = {p.name: p.bits for p in ps}
    for name in sk.extra_params:
        if name not in env:
            env[name] = z3.Int(name)
            bits[name] = 64
    opt = z3.Optimize()
    for p in ps:
        opt.add(env[p.name] >= 1, env[p.name] < 2 ** p.bits)
        for c in list(p.constraints):
            opt.add(params.compile_constraint(c, env, p.bits))
    for name in sk.extra_params:
        opt.add(env[name] >= 1, env[name] < 2 ** bits[name])
    for c in sk.side_constraints + extra_constraints:
        opt.add(params.compile_constraint(c, env))
    hole_names = list(env)
    refs = []
    for name in hole_names:
        if name in ctx.baseline_params:
            refs.append(z3.Abs(env[name] - ctx.baseline_params[name]))
        else:
            refs.append(env[name])
    opt.minimize(z3.Sum(refs))
    defined = syntax.defines(sk.code)
    for attempt in range(1, cap + 1):
        if opt.check() != z3.sat:
            ctx.log.append(f"CEGIS[{','.join(sk.applied) or 'baseline'}]: no further parameter values")
            return None
        m = opt.model()
        values = {name: m[env[name]].as_long() for name in hole_names if name in defined}
        code = syntax.set_parameters(sk.code, values)
        results = verify_candidate(code, values, ctx.contract, ctx.workdir)
        summary = ", ".join(f"{r.outcome}({r.seconds:.1f}s)" for r in results)
        ctx.log.append(f"CEGIS try {attempt}: {values} -> {summary}")
        if all_proved(results, ctx.contract):
            return Candidate(f"{'+'.join(sk.applied) or 'baseline'}:{values}", code, values, results, sk.applied)
        if any(r.outcome == "unknown" for r in results):
            ctx.log.append("CEGIS: unknown (timeout or undecided). Stopping; this valuation is not refuted.")
            return None
        cex = [r for r in results if r.outcome == "counterexample"]
        if cex and cex[0].inputs:
            ctx.log.append(f"CEGIS counterexample inputs: {cex[0].inputs}")
        opt.add(z3.Or([env[name] != values[name] for name in values]))
    ctx.log.append(f"CEGIS: gave up after {cap} tries")
    return None


def baseline_cegis(ctx: Context) -> tuple[bool, str]:
    """Fill the holes of each TheoryLower sketch."""
    for sk in ctx.sketches:
        c = cegis(ctx, sk)
        if c is not None:
            ctx.seeds.append(c)
    if not ctx.seeds:
        return False, "no sketch yielded a verified candidate"
    return True, "seeds: " + "; ".join(c.name for c in ctx.seeds)
