# Real-world kernel catalog

C extractions of the hot loop, contracts a developer could have written, and
rewrites the compiler actually applies. SHAs below are peeled commits of
release tags from `git ls-remote` on 2026-10-06.

| Extract | Upstream | Tag / ref | Peeled commit | Case | Rewrite | C vs upstream |
|---|---|---|---|---|---|---|
| DPDK / Folly SPSC ring | [DPDK/dpdk](https://github.com/DPDK/dpdk) `lib/ring/rte_ring.h`; Folly `ProducerConsumerQueue.h` | DPDK `v23.11` | `eeb0605f118dae66e80faa44f7b3e88748032353` | `cases/ringbuffer/` | pow2-mask, pad-and-mask | C FIFO; no atomics, no multi-producer. Capacity ≥ 1000 is the intent (burst headroom), not bitwise identity with `% 1000`. |
| ClickHouse hash probe | [ClickHouse/ClickHouse](https://github.com/ClickHouse/ClickHouse) `src/Common/HashTable/HashTable.h` | `v24.3.2.23-lts` | `8b7d910960cc2c6a0db07991fe2576a67fe98146` | `cases/hashset/` | pow2-mask | Open addressing in C. Insert may fail (probe limit). Prime 10007 is incidental; `NBUCKETS >= 10007` is the load-factor intent. |
| PARSEC particles | [cirosantilli/parsec-benchmark](https://github.com/cirosantilli/parsec-benchmark) fluidanimate kinematics | tag `3.0` | `b758a0ed159c1b5f854147c8915f360fac195820` | `cases/particles/` | aos-to-soa | Integer positions; N ≤ 4 for BMC. Layout is not in the index API. |
| PARSEC particles (fat) | same fluidanimate kinematics, 64-byte record | tag `3.0` | `b758a0ed159c1b5f854147c8915f360fac195820` | `cases/particles_fat/` | aos-to-soa | Prove `step(n)` at n=4. Measure N=100000. Cold mass/acc/density/pressure fields. |
| Box2D in-range | [erincatto/box2d](https://github.com/erincatto/box2d) length vs radius | tag `v3.1.0` | `d5935a7a1853eb0f4aca92b369f37929d02c7e11` | `cases/inrange/` | squared-compare | `sqrtf(d2)<R` vs `d2<R*R`. Integer BMC harness. No GJK. |
| Opus inner product | [xiph/opus](https://github.com/xiph/opus) `silk/float/inner_product_FLP.c` | tag `v1.5.2` | `ddbe48383984d56acd9e1ab6a090c54ca6b735a6` | `cases/innerprod/` | narrow-accum | Double accum → float. No 4× unroll. LEN=4 for BMC. |
| OpenCV BT.601 luma | [opencv/opencv](https://github.com/opencv/opencv) `color.simd_helpers.hpp` | tag `4.10.0` | `71d3237a093b60a27601c20e9ee6c3e52154e8b1` | `cases/luma/` | luma-q15 | Float MAC → Q15. Post \|Y−Q15\| ≤ 1. NPX=4. |
| Zephyr tick → ms | [zephyrproject-rtos/zephyr](https://github.com/zephyrproject-rtos/zephyr) | `v3.6.0` | `468eb56cf242eedba62006ee758700ee6148763f` | `cases/decimation/` | pow2-shift | Isolated integer conversion. 2.5% vs `/1000` for ticks ≥ 640000 (truncation bound, not a silent CBMC cut). |
| Flecs sparse pool | [SanderMertens/flecs](https://github.com/SanderMertens/flecs) sparse/entity iteration | `v3.2.8` | `78305c422e8694fa714b3b2957ff9245b7760c37` | `cases/flecs_pool/` | predicated-update | `if (alive[i]) x[i]+=d` → multiply by 0/1 flag. Swap-and-pop dense packing is **not** generated (ids would change). |
| MachSuite 2D stencil | [breagen/MachSuite](https://github.com/breagen/MachSuite) `stencil/stencil2d` | `master` (no release tag) | `6236e593012cb86b0d2f08d9fb9ba0411ff989b4` | `cases/stencil1d/` | halo-1d | 1D 3-point integer stencil, N=4. 2D float 128×128 is out of BMC. Zero Dirichlet edges. |
| CMSIS-DSP FIR | [ARM-software/CMSIS-DSP](https://github.com/ARM-software/CMSIS-DSP) `arm_fir_f32.c` | `v1.15.0` | `8f8bb8d56b346274c9b2918928f2d5c3dae51758` | `cases/fir_block/` | align-loop-bound | Integer taps, BLOCK ≥ 5 rounded to a multiple of 4. No SIMD. Catalog CI contract has no objective (emit BLOCK=8). Timed `contract.yaml` ranks one `filter()` call and keeps P1. |
| OGRE TransformSpace | [OGRECave/ogre](https://github.com/OGRECave/ogre) `OgreNode.h` | `v14.2.5` | `0d90297a387f5eb0d6cfa9e5ab17879bb0123316` | `cases/ogre_pack/` | narrow-int-field | `int space` → `uint8_t`. Three tags (local/parent/world). No C++ enum class. |
| MachSuite SpMV ELLPACK | same MachSuite `spmv/crs` | `master` | `6236e593012cb86b0d2f08d9fb9ba0411ff989b4` | *not in catalog* | — | CRS→ELLPACK would be a format-specific dump, not a syntactic rewrite we can check. Left out. |
| Folly (secondary ring) | [facebook/folly](https://github.com/facebook/folly) | `v2024.03.18.00` | `8aceb9bf727c42de013dd3fff8c89bd5d75ff11b` | cited from ringbuffer | (same) | Power-of-two size is Folly's own documented requirement. |

Each case directory has `ATTRIBUTION.md` with the same facts and the manipulations.
