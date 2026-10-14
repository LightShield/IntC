/* Post: output equals sample * GAIN on 16-bit samples (no unsigned wrap). */
#include <stdint.h>
#include "intent_params.h"

uint32_t apply_gain(uint32_t sample);
uint32_t nondet_uint32_t(void);

void harness(void) {
    uint32_t sample = nondet_uint32_t();
    __CPROVER_assume(sample <= 0xffffu);
    uint32_t got = apply_gain(sample);
    __CPROVER_assert(got == sample * (uint32_t)GAIN, "output is sample times GAIN");
    __CPROVER_assert(GAIN >= 8, "gain at least 8");
    __CPROVER_assert(GAIN <= 16, "gain at most 16");
}
