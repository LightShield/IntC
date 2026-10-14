"""The verifier V(P, Phi_func, t) of Section 3.5: a candidate is proved only if CBMC proves every harness."""

from __future__ import annotations

import hashlib
from pathlib import Path

from intentc.contract.spec import Contract
from intentc import syntax
from intentc.verify import cbmc


def verify_candidate(code: str, params: dict[str, int], contract: Contract, workdir: Path) -> list[cbmc.Result]:
    """Run every harness on the candidate. Stops at the first non-proved harness."""
    tag = hashlib.sha256((code + repr(sorted(params.items()))).encode()).hexdigest()[:12]
    d = workdir / f"cand_{tag}"
    d.mkdir(parents=True, exist_ok=True)
    prog = d / "candidate.c"
    prog.write_text(code, encoding="utf-8")
    (d / "intent_params.h").write_text(syntax.params_header(params), encoding="utf-8")
    results = []
    for h in contract.harnesses:
        r = cbmc.verify([prog, h.file], [d], h.entry, h.unwind, contract.verify_timeout_s, h.defines)
        results.append(r)
        if r.outcome != "proved":
            break
    return results


def all_proved(results: list[cbmc.Result], contract: Contract) -> bool:
    return len(results) == len(contract.harnesses) and all(r.outcome == "proved" for r in results)
