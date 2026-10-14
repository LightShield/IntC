# Attribution — Flecs sparse entity iteration

- [SanderMertens/flecs](https://github.com/SanderMertens/flecs) tag **v3.2.8**, `78305c422e8694fa714b3b2957ff9245b7760c37`
- Upstream iterates components and skips inactive entities (sparse `alive` / generation).

**What we kept.** A dense array of slots with a per-slot live flag; the update is `x += d` only when live.

**What we changed.** C, integer `x`, CAP=8, no archetypes, no generation counters. We do **not** emit swap-and-pop compaction: that would reuse indices and needs a different `Post`. The rewrite is predication, `x[i] += d * alive[i]`, which is equivalent when `alive[i] ∈ {0,1}`.
