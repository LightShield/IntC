/* Post: |1000 * got - tick| / tick <= 1/40 for ticks in the stated Pre. */
#include <stdint.h>

#include "intent_params.h"

uint64_t sensor_tick_to_ms(uint64_t tick_us);
uint64_t nondet_uint64_t(void);

void harness(void) {
    uint64_t tick = nondet_uint64_t();
    __CPROVER_assume(tick >= 640000ull);
    __CPROVER_assume(tick <= 0xffffffffull);
    uint64_t got = sensor_tick_to_ms(tick);
    uint64_t scaled = got * 1000ull;
    uint64_t diff = scaled >= tick ? scaled - tick : tick - scaled;
    __CPROVER_assert(diff * 40ull <= tick, "relative error versus tick/1000 is at most 2.5%");
    __CPROVER_assert(DIVISOR >= 1000, "divisor at least 1000");
}
