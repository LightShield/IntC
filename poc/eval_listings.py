"""Parse MSVC /FAs listings used as paper evidence. Not part of IntentCompile."""

from __future__ import annotations


def masm_proc_instructions(asm: str, proc: str) -> list[str]:
    """Opcode lines of a MASM PROC, excluding comments, labels, locals, and ret."""
    lines = asm.splitlines()
    start = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith(proc) and "PROC" in s:
            start = i + 1
            break
    if start is None:
        raise ValueError(f"missing {proc} PROC")
    ops: list[str] = []
    for ln in lines[start:]:
        s = ln.strip()
        if s.startswith(proc) and "ENDP" in s:
            break
        if not s or s.startswith(";") or s.endswith(":"):
            continue
        if "=" in s and not s.split()[0].lower() in {
            "mov", "add", "sub", "imul", "mul", "and", "or", "xor", "lea", "cmp",
        }:
            continue
        if s.lower().startswith("ret"):
            continue
        ops.append(s)
    return ops
