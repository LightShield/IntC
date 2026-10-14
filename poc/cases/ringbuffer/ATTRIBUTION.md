# Attribution — DPDK / Folly ring (this directory is `cases/ringbuffer`)

- DPDK `lib/ring/rte_ring.h`, release **v23.11**, peeled commit `eeb0605f118dae66e80faa44f7b3e88748032353`
  https://github.com/DPDK/dpdk
- Folly `folly/ProducerConsumerQueue.h`, tag **v2024.03.18.00**, `8aceb9bf727c42de013dd3fff8c89bd5d75ff11b`
  https://github.com/facebook/folly

**What we kept.** Slot index from a monotonic counter; FIFO enqueue/dequeue; fixed backing store.

**What we changed.** C, not C++. No `rte_atomic`, no multi-producer. Counters are plain `uint64_t`. Capacity starts at 1000 (not a power of two). DPDK and Folly already require power-of-two sizes in the upstream headers; the point of the contract is that a *developer who only needed ≥ 1000 slots* should not have to write that requirement as a bitwise identity with `% 1000`.
