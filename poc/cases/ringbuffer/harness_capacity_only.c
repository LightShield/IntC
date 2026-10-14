/* Post: success/failure vs occupancy only. No FIFO assertion.
 * A LIFO stack with the same full/empty rules satisfies this harness. */
#include <stdint.h>
#include <stdbool.h>
#include "intent_params.h"

#ifndef K
#define K 6
#endif

extern uint64_t head, tail;
bool enqueue(uint64_t pkt);
bool dequeue(uint64_t *out);
uint64_t nondet_uint64_t(void);
bool nondet_bool(void);

void harness(void) {
    uint64_t base = nondet_uint64_t();
    head = base;
    tail = base;
    unsigned size = 0;
    for (int step = 0; step < K; step++) {
        if (nondet_bool()) {
            uint64_t pkt = nondet_uint64_t();
            bool ok = enqueue(pkt);
            bool expect = size < CAPACITY;
            __CPROVER_assert(ok == expect, "enqueue succeeds iff not full");
            if (ok) size++;
        } else {
            uint64_t got = 0;
            bool ok = dequeue(&got);
            __CPROVER_assert(ok == (size != 0), "dequeue succeeds iff not empty");
            if (ok) size--;
        }
    }
}
