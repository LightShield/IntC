"""Trusted production compiler L_Target: MSVC cl.exe for B, O, and CBMC's preprocessor.

Not the verifier. Admission is CBMC; this package compiles the candidate and
reads sizeof or bench output. Public names are in __all__.
"""

from __future__ import annotations

import functools
import hashlib
import os
import shutil
import statistics
import subprocess
from dataclasses import dataclass
from pathlib import Path

from intentc import syntax

__all__ = ["VCVARS", "msvc_env", "BenchStats", "static_memory", "run_bench"]

VCVARS = Path(os.environ.get(
    "INTENTC_VCVARS",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
))

_CL_FLAGS = ["/nologo", "/O2", "/EHsc", "/W3"]


def _parse_set(text: str) -> dict[str, str]:
    env = dict(os.environ)
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    return env


def _which_cl(env: dict[str, str]) -> str | None:
    path = env.get("PATH") or env.get("Path") or ""
    for dir in path.split(os.pathsep):
        cand = Path(dir) / "cl.exe"
        if cand.is_file():
            return str(cand)
    return None


@functools.cache
def msvc_env() -> dict[str, str]:
    """Environment produced by vcvars64.bat."""
    if not VCVARS.is_file():
        raise FileNotFoundError(f"vcvars64.bat not found at {VCVARS}; set INTENTC_VCVARS")
    cmd = f'call "{VCVARS}" && set'
    proc = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    env = _parse_set(proc.stdout)
    if _which_cl(env) is None:
        vc = VCVARS.parents[2]  # .../VC
        hits = list(vc.glob("Tools/MSVC/*/bin/Hostx64/x64/cl.exe"))
        if not hits:
            raise FileNotFoundError(
                f"cl.exe not on PATH after vcvars (rc={proc.returncode}). set INTENTC_VCVARS"
            )
        cl_dir = str(hits[-1].parent)
        env["PATH"] = cl_dir + os.pathsep + (env.get("PATH") or env.get("Path") or "")
    return env


@dataclass(frozen=True)
class BenchStats:
    """One bench run: every printed trial plus summary stats. Ranking uses median."""

    values: tuple[float, ...]
    median: float
    mean: float
    stdev: float
    min: float
    max: float
    q1: float
    q3: float

    @classmethod
    def from_values(cls, values: list[float]) -> BenchStats:
        if not values:
            raise ValueError("benchmark produced no trial values")
        vals = tuple(float(v) for v in values)
        qs = statistics.quantiles(vals, n=4, method="inclusive") if len(vals) >= 2 else [vals[0], vals[0], vals[0]]
        return cls(
            values=vals,
            median=statistics.median(vals),
            mean=statistics.fmean(vals),
            stdev=statistics.stdev(vals) if len(vals) >= 2 else 0.0,
            min=min(vals),
            max=max(vals),
            q1=qs[0],
            q3=qs[2] if len(qs) > 2 else qs[0],
        )

    def as_json(self) -> dict:
        return {
            "median": self.median,
            "mean": self.mean,
            "stdev": self.stdev,
            "min": self.min,
            "max": self.max,
            "q1": self.q1,
            "q3": self.q3,
            "n": len(self.values),
            "values": list(self.values),
        }


def _build_and_run(main_c: str, cand_code: str, workdir: Path, tag: str, args: list[str] | None = None) -> str:
    h = hashlib.sha256((main_c + cand_code).encode()).hexdigest()[:12]
    d = workdir / f"build_{tag}_{h}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "candidate.c").write_text(cand_code, encoding="utf-8")
    (d / "main.c").write_text(main_c, encoding="utf-8")
    exe = d / "main.exe"
    if not exe.exists():
        env = msvc_env()
        path = env.get("PATH") or env.get("Path")
        cl = shutil.which("cl", path=path) or shutil.which("cl.exe", path=path)
        if cl is None:
            raise FileNotFoundError("cl.exe not found in the MSVC environment")
        p = subprocess.run([cl, *_CL_FLAGS, "main.c", "/Fe:main.exe"], cwd=d, env=env,
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"MSVC build failed:\n{p.stdout[-2000:]}")
    p = subprocess.run([str(exe), *(args or [])], cwd=d, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(f"benchmark failed (rc={p.returncode}): {p.stderr[-500:]}")
    return p.stdout


def _global_objects(code: str) -> list[str]:
    """Names of file-scope variables (not functions)."""
    tree, _ = syntax.parse(code)
    names = []
    for n in tree.root_node.named_children:
        if n.type != "declaration":
            continue
        d = n.child_by_field_name("declarator")
        while d is not None and d.type in {"init_declarator", "array_declarator"}:
            d = d.child_by_field_name("declarator")
        if d is not None and d.type == "identifier":
            names.append(d.text.decode())
    return names


def static_memory(code: str, workdir: Path) -> int:
    """Sum of sizeof over all file-scope objects, as compiled by MSVC for x64."""
    names = _global_objects(code)
    body = " + ".join(f"sizeof({n})" for n in names) or "0"
    main_c = f'#include <stdio.h>\n#include "candidate.c"\nint main(void) {{ printf("%zu\\n", (size_t)({body})); return 0; }}\n'
    return int(_build_and_run(main_c, code, workdir, "mem").strip())


def run_bench(code: str, bench: Path, trials: int, workdir: Path, tag: str) -> BenchStats:
    """Compile the benchmark driver (which #includes "candidate.c") and return
    median, mean, sample stdev, IQR, min/max, and the raw trial list."""
    out = _build_and_run(bench.read_text(encoding="utf-8"), code, workdir, f"bench_{tag}", [str(trials)])
    values = [float(x) for x in out.split()]
    if len(values) != trials:
        raise RuntimeError(f"benchmark printed {len(values)} values, expected {trials}")
    return BenchStats.from_values(values)
