#include <stdint.h>
#include "intent_params.h"

void pool_clear(void);
int spawn(int32_t v);
void step(int32_t d);
int32_t get_x(int i);
int is_alive(int i);
int32_t nondet_int32_t(void);
int nondet_int(void);

void harness(void) {
    pool_clear();
    int32_t v0 = nondet_int32_t();
    int32_t v1 = nondet_int32_t();
    int32_t d = nondet_int32_t();
    __CPROVER_assume(v0 >= -50 && v0 <= 50);
    __CPROVER_assume(v1 >= -50 && v1 <= 50);
    __CPROVER_assume(d >= -4 && d <= 4);
    int i0 = spawn(v0);
    int i1 = spawn(v1);
    __CPROVER_assert(i0 >= 0 && i1 >= 0 && i0 != i1, "two live slots");
    step(d);
    __CPROVER_assert(get_x(i0) == v0 + d, "live slot 0 updated");
    __CPROVER_assert(get_x(i1) == v1 + d, "live slot 1 updated");
    for (int i = 0; i < CAP; i++) {
        if (i != i0 && i != i1) {
            __CPROVER_assert(get_x(i) == 0, "dead slot unchanged");
            __CPROVER_assert(is_alive(i) == 0, "dead stays dead");
        }
    }
}
