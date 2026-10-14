/* Block FIR (CMSIS-DSP-style). At least 5 outputs; extra outputs from a larger
 * block are allowed if they equal the convolution on the provided samples. */
#include <stdint.h>

#define BLOCK 5
#define TAPS 2

static int32_t x[32];
static int32_t h[TAPS];
static int32_t y[32];

void set_x(int i, int32_t v) { x[i] = v; }
void set_h(int k, int32_t v) { h[k] = v; }
int32_t get_y(int i) { return y[i]; }

void filter(void) {
    for (int i = 0; i < BLOCK; i++) {
        y[i] = x[i] * h[0] + x[i + 1] * h[1];
    }
}
