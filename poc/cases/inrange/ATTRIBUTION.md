# Attribution — pairwise in-range (length vs radius)

- Box2D-style disk test: `sqrt(dx*dx+dy*dy) < R` vs the squared form used in
  collision code (`b2LengthSquared` / radius squared). Upstream:
  [erincatto/box2d](https://github.com/erincatto/box2d). Tag used for the
  catalog table is recorded in `cases/real_world/CATALOG.md` if `git ls-remote`
  succeeded; the rewrite does not mention Box2D.

**What we kept.** Boolean in-range of a 2D offset against a radius.

**What we changed.** C, one function `in_range(d2, R)`, integer BMC harness
with `|dx|,|dy|,R| <= RBOUND`. No manifold, no GJK, no time of impact.
`sqrtf` is incidental; Post is `dx^2+dy^2 < R^2`.
