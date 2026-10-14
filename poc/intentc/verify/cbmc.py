"""Verifier V(P, Phi_func, t): run CBMC on a candidate program against a contract harness.

Outcomes follow the paper's definition of a sound verifier:
- Proved: every property, including every unwinding assertion, holds.
- Counterexample: some contract or UB property fails; the input values CBMC chose
  for the harness's nondet_* calls are returned, in call order, for replay.
- Unknown: timeout, CBMC error, or an unwinding assertion fails (the bound was too
  small to cover the program's loops, including when a later property also fails
  on that truncated path). Unknown is never reported as Proved.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from intentc.target import msvc_env

CBMC = Path(os.environ.get("INTENTC_CBMC", r"C:\Program Files\cbmc\bin\cbmc.exe"))


def require_cbmc() -> Path:
    if not CBMC.is_file():
        raise FileNotFoundError(f"CBMC not found at {CBMC}; install CBMC 6.11.0 or set INTENTC_CBMC")
    return CBMC

# Checks for undefined behavior and memory errors (the UB obligations of Section 3).
UB_CHECKS = [
    "--bounds-check",
    "--pointer-check",
    "--signed-overflow-check",
    "--div-by-zero-check",
    "--undefined-shift-check",
]


@dataclass
class Property:
    name: str
    description: str
    status: str  # SUCCESS / FAILURE / ERROR / UNKNOWN


@dataclass
class Result:
    outcome: str  # "proved" / "counterexample" / "unknown"
    seconds: float
    properties: list[Property] = field(default_factory=list)
    inputs: list[tuple[str, int]] = field(default_factory=list)  # (nondet function, value) in call order
    reason: str = ""

    @property
    def failed(self) -> list[Property]:
        return [p for p in self.properties if p.status == "FAILURE"]


def verify(
    sources: list[Path],
    include_dirs: list[Path],
    entry: str,
    unwind: int,
    timeout_s: float,
    defines: dict[str, str] | None = None,
    extra_args: list[str] | None = None,
) -> Result:
    cmd = [str(require_cbmc()), *map(str, sources)]
    for d in include_dirs:
        cmd += ["-I", str(d)]
    for k, v in (defines or {}).items():
        cmd += ["-D", f"{k}={v}"]
    cmd += ["--function", entry, *UB_CHECKS,
            "--unwind", str(unwind), "--unwinding-assertions",
            "--arrays-uf-always",  # array theory; expanding large arrays is infeasible
            "--json-ui", "--trace", *(extra_args or [])]
    t0 = time.perf_counter()
    try:
        # Windows CBMC uses cl.exe as its C preprocessor, so it shares msvc_env with measurement.
        proc = subprocess.run(cmd, capture_output=True, text=True, env=msvc_env(), timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return Result("unknown", time.perf_counter() - t0, reason=f"timeout after {timeout_s}s")
    seconds = time.perf_counter() - t0
    try:
        messages = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return Result("unknown", seconds, reason=f"CBMC output not JSON (rc={proc.returncode}): "
                      + (proc.stderr or proc.stdout)[-500:])
    results = next((m["result"] for m in messages if isinstance(m, dict) and "result" in m), None)
    if results is None:
        errors = [m.get("messageText", "") for m in messages
                  if isinstance(m, dict) and m.get("messageType") == "ERROR"]
        return Result("unknown", seconds, reason="CBMC produced no results: " + "; ".join(errors)[-500:])

    props = [Property(r["property"], r.get("description", ""), r["status"]) for r in results]
    failed = [r for r in results if r["status"] == "FAILURE"]
    if not failed:
        if all(p.status == "SUCCESS" for p in props):
            return Result("proved", seconds, props)
        return Result("unknown", seconds, props, reason="some properties not decided")
    real = [r for r in failed if ".unwind." not in r["property"]]
    unwind = [r for r in failed if ".unwind." in r["property"]]
    if not real:
        return Result("unknown", seconds, props, reason="unwinding assertion failed: bound too small")
    if unwind:
        return Result("unknown", seconds, props,
                      reason="unwinding assertion failed with other property failures")
    return Result("counterexample", seconds, props, inputs=_nondet_inputs(real[0].get("trace", [])))


def _nondet_inputs(trace: list[dict]) -> list[tuple[str, int]]:
    """Values returned by nondet_* calls along the counterexample, in order."""
    out: list[tuple[str, int]] = []
    for step in trace:
        lhs = step.get("lhs", "")
        if step.get("stepType") == "assignment" and lhs.startswith("return_value_nondet_"):
            fn = lhs[len("return_value_"):]
            data = step.get("value", {}).get("data")
            if data is not None:
                out.append((fn, _c_literal(data)))
    return out


def _c_literal(data: object) -> int:
    """Parse CBMC's rendering of a value: 123, 0ull, -5l, TRUE/FALSE, 0x1Fu."""
    if isinstance(data, bool):
        return int(data)
    if isinstance(data, int):
        return data
    s = str(data).strip()
    if s.upper() in {"TRUE", "FALSE"}:
        return int(s.upper() == "TRUE")
    s = s.rstrip("uUlL")
    return int(s, 0)
