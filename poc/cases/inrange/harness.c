/* Post: in_range(dx^2+dy^2, R) agrees with the integer test dx^2+dy^2 < R^2. */
#include <stdint.h>
#include "intent_params.h"

int in_range(float d2, float R);
int32_t nondet_int32_t(void);

void harness(void) {
    int32_t dx = nondet_int32_t();
    int32_t dy = nondet_int32_t();
    int32_t R = nondet_int32_t();
    __CPROVER_assume(dx >= -RBOUND && dx <= RBOUND);
    __CPROVER_assume(dy >= -RBOUND && dy <= RBOUND);
    __CPROVER_assume(R >= 1 && R <= RBOUND);
    int32_t d2i = dx * dx + dy * dy;
    int got = in_range((float)d2i, (float)R);
    __CPROVER_assert(got == (d2i < R * R), "in-range iff squared length < R*R");
}
