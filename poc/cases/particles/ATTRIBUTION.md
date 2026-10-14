# Attribution — PARSEC fluidanimate kinematics

- [cirosantilli/parsec-benchmark](https://github.com/cirosantilli/parsec-benchmark) tag **3.0**, `b758a0ed159c1b5f854147c8915f360fac195820`
- Hot loop: particle `pos += vel * dt` (AoS in the upstream cell/particle structs).

**What we kept.** Per-particle Euler step on position from velocity.

**What we changed.** C, `int32_t` fields, N ≤ 4, index API (`set_particle` / `get_x`) so the harness does not mention AoS vs SoA. No SPH density/pressure. Float fluidanimate at 10k particles is not BMC-feasible; the layout rewrite is what we check.
