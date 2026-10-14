"""Stage 5: GeneratePool (paper §5, Appendix).

Each rewrite is applied to the baseline, filled by CEGIS, and kept if
proved and in budget. Speed is not estimated here. Winner selection measures.
"""

from __future__ import annotations

from intentc import target
from intentc.pipeline.context import Context
from intentc.syntax import Sketch
from intentc.stages.pool.strategies import PERFORMANCE_CATALOG
from intentc.stages.s3_baseline_cegis import cegis


def generate_pool(ctx: Context, performance_catalog: tuple | None = None) -> tuple[bool, str]:
    catalog = PERFORMANCE_CATALOG if performance_catalog is None else performance_catalog
    ctx.pool = list(ctx.seeds)
    names = {p.name for p in ctx.contract.parameters}
    added: list[str] = []
    limit = ctx.contract.budget.get("static_memory_bytes")
    for rewrite in catalog:
        for sk in rewrite.apply_once(Sketch(ctx.baseline_code, (), ()), names):
            cand = cegis(ctx, sk)
            if cand is None:
                continue
            if limit is not None:
                cand.static_memory = target.static_memory(cand.code, ctx.workdir)
                if cand.static_memory > limit:
                    ctx.log.append(f"pool drop {cand.name}: {cand.static_memory} B > {limit} B")
                    continue
            if any(cand.code == p.code for p in ctx.pool):
                continue
            ctx.pool.append(cand)
            added.append(cand.name)
    extra = f", added {', '.join(added)}" if added else ", added none"
    return True, f"pool of {len(ctx.pool)} (performance catalog has {len(catalog)} rewrites{extra})"
