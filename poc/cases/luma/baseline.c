/* Rec. 601 luma: Y = 0.299 R + 0.587 G + 0.114 B on 8-bit channels.
 * Requirement: Y is within 1 of the Q15 integerization of that formula.
 * The float MAC is incidental. */
#include <stdint.h>

#define NPX 4

void luma(const uint8_t *rgb, uint8_t *gray, int n) {
    for (int i = 0; i < n; i++) {
        gray[i] = (uint8_t)(0.299f * (float)rgb[3 * i + 0]
            + 0.587f * (float)rgb[3 * i + 1]
            + 0.114f * (float)rgb[3 * i + 2]);
    }
}
