# Attribution — inner product (double accum on float)

- Shape of `silk_inner_product_FLP` in [xiph/opus](https://github.com/xiph/opus)
  `silk/float/inner_product_FLP.c`. Tag used for the catalog table is in
  `cases/real_world/CATALOG.md`.

**What we kept.** Dot product of two float buffers with a wider accumulator.

**What we changed.** C, no 4× unroll (the rewrite only narrows the accum).
BMC length LEN=4 with integer-valued operands so float and double MACs agree.
No silk residual, no SSE.
