# Attribution — fat particle Euler (layout)

- Same PARSEC fluidanimate kinematics as `cases/particles/`, with a 64-byte
  record (hot pos/vel, cold mass/acc/density/pressure). Upstream tag in
  `cases/particles/ATTRIBUTION.md`.

**What we kept.** Per-particle Euler step on position from velocity.

**What we changed.** Sixteen scalar `int32_t` fields so AoS→SoA applies
(array fields would skip). `step(n, dt)` so the harness can prove n=4 while
`bench.c` defines N=100000. The driver calls `step` through a volatile
function pointer so MSVC `/O2` does not interchange a fused step loop into a
per-particle register chain.
No SPH.
