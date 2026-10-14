"""Stage 2: TheoryLower (paper Section 3.6 step 2; algorithm and proof in Appendix B)."""

from __future__ import annotations

from intentc.pipeline.context import Context
from intentc.syntax import Sketch
from intentc.stages.theory_lowering.kappa import WEIGHTS, features, kappa
from intentc.stages.theory_lowering.rules import CATALOG


def theory_lower(ctx: Context) -> tuple[bool, str]:
    """TheoryLower (Algorithm B.2): greedy rewriting while kappa_V strictly decreases."""
    tau = ctx.contract.kappa_threshold
    names = {p.name for p in ctx.contract.parameters}
    sk = Sketch(ctx.baseline_code, (), ())
    k = kappa(sk.code, ctx.baseline_params)
    trail = [f"kappa={k}"]
    while k > tau:
        options = [s2 for r in CATALOG for s2 in r.apply_once(sk, names)]
        # kappa of a sketch is evaluated with hole values unknown, so pow2-dependent
        # features count as removed only through the rewrite itself.
        scored = [(kappa(o.code, ctx.baseline_params), o) for o in options]
        scored = [(kk, o) for kk, o in scored if kk < k]
        if not scored:
            feats = features(sk.code, ctx.baseline_params)
            ctx.lower_report = "stuck; remaining cost drivers: " + ", ".join(
                f"{n}={v}" for n, v in sorted(feats.items(), key=lambda x: -x[1] * WEIGHTS[x[0]]) if v)
            break
        k, sk = min(scored, key=lambda x: x[0])
        trail.append(f"{sk.applied[-1]} -> kappa={k}")
    if k > tau and not sk.applied:
        ctx.sketches = []
        return False, f"stuck with no applicable rewrite; " + " ; ".join(trail) + (
            f"; {ctx.lower_report}" if ctx.lower_report else "")
    ctx.sketches = [sk] if sk.applied else []
    status = "tractable" if k <= tau else "stuck"
    return True, f"{status}; " + " ; ".join(trail) + (f"; {ctx.lower_report}" if ctx.lower_report else "")
