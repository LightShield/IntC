/* Tick-to-millisecond conversion. Requirement: relative error versus tick/1000
 * of at most 2.5% for tick_us >= 640000 (truncation of integer division by a
 * power of two near 1000 is inside that bound only from this threshold). */
#include <stdint.h>

#define DIVISOR 1000
#define SHIFT 0

uint64_t sensor_tick_to_ms(uint64_t tick_us) {
    return tick_us / DIVISOR;
}
