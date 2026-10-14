#include "intent_params.h"

int sum(void);
int nondet_int(void);
extern int a[];

void harness(void) {
    int expect = 0;
    for (int i = 0; i < N; i++) {
        a[i] = nondet_int();
        __CPROVER_assume(a[i] >= -100 && a[i] <= 100);
        expect += a[i];
    }
    __CPROVER_assert(sum() == expect, "sum of a");
}
