/* Post: inner product on LEN samples from {0,1,2,3} matches a float MAC. */
#include <stdint.h>
#include "intent_params.h"

double inner(const float *data1, const float *data2, int n);
int32_t nondet_int32_t(void);

void harness(void) {
    float a[4], b[4];
    float acc = 0.0f;
    for (int i = 0; i < LEN; i++) {
        int32_t x = nondet_int32_t();
        int32_t y = nondet_int32_t();
        __CPROVER_assume(x >= 0 && x <= 3);
        __CPROVER_assume(y >= 0 && y <= 3);
        a[i] = (float)x;
        b[i] = (float)y;
        acc += a[i] * b[i];
    }
    __CPROVER_assert((float)inner(a, b, LEN) == acc, "inner product matches float MAC");
}
