"""IntentCompile driver (paper Section 3.6): runs the stages in order.

CheckRealiz is required. TheoryLower, CEGIS, and BudgetNormalize may produce no
seed; GeneratePool still runs from P1. Winner selection measures, then emit
writes the winner or the unchanged baseline. The baseline is not required to
have been proved.
"""

from __future__ import annotations

import time
from pathlib import Path

from intentc.contract import spec as contract_mod
from intentc.pipeline.context import Context, StepRecord
from intentc.stages.s1_check_realiz import check_realiz
from intentc.stages.s2_theory_lower import theory_lower
from intentc.stages.s3_baseline_cegis import baseline_cegis
from intentc.stages.s4_budget_normalize import budget_normalize
from intentc.stages.s5_generate_pool import generate_pool
from intentc.stages.s6_winner_selection import select_winner
from intentc.stages.s7_emit import emit

# CheckRealiz must succeed: unsatisfiable I cannot be filled by any later rewrite.
# TheoryLower / CEGIS / BudgetNormalize may yield no seed. GeneratePool still
# runs, because its catalog starts from P1 (pad, AoS-to-SoA), not from those seeds.
REQUIRED = [("S1 CheckRealiz", check_realiz)]
SEARCH = [
    ("S2 TheoryLower", theory_lower),
    ("S3 Baseline-Directed CEGIS", baseline_cegis),
    ("S4 BudgetNormalize", budget_normalize),
]
POOL = [("S5 GeneratePool", generate_pool)]
SELECT = [("S6 WinnerSelection", select_winner)]


def compile_intent(contract_path: Path, workdir: Path, output: Path | None = None) -> Context:
    ctx = Context(contract_mod.load(contract_path), Path(workdir), output=output)
    ctx.workdir.mkdir(parents=True, exist_ok=True)
    stop = False
    for name, fn in REQUIRED + SEARCH + POOL + SELECT:
        if stop:
            break
        t0 = time.perf_counter()
        try:
            ok, details = fn(ctx)
        except Exception as e:  # a failing stage never yields an unverified program
            ok, details = False, f"error: {e}"
        ctx.steps.append(StepRecord(name, ok, time.perf_counter() - t0, details))
        if not ok and name.startswith("S1"):
            ctx.winner = None
            stop = True
    t0 = time.perf_counter()
    ok, details = emit(ctx)  # S7 always runs: emits the winner or the unchanged baseline
    ctx.steps.append(StepRecord("S7 Emit", ok, time.perf_counter() - t0, details))
    return ctx


def summary(ctx: Context) -> str:
    out = [f"contract {ctx.contract.name}"]
    for s in ctx.steps:
        out.append(f"  [{'PASS' if s.ok else 'FAIL'}] {s.stage} ({s.seconds:.1f}s): {s.details}")
    out += ["  log:"] + [f"    {line}" for line in ctx.log]
    return "\n".join(out)
