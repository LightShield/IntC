/* 1920*1080, 8 passes. Prints ns/pixel. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <windows.h>
#define NPIX (1920 * 1080)
#define STEPS 8
#include "candidate.c"

static uint8_t rgb[NPIX * 3];
static uint8_t gray[NPIX];
static volatile uint32_t sink;

int main(int argc, char **argv) {
    int trials = argc > 1 ? atoi(argv[1]) : 15;
    LARGE_INTEGER f, t0, t1;
    QueryPerformanceFrequency(&f);
    for (int i = 0; i < NPIX; i++) {
        rgb[3 * i + 0] = (uint8_t)(i * 13u);
        rgb[3 * i + 1] = (uint8_t)(i * 29u);
        rgb[3 * i + 2] = (uint8_t)(i * 47u);
    }
    for (int w = 0; w < 3; w++) {
        luma(rgb, gray, NPIX);
        uint32_t cs = 0;
        for (int i = 0; i < NPIX; i++) cs += gray[i];
        sink += cs;
    }
    const double scale = (double)NPIX * (double)STEPS;
    for (int t = 0; t < trials; t++) {
        QueryPerformanceCounter(&t0);
        for (int s = 0; s < STEPS; s++)
            luma(rgb, gray, NPIX);
        QueryPerformanceCounter(&t1);
        uint32_t cs = 0;
        for (int i = 0; i < NPIX; i++) cs += gray[i];
        sink += cs;
        printf("%.4f\n", (double)(t1.QuadPart - t0.QuadPart) * 1e9 / (double)f.QuadPart / scale);
    }
    fprintf(stderr, "sink=%u\n", (unsigned)sink);
    return 0;
}
