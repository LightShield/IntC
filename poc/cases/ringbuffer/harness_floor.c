/* Post clause on theta: the harness sees CAPACITY through intent_params.h.
 * I in the skip contract is only CAPACITY >= 1000. This floor is not in I, so
 * CheckRealiz succeeds and CEGIS's closest power of two (1024) is a
 * counterexample. The next power of two that meets the floor is 2048. */
#include "intent_params.h"

void harness(void) {
    __CPROVER_assert(CAPACITY >= 2048, "CAPACITY at least 2048");
}
