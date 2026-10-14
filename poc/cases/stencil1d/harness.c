#include <stdint.h>
#include "intent_params.h"

void set_in(int i, int32_t v);
int32_t get_out(int i);
void stencil(void);
int32_t nondet_int32_t(void);

void harness(void) {
    int32_t a[N];
    for (int i = 0; i < N; i++) {
        a[i] = nondet_int32_t();
        __CPROVER_assume(a[i] >= -20 && a[i] <= 20);
        set_in(i, a[i]);
    }
    stencil();
    for (int i = 0; i < N; i++) {
        int32_t l = (i == 0) ? 0 : a[i - 1];
        int32_t r = (i == N - 1) ? 0 : a[i + 1];
        __CPROVER_assert(get_out(i) == a[i] + l + r, "3-point stencil with zero edges");
    }
}
