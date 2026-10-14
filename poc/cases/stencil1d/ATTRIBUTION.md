# Attribution — MachSuite stencil

- [breagen/MachSuite](https://github.com/breagen/MachSuite) `stencil/stencil2d/stencil.c`
- No release tag on the repo. Recorded **master** `6236e593012cb86b0d2f08d9fb9ba0411ff989b4` on 2026-10-06 via `git ls-remote`.

**What we kept.** A neighbourhood stencil whose edges are a special case (here Dirichlet 0).

**What we changed.** 1D, integer, N=4. Upstream is a 2D 9-point float stencil on 128×128. Halo padding of a 2D grid is the same idea (ghost cells, branch-free interior) but that grid is not what CBMC checks here.
