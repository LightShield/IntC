/* Post: one step implements x += vx * dt and y += vy * dt without overflow.
 * Proved at n = N = 4. The benchmark may run a larger N. */
#include <stdint.h>
#include "intent_params.h"

#ifndef N
#define N 4
#endif

void set_particle(int i, int32_t x, int32_t y, int32_t vx, int32_t vy);
int32_t get_x(int i);
int32_t get_y(int i);
void step(int n, int32_t dt);
int32_t nondet_int32_t(void);

void harness(void) {
    int32_t x[N], y[N], vx[N], vy[N];
    int32_t dt = nondet_int32_t();
    __CPROVER_assume(dt >= 0);
    __CPROVER_assume(dt <= 4);
    for (int i = 0; i < N; i++) {
        x[i] = nondet_int32_t();
        y[i] = nondet_int32_t();
        vx[i] = nondet_int32_t();
        vy[i] = nondet_int32_t();
        __CPROVER_assume(x[i] >= -1000 && x[i] <= 1000);
        __CPROVER_assume(y[i] >= -1000 && y[i] <= 1000);
        __CPROVER_assume(vx[i] >= -8 && vx[i] <= 8);
        __CPROVER_assume(vy[i] >= -8 && vy[i] <= 8);
        set_particle(i, x[i], y[i], vx[i], vy[i]);
    }
    step(N, dt);
    for (int i = 0; i < N; i++) {
        __CPROVER_assert(get_x(i) == x[i] + vx[i] * dt, "x += vx * dt");
        __CPROVER_assert(get_y(i) == y[i] + vy[i] * dt, "y += vy * dt");
    }
}
