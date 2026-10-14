"""Compile and run handwritten ceiling kernels with MSVC /O2.

Not IntentCompile. Uses intentc.target (INTENTC_VCVARS / vcvars64).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POC = HERE.parents[2] / "poc"
WORK = HERE / "_work"
sys.path.insert(0, str(POC))

from intentc.target import msvc_env  # noqa: E402

KERNELS = [
    "luma.c",
    "mag.c",
    "aos_soa.c",
    "innerprod.c",
    "box2d.c",
]


def cl_path(env: dict[str, str]) -> str:
    path = env.get("PATH") or env.get("Path")
    cl = shutil.which("cl", path=path) or shutil.which("cl.exe", path=path)
    if cl is None:
        raise FileNotFoundError("cl.exe not found after vcvars")
    return cl


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    env = msvc_env()
    cl = cl_path(env)
    print(f"cl={cl}", flush=True)
    ver = subprocess.run([cl], capture_output=True, text=True, env=env)
    banner = (ver.stderr or ver.stdout or "").strip().splitlines()
    if banner:
        print(f"cl_banner={banner[0]}", flush=True)
    cpu = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Processor).Name"],
        capture_output=True, text=True,
    )
    if cpu.returncode == 0 and cpu.stdout.strip():
        print(f"cpu={cpu.stdout.strip()}", flush=True)

    rc_all = 0
    for src_name in KERNELS:
        src = HERE / src_name
        stem = src.stem
        exe = WORK / f"{stem}.exe"
        obj = WORK / f"{stem}.obj"
        cmd = [
            cl, "/nologo", "/O2", "/W3", "/D_CRT_SECURE_NO_WARNINGS",
            str(src), f"/Fe:{exe}", f"/Fo:{obj}",
        ]
        if stem == "box2d" or stem == "aos_soa":
            cmd.extend(["/FAs", "/Fa" + str(WORK / f"{stem}.asm")])
        print(f"\n=== compile {src_name} ===", flush=True)
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(HERE))
        out = (p.stdout or "") + (p.stderr or "")
        if out.strip():
            print(out, end="" if out.endswith("\n") else "\n", flush=True)
        if p.returncode != 0:
            print(f"BUILD FAILED {src_name} rc={p.returncode}", flush=True)
            rc_all = 1
            continue
        print(f"=== run {exe.name} ===", flush=True)
        r = subprocess.run([str(exe)], capture_output=True, text=True, cwd=str(WORK), timeout=600)
        sys.stdout.write(r.stdout or "")
        if r.stderr:
            sys.stderr.write(r.stderr)
        if r.returncode != 0:
            print(f"RUN FAILED {exe.name} rc={r.returncode}", flush=True)
            rc_all = 1
    return rc_all


if __name__ == "__main__":
    raise SystemExit(main())
