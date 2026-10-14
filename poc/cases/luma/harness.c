/* Post: each Y is within 1 of (9798 R + 19235 G + 3735 B) >> 15. */
#include <stdint.h>
#include "intent_params.h"

void luma(const uint8_t *rgb, uint8_t *gray, int n);
uint8_t nondet_uint8_t(void);

void harness(void) {
    uint8_t rgb[12], gray[4];
    for (int i = 0; i < NPX; i++) {
        rgb[3 * i + 0] = nondet_uint8_t();
        rgb[3 * i + 1] = nondet_uint8_t();
        rgb[3 * i + 2] = nondet_uint8_t();
    }
    luma(rgb, gray, NPX);
    for (int i = 0; i < NPX; i++) {
        int yq = (9798 * rgb[3 * i] + 19235 * rgb[3 * i + 1] + 3735 * rgb[3 * i + 2]) >> 15;
        int d = (int)gray[i] - yq;
        if (d < 0) d = -d;
        __CPROVER_assert(d <= 1, "luma within 1 of Q15 BT.601");
    }
}
