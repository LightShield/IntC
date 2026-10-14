# Artifact: IntC

This repository is the prototype C instance of IntentCompile used in the paper
*Compiling Against Intent* (https://github.com/LightShield/IntC). Admission is \(\models_K\) with CBMC 6.11.0.
Measurement and listings are MSVC 19.29 `/O2` on Windows.

## What a reviewer can do, by OS

- **Windows** with the pinned toolchain: full `python reproduce.py` (~12 minutes
  on the paper machine, an Intel Core i7-14700K).
- **Linux** (and any machine without VS 2019 `cl.exe`): `pip install`,
  `pytest tests` (core), `python reproduce.py --check`, and
  `--tex-only`. Linux cannot replay CBMC or ns/op: every CBMC call loads the
  MSVC environment (`intentc/verify/cbmc.py`).

Solver seconds are not bit-stable. Admit / timeout / counterexample outcomes,
rewrite names, and the shipped listing checks must match this README and
`experiments/eval/README.md`.

## Contents

| Path | Role |
|---|---|
| `poc/intentc/` | Compiler |
| `poc/cases/` | Contracts, C baselines, harnesses |
| `poc/reproduce.py` | One-command table rebuild |
| `experiments/eval/` | Catalog, ablation, timed JSON/TeX/ASM |
| `main.pdf` and TeX sources | Paper (optional to rebuild) |

Scratch: `_work/` (gitignored). Do not hand-edit `experiments/eval/*.tex`.

## Install (Windows, paper-faithful)

Working directory for every Python command: **`poc/`**.

1. **Python 3.13** (toml allows `>=3.10`; 3.13 matches the paper machine).
2. `pip install -e .[test]`
   (`z3-solver`, `tree-sitter`, `tree-sitter-cpp`, `pydantic`, `pyyaml`, `pytest`).
   There is no standalone Z3 binary; `import z3` is the wheel.
3. **CBMC 6.11.0** Windows MSI:
   https://github.com/diffblue/cbmc/releases/tag/cbmc-6.11.0
   — `cbmc-6.11.0-win64.msi`, SHA-256
   `8dcb29c2e91329898ecde5b79198dad2f4b5ebc5cb6b7d15e892c4fe26c6ea53`.
   Default path: `C:\Program Files\cbmc\bin\cbmc.exe`. Override: `INTENTC_CBMC`.
4. **Visual Studio Build Tools 2019**, C++ workload, so this file exists:
   `C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat`
   (`cl.exe` 19.29). Override: `INTENTC_VCVARS`. Flags used: `/nologo /O2 /EHsc /W3`.
5. No git LFS. `clang` on PATH is optional (extra LLVM listings only).

## Install (Linux / check-only)

Python `>=3.10` and `pip install -e .[test]` from `poc/`. Do not expect CBMC
to run: `verify()` always calls `msvc_env()`.

## Replay

```
pip install -e .[test]
python reproduce.py              # full tables; needs CBMC + MSVC
python reproduce.py --check      # outcomes vs shipped JSON/ASM; no CBMC
python reproduce.py --tex-only   # rebuild .tex from JSON; no CBMC
python -m pytest tests           # pipeline tests; not a substitute for reproduce.py
```

`--check` requires the shipped `experiments/eval/{catalog,ablations,workhorse}.json`,
`asif_slot.asm`, and `inrange_baseline.asm`.

## Expected outcomes (`--check` / full replay)

See `experiments/eval/README.md`. Short form:

- Catalog: fourteen rows admitted; rewrite names and proved/unknown/cex as in
  `catalog.tex`.
- Ablations: colliding `& 999` proved at \(K=4\), refuted at \(K=10\);
  occupancy-only proves a LIFO stack; 8016-byte ceiling emits \(P_1\).
- Timed contracts: ring `CAPACITY=1024`, hash `NBUCKETS=16384`; six rows
  winner median strictly below \(P_1\); FIR admitted `BLOCK=8` is slower,
  emit is \(P_1\).
- Listings: reciprocal multiply for `% 1000`; `and` 1023 for the mask;
  `sqrtss` on the in-range bench TU.

## Out of the one command

Spearman \(\rho\) (kappa), ceiling kernels, and the motivating slot
microbench are separate scripts. They need MSVC and are not required to
match `--check`.

## Rebuilding the PDF (optional)

TeX Live or MiKTeX with ACM `acmart` (not bundled). Tables are
`\input{experiments/eval/*.tex}`.

## Scope

Extracts are not whole-program compiles of DPDK, Zephyr, or OGRE. Another
compiler or CPU is another \(\mathcal{O}\).
