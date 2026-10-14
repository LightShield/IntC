#include <stdint.h>
#include "intent_params.h"

void set_cmd(int i, int space, int32_t x, int32_t y);
int32_t eval_x(int i);
int32_t nondet_int32_t(void);
int nondet_int(void);

void harness(void) {
    for (int i = 0; i < N; i++) {
        int space = nondet_int();
        int32_t x = nondet_int32_t();
        __CPROVER_assume(space >= 0 && space <= 2);
        __CPROVER_assume(x >= -100 && x <= 100);
        set_cmd(i, space, x, 0);
        int32_t f = (space == 2) ? 2 : 1;
        __CPROVER_assert(eval_x(i) == x * f, "world doubles x; other spaces keep x");
    }
}
