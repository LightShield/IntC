# Handwritten performance ceilings

**Not IntentCompile. Not paper pipeline numbers.** Expert-oracle C kernels timed on the paper machine.

Date: 2026-10-06.  
Machine: Intel Core i7-14700K, Windows.  
Compiler: MSVC 19.29.30157 (VS 2019 Build Tools), x64, `/O2` only (no `/fp:fast`, no `/arch:AVX2`). MSVC env via `poc/intentc/target/` (`INTENTC_VCVARS` / `vcvars64`).  
Sources: `experiments/eval/ceiling/*.c`. Replay: `python experiments/eval/ceiling/run_ceiling.py`. Build products go in `ceiling/_work/` (gitignored).

## Method

- QueryPerformanceCounter. 3 warmup runs discarded, then **15** timed trials. Table is the **median**. Times are **ns per element** (pixel, bin, particle-step, MAC, pair, or vector).
- P1 and P* of each pair are interleaved in the same process except magnitude, which times variants sequentially after a per-variant warmup.
- A checksum/sink consumes outputs so the loops are not DCE’d.
- Remainder-to-mask / pow2 capacity was not measured.

## Table

| Proposal | N | P1 ns/elem | P* ns/elem | ratio P1/P* | trials | Notes |
|---|---:|---:|---:|---:|---:|---|
| 1. OpenCV float BT.601 luma vs Q15 | 2,073,600 (1920×1080), 8 passes | 0.8656 | 0.5640 | **1.53×** | 15 | Packed 8-bit RGB. Float MAC promotes `uint8` in-loop (`0.299/0.587/0.114`). Q15 is `(9798*r+19235*g+3735*b)>>15`. |
| 2a. CMSIS mag `sqrtf` vs 1-iter rsqrt Newton | 1,048,576 bins, 4 passes | 0.8155 | 1.2140 | **0.67×** | 15 | P* is **slower**. Quake seed + one Newton, `mag = x*y`. |
| 2b. same vs 2-iter Newton | 1,048,576 | 0.8155 | 1.7679 | **0.46×** | 15 | Slower still. |
| 2c. same vs 3-iter Newton | 1,048,576 | 0.8155 | 2.3759 | **0.34×** | 15 | Slower still. CMSIS MVE’s extra iteration is not a win on this x86. |
| 2d. same vs α-max+β-min (α=1, β=3/8) | 1,048,576 | 0.8155 | 0.6770 | **1.20×** | 15 | Only mag variant faster than `sqrtf`. Small. Max rel \|P*−sqrtf\| on this buffer: n1=1.75e-3, n2=5e-6, n3=0 (at 1e-6), alphamax=6.80e-2. |
| 3. Fat AoS vs SoA Euler | 100,000 particles, 200 steps, 64-byte `Fat` | 1.2787 | 0.2984 | **4.29×** | 15 | Hot pos/vel, cold mass/acc/density/pressure. `__restrict` SoA. See layout note below. |
| 4a. Opus inner product double vs float accum | L=256, 200,000 dots | 0.4427 | 0.1356 | **3.26×** | 15 | SILK-shaped 4× unroll. ns/elem = ns/MAC. Sliding start of 32 to block LICM of one invariant dot. |
| 4b. same, longer | L=4096, 20,000 dots | 0.4443 | 0.1362 | **3.26×** | 15 | Same ratio as L=256. |
| 5a. Box2D `sqrt(d2)<R` vs `d2<R*R` | 1,000,000 pairs, 8 passes | 0.7043 | 0.1133 | **6.22×** | 15 | Boolean in-range, R=50. Counts matched (1,480,000). **MSVC did not fold** (listing still has `sqrtss`). |
| 5b. always-normalize vs skip-normalize | 1,000,000 unit vectors, 4 passes | 1.3010 | 0.5565 | **2.34×** | 15 | P1: `len=sqrtf(x*x+y*y); inv=1/len`. P*: copy already-unit `x,y`. |

Min–max of the 15 trials (same run):

| Kernel | min | median | max |
|---|---:|---:|---:|
| luma float | 0.8375 | 0.8656 | 0.8851 |
| luma Q15 | 0.5504 | 0.5640 | 0.5976 |
| mag sqrtf | 0.7816 | 0.8155 | 0.9760 |
| mag Newton1 | 1.1985 | 1.2140 | 1.3284 |
| mag Newton2 | 1.7204 | 1.7679 | 1.8523 |
| mag Newton3 | 2.2921 | 2.3759 | 2.5290 |
| mag α-max | 0.6425 | 0.6770 | 0.9095 |
| fat AoS | 1.2067 | 1.2787 | 1.3369 |
| SoA | 0.2768 | 0.2984 | 0.3187 |
| inner double L256 | 0.4229 | 0.4427 | 0.4526 |
| inner float L256 | 0.1292 | 0.1356 | 0.1395 |
| inner double L4096 | 0.4290 | 0.4443 | 0.4702 |
| inner float L4096 | 0.1303 | 0.1362 | 0.1408 |
| in-range sqrt | 0.6941 | 0.7043 | 0.7317 |
| in-range sq | 0.1046 | 0.1133 | 0.1470 |
| normalize always | 1.2806 | 1.3010 | 1.3605 |
| normalize skip | 0.5408 | 0.5565 | 0.5931 |

No build failed on this run. Box2D `/Fa:path` with an extra colon failed once (`fatal error C1083`); the runner now uses `/Fa` + path without that colon, and the kernel built.

## As-if

- **(1)(2)(4) change bits.** Compilers do not retarget `float` MAC to Q15, `sqrtf` to Newton/α-max, or `double` accum to `float`. On this luma buffer, u8 destinations happened to match (max abs diff 0); that does not make the rewrite as-if-legal. Inner-product one-dot `|float−double|` printed as 0 at `%.6e`; the many-rep sinks still diverged (`sink_d=1.80287e8`, `sink_f=1.80297e8`).
- **(3) is layout.** Observational index API. MSVC/Clang `/O2` do not SoA-convert structs.
- **(5a) may be as-if-legal** if a compiler proves `R≥0` and `d2≥0` and rewrites `sqrt(d2)<R` into `d2<R*R`. LLVM InstCombine is the known risk. **MSVC 19.29 /O2 did not:** `inrange_sqrt` still executes `sqrtss` (with a `sqrtf` call if `d2<0`); `inrange_sq` is SSE `mulps`/`cmpltps`. The 6.2× ceiling on this machine is therefore “drop sqrt **and** get a vectorized compare,” not a fold that as-if already spent.
- **(5b)** skip-normalize is a Pre / don’t-care (`||v||≈1`). A non-unit input would diverge.

## Layout measurement (proposal 3)

An earlier fused `for s: for i` kernel was **not** used in the table. MSVC `/O2` interchanged it into a per-particle inner loop of 200 register adds for AoS (velocity is invariant, so `x += vx` stays in registers), while SoA still did 200 memory RMWs. That made AoS look ~12× *faster* than SoA — an interchange artifact, not a bandwidth ceiling.

The table uses `__declspec(noinline)` one-pass `step_*_once` called 200 times, so each Euler step actually walks memory. Listing check: `call step_aos_once` / `call step_soa_once`; SoA is 4-wide `pmulld`/`paddd` on contiguous arrays; AoS gathers `movd` from a 64-byte stride. `sizeof(Fat)=64`. This is the Godot/PARSEC-scale layout ceiling at N=1e5, not the N=4 catalog toy.

Without `__restrict` on the six SoA pointers, MSVC also stayed scalar on SoA. The expert SoA in the table is the non-aliasing one.

## How to read these ceilings

These ratios are **upper bounds on a microkernel**, one machine, one compiler. They are not IntentCompile speedups.

- **Largest measured P1/P\*:** 5a in-range 6.22× (with the LLVM-fold caveat), then 3 layout 4.29×, then 4 inner-product 3.26×.
- **Newton mag is a negative result on this i7** (`sqrtss` beats software rsqrt+Newton). α-max is only 1.20×.
- Static `/FAs` opcode count of the specialized `mag_newton1` PROC is **43** against **45** for `mag_sqrtf` (prolog included). That ranking would emit Newton. The inner `$LL9` trip is the longer loop.
- **Luma Q15 is 1.53×**, medium, not maybe-flat.
- **5b skip-normalize is 2.34×** (copy vs hypot).
