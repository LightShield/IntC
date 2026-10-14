/* Contract harness (Post): set semantics for every sequence of up to K operations
 * from an empty table. A successful insert makes the key a member; a member stays a
 * member; contains never reports a key that was not successfully inserted.
 * Insert may fail (probe limit), which the contract allows. */
#include <stdint.h>
#include <stdbool.h>
#include "intent_params.h"

#ifndef K
#define K 4
#endif

bool insert(uint64_t k);
bool contains(uint64_t k);
uint64_t nondet_uint64_t(void);
bool nondet_bool(void);

void harness(void) {
    uint64_t inserted[K];
    unsigned n = 0;
    for (int step = 0; step < K; step++) {
        uint64_t k = nondet_uint64_t();
        bool member = false;
        for (unsigned j = 0; j < n; j++) if (inserted[j] == k) member = true;
        if (nondet_bool()) {
            bool ok = insert(k);
            if (member) __CPROVER_assert(ok, "re-inserting a member succeeds");
            if (ok && !member) inserted[n++] = k;
        } else {
            bool got = contains(k);
            __CPROVER_assert(got == member, "contains reports exactly the successfully inserted keys");
        }
    }
}
