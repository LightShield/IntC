"""Stage 6: Winner selection (paper Section 3.4, winner selection; Appendix B)."""

from __future__ import annotations

from intentc import target
from intentc.pipeline.context import Context


def _stats(raw) -> target.BenchStats:
    if isinstance(raw, target.BenchStats):
        return raw
    return target.BenchStats.from_values([float(raw)])


def select_winner(ctx: Context) -> tuple[bool, str]:
    """Algorithm B.6: measure baseline and pool with MSVC; keep the fastest (ties -> baseline)."""
    obj = ctx.contract.objective
    if obj is None:
        if not ctx.pool:
            return False, "no objective and empty pool"
        ctx.winner = ctx.pool[0]
        return True, f"no objective: keep admitted candidate {ctx.winner.name}"
    b = _stats(target.run_bench(ctx.baseline_code, obj.bench, obj.trials, ctx.workdir, "baseline"))
    ctx.baseline_stats = b
    ctx.baseline_measured = b.median
    best, best_val = None, b.median
    for c in ctx.pool:
        s = _stats(target.run_bench(c.code, obj.bench, obj.trials, ctx.workdir, "cand"))
        c.measured_stats = s
        c.measured = s.median
        # Replace the current best only if faster by more than this candidate's
        # sample stdev. Near-ties keep the earlier program (baseline, then CEGIS seed).
        if s.median + s.stdev < best_val:
            best, best_val = c, s.median
    ctx.winner = best
    if best is None:
        return True, f"baseline kept ({ctx.baseline_measured:.3f} ± {b.stdev:.3f})"
    ws = best.measured_stats
    extra = f" ± {ws.stdev:.3f}" if isinstance(ws, target.BenchStats) else ""
    return True, (
        f"winner {best.name}: {best.measured:.3f}{extra} vs baseline "
        f"{ctx.baseline_measured:.3f} ± {b.stdev:.3f} {obj.metric}"
    )
