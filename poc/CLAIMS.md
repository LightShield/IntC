# Paper claims → evidence

**Source of truth is the PDF.** A row is a sentence a reviewer can attack. Column 2 is what would **falsify** it.

If you add a paper sentence, add a row first. If column 2 is empty, cut or hedge the sentence.

Status: **test** · **recorded** · **proof** · **scope**

Solver **seconds** in catalog cells are not claims. `reproduce.py --check` pins outcomes, rewrite names, timed winner-faster-than-\(P_1\) with 31-trial stats, the ten-instruction remainder listing, and `sqrtss` on the in-range bench TU.

---

## Empirical

| Claim | Falsify with |
|---|---|
| Catalog: 14 rows admitted; rewrite names and proved/unknown/cex as in `catalog.tex` | `python reproduce.py --check`; `test_catalog_e2e` |
| Ring P1 `% 1000` unknown at CI timeout; winner mask proved | `catalog.json` ring P1_V; `test_mask_1024_proved` |
| Hash P1 unknown; winner NBUCKETS=16384 proved | `test_hashset_pipeline_emits_mask`; catalog/workhorse JSON |
| Luma P1 unknown/60 s; Q15 proved/0.1 s | `catalog.json` luma; `test_luma_pipeline_emits_q15` |
| Particles S2 fails; GeneratePool still admits SoA | `test_particles_pipeline_emits_soa_after_theory_lower_stuck`; `--check` `S2_ok` |
| Timed ns/op: six rows have winner median strictly below \(P_1\); FIR admits BLOCK=8 slower than \(P_1\) and emits \(P_1\); 31 trials, median ± sample stdev | `workhorse.json` + `--check` loop; Table `tab:timed` |
| Slot microbench 2.67 vs 0.39 (6.8×) and 0.52 vs 0.17 (3.1×) | §7 as-if slot paragraph; `asif_slot.asm` |
| Remainder-by-1000 is ten instructions before `ret`; `% 1024` is `and …, 1023` | `test_slot_1000_listing_has_ten_instructions_before_ret` (`eval_listings.py`); `ablations.json` asif flags; `asif_slot.asm` |
| MSVC `/O2` emits `sqrtss` on the in-range **bench TU** | `test_inrange_bench_tu_emits_sqrtss`; `test_inrange_baseline_listing_has_sqrtss`; `inrange_baseline.asm` |
| `& 999` proved at K=4, FIFO cex at K=10 | `test_mask_with_non_pow2_capacity_is_refuted` |
| Occupancy-only proves LIFO; FIFO refutes it | `test_capacity_only_harness_accepts_stack`; `test_fifo_harness_refutes_stack` |
| 8016 B drops 1024-slot mask; emit P1 | `test_tight_memory_keeps_baseline` |
| Baseline `% 1000` timeout 300 s at K=4,6,8 (sweep); 120 s on CI | `catalog.json` ring P1_V; §7 ring timed paragraph |
| Without `--arrays-uf-always`, K=3 times out at 120 s | §7 / implementation notes in the PDF |
| Timed ring proved ~47 s at K=10 | `workhorse.json` |
| κ vs CBMC time Spearman ρ=0.11; timeouts still have a non-pow2 remainder | §7 TheoryLower-score paragraph |
| CEGIS ring CAPACITY=1024; hash 16384; scale GAIN=8 SH_GAIN=3; decimation SHIFT=10; physical STORAGE=1024 CAPACITY=1000 | matching `test_*_pipeline_*` |
| Inrange / innerprod / luma / fat SoA admitted with the named rewrites | `test_inrange_*`, `test_innerprod_*`, `test_luma_*`, `test_particles_fat_*` |
| Integer `/1024` misses the 2.5% bound at tick=599000; holds at 600000 and at the Pre floor 640000 | `test_div1024_misses_2_5_percent_below_pre_floor` |
| Ceiling inrange 6.22× / fat 4.29× / inner 3.26× | `CEILING_MEASUREMENTS.md`. **Not** IntentCompile |

---

## Mechanism

| Claim | Falsify with |
|---|---|
| CheckRealiz: \(\mathcal{I}\) sat / unsat core; missing `#define` emits P1 | `test_check_realiz_*` |
| Vacuous contract: no harness rejected | `test_contract_requires_a_harness` |
| `% N` → mask + `is_pow2`; literals not rewritten | `test_pow2_mask_*` |
| `/ D` → `>> SHIFT` + `pow2_pair` | `test_pow2_shift_*` |
| `* M` → `<< SH_M` + hole | `test_pow2_mul_*` |
| Pad-and-mask introduces STORAGE on a one-parameter ring | `test_pad_and_mask_*`; `test_generate_pool_adds_physical_pad_*` |
| Unknown ≠ proved (unwind too small) | `test_too_small_unwind_is_unknown_not_proved` |
| Mixed unwind + property failure is unknown | `test_mixed_unwind_and_property_failure_is_unknown` |
| Mask/shift rewrites parenthesize under `==` and `+` | `test_pow2_mask_parenthesizes_under_equality`; `test_pow2_mul_parenthesizes_under_add` |
| Squared compare preserves `R < sqrtf(d2)` | `test_squared_compare_bound_lt_sqrt` |
| CEGIS: unknown stops, does not refute; cex excludes 1024 then 2048; attempt cap stops after one cex | `test_cegis_unknown_*`; `test_cegis_excludes_*`; `test_cegis_attempt_cap_*` |
| sizeof is compiled | `test_static_memory_is_compiled_sizeof` |
| Impossible budget still emits P1 | `test_impossible_budget_still_emits_baseline` |
| TheoryLower stuck (loopsum) emits P1 | `test_theory_lower_stuck_emits_baseline` |
| GeneratePool starts from P1 after empty seeds | `test_particles_pipeline_emits_soa_*` |
| Winner measures both binaries; strictly faster candidate wins; equal median keeps \(P_1\) | `test_winner_selection_measures_pool`; `test_winner_takes_strictly_faster_candidate`; `test_winner_prefers_baseline_on_equal_median` |
| Unparseable source rejected | `test_unparseable_source_is_rejected` |
| SoA / predication / halo / align×4 / uint8 space / squared-compare / narrow-accum / luma-q15 | matching `test_*` in `test_core` + `test_tools` |
| Admission is \(\models_K\) (CBMC, UB checks, unwinding assertions) | `intentc/verify/cbmc.py` + unknown/cex tests |
| Fallback emit is baseline source | `test_unsat_contract_emits_baseline` |

---

## Theorems (not pytest)

`prop:refine`, `prop:expansion`, `lem:lowering`, `thm:restricted`, `thm:cegis`, TheoryLower termination. Falsify by finding a hole in `appendix.tex`. Compiler-correctness of MSVC is **trusted**.

---

## Scope (must not grow into a positive claim)

| Must not claim | Where said |
|---|---|
| We compiled DPDK / Zephyr / OGRE / Opus / OpenCV / Box2D whole | §7, DAS |
| Inductive / unbounded FIFO | DAS, §7 bounded-gap, §9 |
| CRS→ELLPACK, linked queue, Flecs swap-and-pop | §7 failures |
| False-sharing ratio, concurrent ring | §7 unnamed cost |
| Newton rewrite is in IntentCompile or in Table timed | §7 |
| Catalog ns/op | catalog Timed column is empty |
| LLVM folded or left `sqrt` on the in-range extract | §7: not reported |
| Measurements on more than MSVC 19.29 / one i7 | §6–§7 scope |
| Solver seconds are stable | §7 opener |

Catalog table cells: `catalog.json` + `--check` + `test_catalog_e2e`. Re-run `reproduce.py` to refresh seconds; do not hand-edit `catalog.tex`.
