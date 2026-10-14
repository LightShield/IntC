"""Rebuild the evaluation tables (catalog, ablations, workhorse, as-if listing).

From poc/:

    python reproduce.py           # full run, ~12 min
    python reproduce.py --tex-only
    python reproduce.py --check   # outcomes vs README expected facts (no CBMC)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVAL = ROOT.parent / "experiments" / "eval"
sys.path.insert(0, str(ROOT))
import eval_listings  # noqa: E402


def check() -> int:
    """Outcomes that must not drift. Times are allowed to move."""
    cat = json.loads((EVAL / "catalog.json").read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in cat["rows"]}
    fail = []

    def want(cid, admitted, as_if_prefix, p1_outcome=None):
        r = rows.get(cid)
        if r is None:
            fail.append(f"missing {cid}")
            return
        if bool(r["admitted"]) != admitted:
            fail.append(f"{cid} admitted={r['admitted']}")
        if not str(r.get("as_if", "")).startswith(as_if_prefix):
            fail.append(f"{cid} as_if={r.get('as_if')}")
        p1 = (r.get("P1_V") or [{}])[0].get("outcome")
        if p1_outcome and p1 != p1_outcome:
            fail.append(f"{cid} P1={p1}")

    want("ring", True, "leaves", "unknown")
    want("ring-physical", True, "unexposed", "unknown")
    want("hash", True, "leaves", "unknown")
    want("decimation", True, "leaves", "proved")
    want("scale", True, "leaves", "proved")
    want("particles", True, "representation", "proved")
    want("flecs", True, "representation", "proved")
    want("stencil", True, "representation", "proved")
    want("fir", True, "leaves", "proved")
    want("ogre", True, "representation", "proved")
    want("inrange", True, "leaves", "proved")
    want("innerprod", True, "leaves", "proved")
    want("luma", True, "leaves", "unknown")
    want("particles-fat", True, "representation", "proved")
    if rows["particles"].get("S2_ok"):
        fail.append("particles S2 should fail")
    ab = json.loads((EVAL / "ablations.json").read_text(encoding="utf-8"))
    by = {r["id"]: r for r in ab["rows"]}
    if by["bound-hides-bug"]["weak"]["outcome"] != "proved":
        fail.append("K=4 colliding mask not proved")
    if by["bound-hides-bug"]["outcome"] != "counterexample":
        fail.append("K=10 colliding mask not cex")
    if by["underspec-stack"]["capacity_only"]["outcome"] != "proved":
        fail.append("stack occupancy not proved")
    if by["underspec-stack"]["fifo"]["outcome"] != "counterexample":
        fail.append("stack FIFO not cex")
    if not by["budget-drops-mask"].get("emit_baseline"):
        fail.append("tight budget did not emit P1")
    if not ab["asif"].get("has_reciprocal_mul") or not ab["asif"].get("has_and_1023"):
        fail.append("as-if listing missing remainder vs mask")
    horse = json.loads((EVAL / "workhorse.json").read_text(encoding="utf-8"))
    h = {r["id"]: r for r in horse["rows"]}
    if h["ring"]["winner_params"].get("CAPACITY") != 1024:
        fail.append("ring winner not 1024")
    if h["hash"]["winner_params"].get("NBUCKETS") != 16384:
        fail.append("hash winner not 16384")
    if not h.get("fir", {}).get("emit_is_baseline"):
        fail.append("fir should keep P1")
    fir_pool = (h.get("fir", {}).get("pool") or [{}])[0]
    fir_adm = fir_pool.get("measured")
    fir_p1 = h.get("fir", {}).get("baseline_measured")
    if fir_p1 is None or fir_adm is None or not (fir_adm > fir_p1):
        fail.append(f"fir admitted {fir_adm} not slower than P1 {fir_p1}")
    for cid, r in h.items():
        p1m = r.get("baseline_measured")
        bs = r.get("baseline_stats") or {}
        if r.get("emit_is_baseline"):
            adm = (r.get("pool") or [{}])[0]
            wm = adm.get("measured")
            ws = adm.get("stats") or {}
        else:
            wm = r.get("winner_measured")
            ws = r.get("winner_stats") or {}
        if p1m is None or wm is None:
            fail.append(f"{cid} missing workhorse ns/op")
        elif cid != "fir" and not (wm < p1m):
            fail.append(f"{cid} winner {wm} not faster than P1 {p1m}")
        if bs.get("n") != 31 or ws.get("n") != 31:
            fail.append(f"{cid} expected 31 trials, got P1 n={bs.get('n')} admitted n={ws.get('n')}")
        if "stdev" not in bs or "stdev" not in ws:
            fail.append(f"{cid} missing stdev")
    slot = (EVAL / "asif_slot.asm").read_text(encoding="utf-8")
    if len(eval_listings.masm_proc_instructions(slot, "slot_1000")) != 10:
        fail.append("slot_1000 is not ten instructions before ret")
    inrange_asm = EVAL / "inrange_baseline.asm"
    if not inrange_asm.is_file() or "sqrtss" not in inrange_asm.read_text(encoding="utf-8", errors="replace").lower():
        fail.append("inrange baseline listing missing sqrtss")
    if fail:
        print("check failed:")
        for f in fail:
            print(" ", f)
        return 1
    print("check ok:", len(rows), "catalog rows, ablations, workhorse params")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        raise SystemExit(check())
    from scripts.run_paper_eval import main
    sys.argv = [sys.argv[0], *[a for a in sys.argv[1:] if a != "--check"]]
    raise SystemExit(main())
