#include <stdint.h>
#include "intent_params.h"

void set_x(int i, int32_t v);
void set_h(int k, int32_t v);
int32_t get_y(int i);
void filter(void);
int32_t nondet_int32_t(void);

void harness(void) {
    int32_t xs[20];
    int32_t hs[2];
    for (int k = 0; k < TAPS; k++) {
        hs[k] = nondet_int32_t();
        __CPROVER_assume(hs[k] >= -2 && hs[k] <= 2);
        set_h(k, hs[k]);
    }
    for (int i = 0; i < BLOCK + TAPS; i++) {
        xs[i] = nondet_int32_t();
        __CPROVER_assume(xs[i] >= -8 && xs[i] <= 8);
        set_x(i, xs[i]);
    }
    filter();
    for (int i = 0; i < BLOCK; i++) {
        __CPROVER_assert(get_y(i) == xs[i] * hs[0] + xs[i + 1] * hs[1],
                         "FIR output is the 2-tap convolution");
    }
}
