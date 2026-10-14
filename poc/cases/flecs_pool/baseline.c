/* Sparse active-flag iteration (Flecs-style). Live entities receive +dt on x.
 * Dead slots must not change. alive[i] is 0 or 1. */
#include <stdint.h>

#define CAP 8

static int32_t x[CAP];
static int alive[CAP];

void pool_clear(void) {
    for (int i = 0; i < CAP; i++) {
        x[i] = 0;
        alive[i] = 0;
    }
}

int spawn(int32_t v) {
    for (int i = 0; i < CAP; i++) {
        if (!alive[i]) {
            x[i] = v;
            alive[i] = 1;
            return i;
        }
    }
    return -1;
}

void step(int32_t d) {
    for (int i = 0; i < CAP; i++) {
        if (alive[i]) x[i] += d;
    }
}

int32_t get_x(int i) { return x[i]; }
int is_alive(int i) { return alive[i]; }
