/* 1D 3-point stencil with zero Dirichlet edges (MachSuite stencil reduced to 1D). */
#include <stdint.h>

#define N 4

static int32_t in[N];
static int32_t out[N];

void set_in(int i, int32_t v) { in[i] = v; }
int32_t get_out(int i) { return out[i]; }

void stencil(void) {
    for (int i = 0; i < N; i++) {
        int32_t l = (i == 0) ? 0 : in[i - 1];
        int32_t r = (i == N - 1) ? 0 : in[i + 1];
        out[i] = in[i] + l + r;
    }
}
