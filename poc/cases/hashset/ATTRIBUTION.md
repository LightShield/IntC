# Attribution — ClickHouse hash table probe

- `src/Common/HashTable/HashTable.h`, tag **v24.3.2.23-lts**, peeled commit `8b7d910960cc2c6a0db07991fe2576a67fe98146`
  https://github.com/ClickHouse/ClickHouse

**What we kept.** Bucket index from `hash % NBUCKETS` and linear probing.

**What we changed.** C open-addressing set. Probe limit 4. Insert may fail. Integer keys. `NBUCKETS` starts at 10007 (a prime). Upstream uses power-of-two tables with a mask when configured that way; our contract is the load-factor floor `NBUCKETS >= 10007`, not “must remain prime.”
