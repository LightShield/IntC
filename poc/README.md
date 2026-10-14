# IntC

Integrity: `DESIGN.md`. Claim map: `CLAIMS.md`. Owned packages at the
`intentc/` root; stage drivers `s1..s7`; catalogs under
`theory_lowering/rules` and `pool/strategies`.

## Requirements

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.13 | pipeline |
| packages | `pyproject.toml` | z3-solver, tree-sitter-cpp, pydantic, pyyaml, pytest |
| CBMC | 6.11.0 | `V` |
| MSVC | 19.29 x64 | preprocessor, sizeof, benchmarks |

`INTENTC_CBMC` overrides the binary in `intentc/verify/cbmc.py`. `INTENTC_VCVARS` overrides `vcvars64` in `intentc/target/`.

## Layout

```
poc/
├── intentc/main.py
├── intentc/pipeline/          # compile_intent, Context
├── intentc/contract/          # Phi YAML, parameter constraints I
├── intentc/syntax/            # C text, CST edits, Sketch
├── intentc/verify/            # CBMC V
├── intentc/target/            # L_Target: cl env, sizeof, bench
├── intentc/stages/s1 … s7
├── intentc/stages/theory_lowering/
├── intentc/stages/pool/strategies/
├── cases/ringbuffer/          # logical-parameter slack (CAPACITY ≥ 1000)
├── cases/ringbuffer_exact/    # physical slack (CAPACITY fixed, STORAGE ≥ CAPACITY)
├── cases/hashset/
├── cases/decimation/          # output slack (error vs tick/1000)
├── cases/scale/               # multiply-to-shift (GAIN in [8,16])
├── cases/particles/           # AoS→SoA (GeneratePool after TheoryLower stuck)
├── cases/particles_fat/       # same layout rewrite, 64-byte record, measure-large
├── cases/inrange/             # sqrt compare → squared (Box2D-style)
├── cases/innerprod/           # double accum → float (Opus-style)
├── cases/luma/                # BT.601 float MAC → Q15
├── cases/flecs_pool/          # sparse alive[] predication (Flecs)
├── cases/stencil1d/           # 1D halo (MachSuite stencil reduced)
├── cases/fir_block/           # FIR block % 4 (CMSIS-DSP)
├── cases/ogre_pack/           # uint8_t space tag (OGRE Node)
├── cases/loopsum/             # TheoryLower stuck (no remainder/divisor rewrite)
├── cases/real_world/CATALOG.md
├── cases/ringbuffer/handwritten/stack.c
├── eval_listings.py           # parse /FAs for paper evidence (not the compiler)
├── reproduce.py
└── tests/
```

## Implemented vs designed

| Component | Status |
|---|---|
| CBMC proved / counterexample / unknown | implemented, tested |
| CheckRealiz (`I` sat, unsat core) | implemented, tested |
| TheoryLower, Pow2Mask, Pow2Shift, Pow2Mul | implemented, tested |
| TheoryLower stuck (no applicable rewrite) | implemented, tested |
| CEGIS (enumerative, CBMC each value) | implemented, tested |
| CEGIS stops on unknown | implemented, tested |
| CEGIS excludes a counterexample | implemented, tested |
| CEGIS attempt cap | implemented, tested |
| BudgetNormalize (compiled sizeof; miss → baseline) | implemented, tested |
| GeneratePool | pad, narrow-int, SoA, align×4, predicate, halo-1d, squared-compare, narrow-accum, luma-q15; runs after empty seeds |
| Winner selection (MSVC median, or first seed if no bench) | implemented, tested |
| Emit with proof/measurement banner | implemented |
| Weak Post admits LIFO | tested (hand-written stack) |
| Physical slack (two-parameter baseline) | implemented, tested |
| Introduce STORAGE from a one-parameter ring | pad-and-mask, tested |
| AoS to SoA | tested (particles, particles_fat) |
| Squared length compare | tested (inrange) |
| Narrow float accum | tested (innerprod) |
| BT.601 luma Q15 | tested (luma) |
| Predicated sparse update | tested (flecs_pool) |
| 1D halo | tested (stencil1d) |
| Loop-bound align ×4 | tested (fir_block) |
| Narrow int field | tested (ogre_pack) |
| Inductive unbounded FIFO | not implemented |

## Running

```
pip install -e .[test]
python -m pytest tests
python reproduce.py
```

`reproduce.py` is the paper-table command (catalog, ablations, workhorse, MSVC listing). About 12 minutes. See `../experiments/eval/README.md`.

```
python -m intentc.main cases/ringbuffer/contract_ci.yaml -o tmp/out.c
python -m intentc.main cases/ringbuffer/baseline.c cases/ringbuffer/contract_ci.yaml -o tmp/out.c
python -m intentc.main cases/ringbuffer_exact/contract_ci.yaml -o tmp/exact.c
python -m intentc.main cases/decimation/contract.yaml -o tmp/decim.c
```

The two-argument form rejects a source that is not the contract's baseline (exit 2).
A stage failure before emit still writes the baseline and exits 1.
