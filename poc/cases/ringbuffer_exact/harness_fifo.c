/* Post: FIFO order; enqueue fails iff the ring holds CAPACITY packets.
 * STORAGE may be larger. Bounded: every sequence of up to K operations. */
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
    uint64_t model[K];
    unsigned mh = 0, mt = 0;
    for (int step = 0; step < K; step++) {
        if (nondet_bool()) {
            uint64_t pkt = nondet_uint64_t();
            bool ok = enqueue(pkt);
            bool expect = (mt - mh) < CAPACITY;
            __CPROVER_assert(ok == expect, "enqueue succeeds iff not full");
            __CPROVER_assert(STORAGE >= CAPACITY, "backing store covers logical capacity");
            if (ok) model[mt++] = pkt;
        } else {
            uint64_t got = 0;
            bool ok = dequeue(&got);
            __CPROVER_assert(ok == (mt != mh), "dequeue succeeds iff not empty");
            if (ok) { __CPROVER_assert(got == model[mh], "FIFO order"); mh++; }
        }
    }
}
