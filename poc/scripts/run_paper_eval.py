"""Record catalog, ablation, and as-if-compiler evidence for §7.

Every number is from running compile_intent, CBMC, or MSVC. Nothing is filled
from benchmark names. Run from poc/:

    python scripts/run_paper_eval.py

Writes experiments/eval/{catalog,ablations,asif,workhorse}.{json,tex}.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import eval_listings  # noqa: E402
from intentc import target  # noqa: E402
from intentc import syntax  # noqa: E402
from intentc.verify import cbmc  # noqa: E402
from intentc.pipeline import compile_intent, summary  # noqa: E402
from intentc.pipeline.context import Context  # noqa: E402
from intentc.verify.verifier import verify_candidate  # noqa: E402

EVAL = ROOT.parent / "experiments" / "eval"
CASES = ROOT / "cases"

# (relative contract, rewrite marker in winner, paper case id)
CATALOG = [
    ("cases/ringbuffer/contract_ci.yaml", "& (CAPACITY - 1)", "ring"),
    ("cases/ringbuffer_exact/contract_ci.yaml", "& (STORAGE - 1)", "ring-physical"),
    ("cases/hashset/contract_ci.yaml", "& (NBUCKETS - 1)", "hash"),
    ("cases/decimation/contract_ci.yaml", ">> SHIFT", "decimation"),
    ("cases/scale/contract_ci.yaml", "<< SH_GAIN", "scale"),
    ("cases/particles/contract_ci.yaml", "p_x[N]", "particles"),
    ("cases/flecs_pool/contract_ci.yaml", "* (alive[i])", "flecs"),
    ("cases/stencil1d/contract_ci.yaml", "halo_in", "stencil"),
    ("cases/fir_block/contract_ci.yaml", "#define BLOCK 8", "fir"),
    ("cases/ogre_pack/contract_ci.yaml", "uint8_t space", "ogre"),
    ("cases/inrange/contract_ci.yaml", "(d2) < (R)*(R)", "inrange"),
    ("cases/innerprod/contract_ci.yaml", "float result", "innerprod"),
    ("cases/luma/contract_ci.yaml", "9798", "luma"),
    ("cases/particles_fat/contract_ci.yaml", "p_x[N]", "particles-fat"),
]

WORKHORSE = [
    ("cases/ringbuffer/contract.yaml", "ring"),
    ("cases/hashset/contract.yaml", "hash"),
    ("cases/inrange/contract.yaml", "inrange"),
    ("cases/innerprod/contract.yaml", "innerprod"),
    ("cases/luma/contract.yaml", "luma"),
    ("cases/particles_fat/contract.yaml", "particles-fat"),
    ("cases/fir_block/contract.yaml", "fir"),
]


def _tex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def _step(ctx: Context, prefix: str):
    for s in ctx.steps:
        if s.stage.startswith(prefix):
            return s
    return None


def _k(contract) -> str:
    ks = []
    for h in contract.harnesses:
        if "K" in h.defines:
            ks.append(h.defines["K"])
        else:
            ks.append(f"unwind {h.unwind}")
    return ",".join(ks)


def _fmt_v(results) -> str:
    if not results:
        return "n/a"
    parts = []
    for r in results:
        parts.append(f"{r.outcome}/{r.seconds:.1f}s")
    return "; ".join(parts)


def _json_v(results) -> list[dict]:
    return [{"outcome": r.outcome, "seconds": r.seconds, "reason": r.reason} for r in results]


def _leaves_asif(baseline: dict[str, int], winner_params: dict[str, int], applied: tuple[str, ...]) -> str:
    """Logical/output parameter change vs a representation rewrite that as-if could in principle allow."""
    changed = {k: winner_params[k] for k in winner_params if baseline.get(k) != winner_params[k]}
    extra = {k: winner_params[k] for k in winner_params if k not in baseline}
    if any(n in changed or n in extra for n in (
        "CAPACITY", "NBUCKETS", "GAIN", "DIVISOR", "SHIFT", "SH_GAIN", "BLOCK",
    )):
        return "leaves as-if"
    if "STORAGE" in extra or "STORAGE" in changed:
        return "unexposed (API capacity fixed)"
    joined = " ".join(applied)
    if "narrow-accum" in joined or "luma-q15" in joined or "squared-compare" in joined:
        return "leaves as-if"
    if applied:
        return "representation"
    return "same source"


def record_case(contract_rel: str, marker: str, case_id: str, work: Path, verify_p1: bool) -> dict:
    cpath = ROOT / contract_rel
    wd = work / case_id
    out = wd / "out.c"
    wd.mkdir(parents=True, exist_ok=True)
    ctx = compile_intent(cpath, wd / "pipe", out)
    text = out.read_text(encoding="utf-8") if out.exists() else ""
    s2 = _step(ctx, "S2")
    winner = ctx.winner
    pool = []
    for c in ctx.pool:
        st = getattr(c, "measured_stats", None)
        pool.append({
            "name": c.name,
            "params": dict(c.params),
            "applied": list(c.applied),
            "measured": c.measured,
            "stats": st.as_json() if st is not None else None,
            "V": _json_v(c.proofs),
        })
    row = {
        "id": case_id,
        "contract": contract_rel,
        "K": _k(ctx.contract),
        "S2_ok": bool(s2 and s2.ok),
        "S2_details": s2.details if s2 else "",
        "pool_n": len(ctx.pool),
        "pool_applied": [list(c.applied) for c in ctx.pool],
        "pool": pool,
        "admitted": bool(ctx.pool) or winner is not None,
        "emit_is_baseline": "baseline kept unchanged" in text,
        "winner_name": winner.name if winner else None,
        "winner_params": dict(winner.params) if winner else {},
        "winner_applied": list(winner.applied) if winner else [],
        "winner_V": _json_v(winner.proofs) if winner else [],
        "winner_measured": winner.measured if winner else None,
        "winner_stats": winner.measured_stats.as_json() if winner and getattr(winner, "measured_stats", None) else None,
        "baseline_params": dict(ctx.baseline_params),
        "baseline_measured": ctx.baseline_measured,
        "baseline_stats": ctx.baseline_stats.as_json() if getattr(ctx, "baseline_stats", None) else None,
        "marker_in_winner": marker in text if winner else False,
        "as_if": _leaves_asif(ctx.baseline_params, winner.params, winner.applied) if winner else "fallback P1",
        "pipeline": summary(ctx),
        "seconds": {s.stage: s.seconds for s in ctx.steps},
        "steps_ok": {s.stage: s.ok for s in ctx.steps},
    }
    if verify_p1:
        p1 = verify_candidate(ctx.baseline_code, ctx.baseline_params, ctx.contract, wd / "p1")
        row["P1_V"] = _json_v(p1)
    else:
        row["P1_V"] = None
    return row


def run_ablations(work: Path) -> list[dict]:
    rows = []
    ring = CASES / "ringbuffer"
    stack = (ring / "handwritten/stack.c").read_text(encoding="utf-8")

    def cand(code, values, tag):
        d = work / tag
        d.mkdir(parents=True, exist_ok=True)
        (d / "candidate.c").write_text(code, encoding="utf-8")
        (d / "intent_params.h").write_text(syntax.params_header(values), encoding="utf-8")
        return d / "candidate.c"

    masked = (ring / "baseline.c").read_text().replace("% CAPACITY", "& (CAPACITY - 1)")
    masked = syntax.set_parameters(masked, {"CAPACITY": 1024})
    p1 = cand(masked, {"CAPACITY": 1024}, "mask1024")
    r = cbmc.verify([p1, ring / "harness_fifo.c"], [p1.parent], "harness", 8, 120, {"K": "4"})
    rows.append({
        "id": "contract-admits-mask",
        "setting": "FIFO harness on mask, CAPACITY 1024, K=4",
        "result": f"{r.outcome}/{r.seconds:.1f}s",
        "outcome": r.outcome,
        "seconds": r.seconds,
    })

    wrong = cand(syntax.set_parameters(
        (ring / "baseline.c").read_text().replace("% CAPACITY", "& (CAPACITY - 1)"),
        {"CAPACITY": 1000},
    ), {"CAPACITY": 1000}, "mask999")
    weak = cbmc.verify([wrong, ring / "harness_fifo.c"], [wrong.parent], "harness", 6, 120, {"K": "4"})
    strong = cbmc.verify([wrong, ring / "harness_fifo.c"], [wrong.parent], "harness", 12, 300, {"K": "10"})
    rows.append({
        "id": "bound-hides-bug",
        "setting": "& 999 at capacity 1000",
        "result": f"K=4 {weak.outcome}/{weak.seconds:.1f}s; K=10 {strong.outcome}/{strong.seconds:.1f}s",
        "outcome": strong.outcome,
        "seconds": strong.seconds,
        "weak": {"outcome": weak.outcome, "seconds": weak.seconds},
    })

    sc = cand(stack, {"CAPACITY": 1024}, "stack")
    cap_only = cbmc.verify(
        [sc, ring / "harness_capacity_only.c"], [sc.parent], "harness", 8, 120, {"K": "4"}
    )
    fifo = cbmc.verify([sc, ring / "harness_fifo.c"], [sc.parent], "harness", 8, 120, {"K": "4"})
    rows.append({
        "id": "underspec-stack",
        "setting": "LIFO stack vs occupancy-only Post vs FIFO Post",
        "result": f"capacity-only {cap_only.outcome}/{cap_only.seconds:.1f}s; FIFO {fifo.outcome}/{fifo.seconds:.1f}s",
        "capacity_only": {"outcome": cap_only.outcome, "seconds": cap_only.seconds},
        "fifo": {"outcome": fifo.outcome, "seconds": fifo.seconds},
    })

    out = work / "tight" / "out.c"
    ctx = compile_intent(ring / "contract_tight_memory.yaml", work / "tight" / "pipe", out)
    text = out.read_text(encoding="utf-8")
    rows.append({
        "id": "budget-drops-mask",
        "setting": "static_memory_bytes 8016 on the one-parameter ring",
        "result": "emit P1" if "baseline kept unchanged" in text else "unexpected winner",
        "winner": ctx.winner.name if ctx.winner else None,
        "S4": _step(ctx, "S4").details if _step(ctx, "S4") else "",
        "emit_baseline": "baseline kept unchanged" in text,
    })
    return rows


def dump_asif(work: Path) -> dict:
    """MSVC /O2 listing of remainder-by-1000 vs remainder-by-1024 vs mask."""
    src = Path(__file__).with_name("asif_slot.c")
    d = work / "asif"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, d / "asif_slot.c")
    env = target.msvc_env()
    cl = shutil.which("cl", path=env.get("PATH") or env.get("Path")) or shutil.which("cl.exe")
    if cl is None:
        raise FileNotFoundError("cl.exe")
    p = subprocess.run(
        [cl, "/nologo", "/O2", "/c", "/FAs", "/Faasif_slot.asm", "asif_slot.c"],
        cwd=d, env=env, capture_output=True, text=True,
    )
    asm = (d / "asif_slot.asm").read_text(encoding="utf-8", errors="replace") if (d / "asif_slot.asm").exists() else ""
    out_asm = EVAL / "asif_slot.asm"
    if asm:
        out_asm.write_text(asm, encoding="utf-8")
    clang = shutil.which("clang") or shutil.which("clang.exe")
    clang_note = "clang not on PATH"
    if clang:
        cp = subprocess.run(
            [clang, "-O2", "-S", "-o", str(d / "asif_slot.s"), str(d / "asif_slot.c")],
            capture_output=True, text=True,
        )
        clang_note = "ok" if cp.returncode == 0 else (cp.stderr or cp.stdout)[-400:]
        if cp.returncode == 0:
            (EVAL / "asif_slot_clang.s").write_text((d / "asif_slot.s").read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    n1000 = len(eval_listings.masm_proc_instructions(asm, "slot_1000")) if asm else 0
    return {
        "cl_rc": p.returncode,
        "cl_err": (p.stderr or p.stdout)[-500:],
        "has_reciprocal_mul": "0624dd2f1a9fbe77" in asm.lower() or "imul" in asm.lower(),
        "has_and_1023": "and" in asm.lower() and "1023" in asm,
        "slot_1000_ops": n1000,
        "clang": clang_note,
        "listing": str(out_asm) if asm else None,
    }


def dump_inrange(work: Path) -> dict:
    """MSVC /O2 listing of the IntentCompile in-range baseline as the bench compiles it."""
    cases = CASES / "inrange"
    d = work / "inrange_asm"
    d.mkdir(parents=True, exist_ok=True)
    (d / "candidate.c").write_text((cases / "baseline.c").read_text(encoding="utf-8"), encoding="utf-8")
    (d / "main.c").write_text((cases / "bench.c").read_text(encoding="utf-8"), encoding="utf-8")
    env = target.msvc_env()
    cl = shutil.which("cl", path=env.get("PATH") or env.get("Path")) or shutil.which("cl.exe")
    if cl is None:
        raise FileNotFoundError("cl.exe")
    p = subprocess.run(
        [cl, "/nologo", "/O2", "/c", "/FAs", "/Fainrange_baseline.asm", "main.c"],
        cwd=d, env=env, capture_output=True, text=True,
    )
    asm_path = d / "inrange_baseline.asm"
    asm = asm_path.read_text(encoding="utf-8", errors="replace") if asm_path.exists() else ""
    out_asm = EVAL / "inrange_baseline.asm"
    if asm:
        out_asm.write_text(asm, encoding="utf-8")
    clang = shutil.which("clang") or shutil.which("clang.exe")
    clang_note = "clang not on PATH"
    clang_has_sqrtss = None
    if clang:
        cp = subprocess.run(
            [clang, "-O2", "-S", "-o", str(d / "inrange_baseline.s"), str(cases / "baseline.c")],
            capture_output=True, text=True,
        )
        clang_note = "ok" if cp.returncode == 0 else (cp.stderr or cp.stdout)[-400:]
        if cp.returncode == 0:
            s = (d / "inrange_baseline.s").read_text(encoding="utf-8", errors="replace")
            (EVAL / "inrange_baseline_clang.s").write_text(s, encoding="utf-8")
            clang_has_sqrtss = "sqrtss" in s.lower() or "sqrtss" in s
    return {
        "cl_rc": p.returncode,
        "cl_err": (p.stderr or p.stdout)[-500:],
        "has_sqrtss": "sqrtss" in asm.lower(),
        "clang": clang_note,
        "clang_has_sqrtss": clang_has_sqrtss,
        "listing": str(out_asm) if asm else None,
    }


def pretty_applied(names: list[str]) -> str:
    seen: list[str] = []
    for n in names:
        base = n.split("@")[0]
        if base not in seen:
            seen.append(base)
    return ", ".join(seen)


def pretty_k(k: str) -> str:
    return k.replace("unwind ", "")


def pretty_asif(label: str) -> str:
    return {
        "leaves as-if": "not as-if",
        "unexposed (API capacity fixed)": "unexposed",
        "physical (API capacity fixed)": "unexposed",
        "representation": "layout",
        "fallback P1": "P1",
    }.get(label, label)


# Display names for Table 2. JSON ids stay the short case keys.
CATALOG_LABEL = {
    "ring": "DPDK ring",
    "ring-physical": "DPDK pad",
    "hash": "ClickHouse",
    "decimation": "Zephyr",
    "scale": "gain",
    "particles": "PARSEC",
    "flecs": "Flecs",
    "stencil": "MachSuite",
    "fir": "CMSIS-DSP",
    "ogre": "OGRE",
    "inrange": "Box2D",
    "innerprod": "Opus",
    "luma": "OpenCV",
    "particles-fat": "PARSEC fat",
}


def catalog_tex(rows: list[dict]) -> str:
    lines = [
        r"\begin{center}",
        r"\scriptsize",
        r"\begin{tabular}{llllll}",
        r"\toprule",
        r"Case & Rewrite & $K$ & $V$ on $P_1$ & $V$ on winner & As-if \\",
        r"\midrule",
    ]
    for r in rows:
        rew = pretty_applied(r["winner_applied"]) if r["winner_applied"] else ("P1" if r["emit_is_baseline"] else "?")
        p1 = _fmt_from_json(r.get("P1_V"))
        wv = _fmt_from_json(r.get("winner_V"))
        lines.append(
            " & ".join([
                _tex_escape(CATALOG_LABEL.get(r["id"], r["id"])),
                _tex_escape(rew),
                _tex_escape(pretty_k(str(r["K"]))),
                _tex_escape(p1),
                _tex_escape(wv),
                _tex_escape(pretty_asif(r["as_if"])),
            ]) + r" \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{center}", ""]
    return "\n".join(lines)


def _fmt_from_json(vs) -> str:
    if not vs:
        return "not run"
    return "; ".join(f"{v['outcome']}/{v['seconds']:.1f}s" for v in vs)


def ablations_tex(rows: list[dict]) -> str:
    lines = [
        r"\begin{center}",
        r"\scriptsize",
        r"\begin{tabular}{p{0.34\linewidth}p{0.58\linewidth}}",
        r"\toprule",
        r"Switch & Outcome \\",
        r"\midrule",
    ]
    labels = {
        "contract-admits-mask": "Contract oracle (FIFO harness)",
        "bound-hides-bug": r"Admission is $\models_K$",
        "underspec-stack": r"Occupancy-only vs FIFO $\mathit{Post}$",
        "budget-drops-mask": r"BudgetNormalize at 8016\,B",
    }
    for r in rows:
        lab = labels.get(r["id"], _tex_escape(r["id"]))
        lines.append(lab + " & " + _tex_escape(r["result"]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{center}", ""]
    return "\n".join(lines)


def _fmt_pm(stats, median) -> str:
    if median is None:
        return "---"
    if not stats:
        return f"{median:.2f}"
    m = stats.get("median", median)
    sd = stats.get("stdev", 0.0)
    return f"${m:.3f} \\pm {sd:.3f}$"


def _fmt_ratio(p1, win) -> str:
    if p1 is None or win is None or not win:
        return "---"
    return f"${round(p1, 3) / round(win, 3):.1f}\\times$"


def _workhorse_sort_key(r: dict) -> tuple:
    r"""Emit ratio descending; keep-\(P_1\) last."""
    if r.get("emit_is_baseline"):
        return (1, 0.0)
    p1, win = r.get("baseline_measured"), r.get("winner_measured")
    if not p1 or not win:
        return (1, 0.0)
    return (0, -(p1 / win))


def workhorse_tex(rows: list[dict]) -> str:
    lines = [
        r"\begin{center}",
        r"\scriptsize",
        r"\begin{tabular}{llllll}",
        r"\toprule",
        r"Case & $K$ & $V$ on admitted & $P_1$ ns & admitted ns & emit \\",
        r"\midrule",
    ]
    for r in sorted(rows, key=_workhorse_sort_key):
        p1 = r.get("baseline_measured")
        p1m = _fmt_pm(r.get("baseline_stats"), p1)
        if r.get("emit_is_baseline"):
            adm = (r.get("pool") or [{}])[0]
            win = adm.get("measured")
            wm = _fmt_pm(adm.get("stats"), win)
            vcell = _fmt_from_json(adm.get("V") or r.get("winner_V"))
            emit = r"$P_1$"
        else:
            win = r.get("winner_measured")
            wm = _fmt_pm(r.get("winner_stats"), win)
            vcell = _fmt_from_json(r.get("winner_V"))
            emit = _fmt_ratio(p1, win)
        lines.append(
            " & ".join([
                _tex_escape(CATALOG_LABEL.get(r["id"], r["id"])),
                _tex_escape(pretty_k(str(r["K"]))),
                _tex_escape(vcell),
                p1m,
                wm,
                emit,
            ]) + r" \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{center}", ""]
    return "\n".join(lines)


def write_tex_from_json() -> None:
    cat = json.loads((EVAL / "catalog.json").read_text(encoding="utf-8"))
    (EVAL / "catalog.tex").write_text(catalog_tex(cat["rows"]), encoding="utf-8")
    if (EVAL / "ablations.json").exists():
        ab = json.loads((EVAL / "ablations.json").read_text(encoding="utf-8"))
        (EVAL / "ablations.tex").write_text(ablations_tex(ab["rows"]), encoding="utf-8")
    if (EVAL / "workhorse.json").exists():
        horse = json.loads((EVAL / "workhorse.json").read_text(encoding="utf-8"))
        (EVAL / "workhorse.tex").write_text(workhorse_tex(horse["rows"]), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-p1", action="store_true", help="do not re-verify the baseline")
    ap.add_argument("--skip-catalog", action="store_true")
    ap.add_argument("--skip-workhorse", action="store_true")
    ap.add_argument("--skip-ablations", action="store_true")
    ap.add_argument("--tex-only", action="store_true", help="regenerate .tex from existing json")
    ap.add_argument("--listings-only", action="store_true", help="rebuild as-if and in-range /Fa listings")
    ap.add_argument("--only", default=None, help="rerun one workhorse id and splice into workhorse.json")
    args = ap.parse_args()
    if args.tex_only:
        write_tex_from_json()
        print("regenerated tex in", EVAL)
        return 0
    if args.listings_only:
        EVAL.mkdir(parents=True, exist_ok=True)
        work = EVAL / "_work"
        work.mkdir(parents=True, exist_ok=True)
        asif = dump_asif(work)
        ir = dump_inrange(work)
        print("asif slot_1000_ops", asif.get("slot_1000_ops"), "inrange sqrtss", ir.get("has_sqrtss"), "clang", ir.get("clang"))
        return 0 if asif.get("has_reciprocal_mul") and ir.get("has_sqrtss") else 1
    EVAL.mkdir(parents=True, exist_ok=True)
    work = EVAL / "_work"
    work.mkdir(parents=True, exist_ok=True)
    meta = {"when": datetime.now(timezone.utc).isoformat(), "machine": "see paper §7"}

    if not args.skip_catalog:
        catalog = []
        for rel, marker, cid in CATALOG:
            print(f"== catalog {cid} ==", flush=True)
            row = record_case(rel, marker, cid, work / "catalog", verify_p1=not args.skip_p1)
            catalog.append(row)
            print(f"   admitted={row['admitted']} applied={row['winner_applied']} P1={row.get('P1_V')}", flush=True)
        (EVAL / "catalog.json").write_text(json.dumps({"meta": meta, "rows": catalog}, indent=2), encoding="utf-8")
        (EVAL / "catalog.tex").write_text(catalog_tex(catalog), encoding="utf-8")

    if not args.skip_ablations:
        print("== ablations ==", flush=True)
        ab = run_ablations(work / "ablate")
        asif = dump_asif(work)
        ir = dump_inrange(work)
        (EVAL / "ablations.json").write_text(
            json.dumps({"meta": meta, "rows": ab, "asif": asif, "inrange_listing": ir}, indent=2),
            encoding="utf-8",
        )
        (EVAL / "ablations.tex").write_text(ablations_tex(ab), encoding="utf-8")
        print(f"   as-if listing reciprocal={asif['has_reciprocal_mul']} and1023={asif['has_and_1023']}", flush=True)

    if not args.skip_workhorse:
        existing = []
        if args.only and (EVAL / "workhorse.json").exists():
            existing = json.loads((EVAL / "workhorse.json").read_text(encoding="utf-8"))["rows"]
            meta = json.loads((EVAL / "workhorse.json").read_text(encoding="utf-8")).get("meta", meta)
            meta = {**meta, "when_spliced": datetime.now(timezone.utc).isoformat(), "spliced": args.only}
        horse_by_id = {r["id"]: r for r in existing if r["id"] != args.only}
        for rel, cid in WORKHORSE:
            if args.only and cid != args.only:
                continue
            print(f"== timed {cid} ==", flush=True)
            row = record_case(rel, "", cid, work / "horse", verify_p1=False)
            horse_by_id[cid] = row
            print(
                f"   measured P1={row['baseline_measured']} win={row['winner_measured']} "
                f"emit_p1={row['emit_is_baseline']}",
                flush=True,
            )
        horse = [horse_by_id[cid] for _, cid in WORKHORSE if cid in horse_by_id]
        (EVAL / "workhorse.json").write_text(json.dumps({"meta": meta, "rows": horse}, indent=2), encoding="utf-8")
        (EVAL / "workhorse.tex").write_text(workhorse_tex(horse), encoding="utf-8")
    print("wrote", EVAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
