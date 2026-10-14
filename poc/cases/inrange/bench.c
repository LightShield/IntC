/* 1e6 pairs, 8 passes. Prints ns/pair. Candidate supplies in_range.
 * acc sums every in_range result so the timed calls are not dead. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <windows.h>
#define NPAIRS 1000000
#define STEPS 8
#include "candidate.c"

static float dx[NPAIRS], dy[NPAIRS];
static volatile uint32_t sink;

int main(int argc, char **argv) {
    int trials = argc > 1 ? atoi(argv[1]) : 15;
    const float R = 50.0f;
    LARGE_INTEGER f, a, b;
    QueryPerformanceFrequency(&f);
    for (int i = 0; i < NPAIRS; i++) {
        dx[i] = (float)((i * 17) % 200) - 100.0f;
        dy[i] = (float)((i * 31) % 200) - 100.0f;
    }
    for (int w = 0; w < 3; w++) {
        uint32_t acc = 0;
        for (int s = 0; s < STEPS; s++)
            for (int i = 0; i < NPAIRS; i++)
                acc += (uint32_t)in_range(dx[i] * dx[i] + dy[i] * dy[i], R);
        sink += acc;
    }
    const double scale = (double)NPAIRS * (double)STEPS;
    for (int t = 0; t < trials; t++) {
        uint32_t acc = 0;
        QueryPerformanceCounter(&a);
        for (int s = 0; s < STEPS; s++)
            for (int i = 0; i < NPAIRS; i++)
                acc += (uint32_t)in_range(dx[i] * dx[i] + dy[i] * dy[i], R);
        QueryPerformanceCounter(&b);
        sink += acc;
        printf("%.4f\n", (double)(b.QuadPart - a.QuadPart) * 1e9 / (double)f.QuadPart / scale);
    }
    fprintf(stderr, "sink=%u\n", (unsigned)sink);
    return 0;
}
