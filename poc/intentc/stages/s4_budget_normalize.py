"""Stage 4: BudgetNormalize (paper §5, Appendix).

Keeps proved seeds whose compiled sizeof of file-scope objects fits B.
A candidate that misses the ceiling is dropped. A missing ceiling is no
check. The baseline is never proved here: if it fits the budget it remains
the fallback of winner selection / emit (Theorem: baseline need not be in A).
This stage does not run CBMC on the unmasked baseline, which would time out
on i % 1000 at the same K used for the mask.
"""

from __future__ import annotations

from intentc import target
from intentc.pipeline.context import Context


def budget_normalize(ctx: Context) -> tuple[bool, str]:
    limit = ctx.contract.budget.get("static_memory_bytes")
    if limit is None:
        return True, "no budget"
    kept, notes = [], []
    baseline_mem = target.static_memory(ctx.baseline_code, ctx.workdir)
    notes.append(f"baseline {baseline_mem} B")
    for c in ctx.seeds:
        c.static_memory = target.static_memory(c.code, ctx.workdir)
        if c.static_memory <= limit:
            kept.append(c)
            notes.append(f"{c.name}: {c.static_memory} B ok")
            continue
        notes.append(f"{c.name}: {c.static_memory} B > {limit} B")
        if baseline_mem <= limit:
            notes.append("baseline fits; candidate dropped (emit will keep baseline)")
        else:
            notes.append(f"baseline {baseline_mem} B also exceeds {limit} B")
    ctx.seeds = kept
    if kept:
        return True, "; ".join(notes)
    if baseline_mem <= limit:
        return False, "; ".join(notes)  # empty A, compiler emits P1
    return False, "; ".join(notes)
