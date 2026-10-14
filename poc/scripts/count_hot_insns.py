"""Compile timed benches with MSVC /FAs and count opcodes in the innermost loop
of the timed trial. Used to check whether a static-instruction-count objective
would disagree with wall-clock ranking.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import eval_listings  # noqa: E402
from intentc import target  # noqa: E402

EVAL = ROOT.parent / "experiments" / "eval"
CASES = ROOT / "cases"
HORSE = EVAL / "_work" / "horse"

PAIRS = [
    ("inrange", CASES / "inrange" / "baseline.c", HORSE / "inrange" / "out.c", CASES / "inrange" / "bench.c"),
    ("luma", CASES / "luma" / "baseline.c", HORSE / "luma" / "out.c", CASES / "luma" / "bench.c"),
    ("innerprod", CASES / "innerprod" / "baseline.c", HORSE / "innerprod" / "out.c", CASES / "innerprod" / "bench.c"),
    ("particles-fat", CASES / "particles_fat" / "baseline.c", HORSE / "particles-fat" / "out.c", CASES / "particles_fat" / "bench.c"),
]


def _strip_header(text: str) -> str:
    if text.startswith("/* ===== generated"):
        end = text.find("*/")
        if end != -1:
            return text[end + 2 :].lstrip("\n")
    return text


def _compile_fa(cand: str, bench: str, dest: Path) -> str:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "candidate.c").write_text(cand, encoding="utf-8")
    (dest / "main.c").write_text(bench, encoding="utf-8")
    env = target.msvc_env()
    path = env.get("PATH") or env.get("Path")
    cl = shutil.which("cl", path=path) or shutil.which("cl.exe", path=path)
    p = subprocess.run(
        [cl, "/nologo", "/O2", "/c", "/FAs", "/Fahot.asm", "main.c"],
        cwd=dest, env=env, capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise RuntimeError(p.stdout + p.stderr)
    return (dest / "hot.asm").read_text(encoding="utf-8", errors="replace")


def _is_op(s: str) -> bool:
    if not s or s.startswith(";") or s.endswith(":") or s.startswith("INCLUDE"):
        return False
    first = s.split()[0].lower() if s.split() else ""
    if first in {"", "end", "endp", "proc", "segment", "ends", "public", "extrn", "comm"}:
        return False
    if re.match(r"^\S+\s*=", s):
        return False
    if first.startswith("ret"):
        return False
    return bool(re.match(r"^[a-z][a-z0-9]+$", first))


def innermost_loop_ops(asm: str) -> list[str]:
    """Opcode lines of the shortest backward-edge loop in main (the hot inner trip)."""
    try:
        ops_all = eval_listings.masm_proc_instructions(asm, "main")
    except ValueError:
        return []
    # Fall back: scan listing for $LL labels with shortest body.
    lines = asm.splitlines()
    labels: dict[str, int] = {}
    for i, ln in enumerate(lines):
        s = ln.strip()
        if re.match(r"^\$LL\d+", s) and s.endswith(":"):
            labels[s[:-1]] = i
    best: list[str] = []
    best_len = 10**9
    for name, start in labels.items():
        body: list[str] = []
        for ln in lines[start + 1 :]:
            s = ln.strip()
            if s.startswith(name) and s.endswith(":"):
                break
            if re.search(rf"\b{re.escape(name)}\b", s) and s.lower().split()[0] in {
                "jne", "je", "jmp", "ja", "jb", "jae", "jbe", "jg", "jl", "jge", "jle", "jnz", "jz",
            }:
                if 2 <= len(body) < best_len:
                    best, best_len = body, len(body)
                break
            if _is_op(s):
                body.append(s)
    return best if best else ops_all


def main() -> int:
    work = EVAL / "_work" / "proxy_ic"
    rows = []
    for cid, base, win, bench in PAIRS:
        if not win.is_file():
            print("skip", cid, "no winner source")
            continue
        btxt = bench.read_text(encoding="utf-8")
        p1 = _compile_fa((CASES / cid.replace("particles-fat", "particles_fat") / "baseline.c").read_text(encoding="utf-8") if False else base.read_text(encoding="utf-8"), btxt, work / cid / "p1")
        wsrc = _strip_header(win.read_text(encoding="utf-8"))
        w = _compile_fa(wsrc, btxt, work / cid / "win")
        p1_ops = innermost_loop_ops(p1)
        w_ops = innermost_loop_ops(w)
        (EVAL / f"proxy_{cid}_p1.asm").write_text(p1, encoding="utf-8")
        (EVAL / f"proxy_{cid}_win.asm").write_text(w, encoding="utf-8")
        row = {
            "id": cid,
            "p1_inner_ops": len(p1_ops),
            "win_inner_ops": len(w_ops),
            "ic_prefers_winner": len(w_ops) < len(p1_ops),
            "p1_sample": p1_ops[:12],
            "win_sample": w_ops[:12],
        }
        rows.append(row)
        print(cid, "P1", len(p1_ops), "win", len(w_ops), "IC prefers winner" if row["ic_prefers_winner"] else "IC prefers P1 or tie")
    import json
    (EVAL / "proxy_ic.json").write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
