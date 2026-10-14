/* L=256, 200000 dots, sliding start. Prints ns/MAC. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <windows.h>
#define L 256
#define REPS 200000
#define PAD 32
#include "candidate.c"

static float a[L + PAD], b[L];
static volatile double sink;

int main(int argc, char **argv) {
    int trials = argc > 1 ? atoi(argv[1]) : 15;
    LARGE_INTEGER f, t0, t1;
    QueryPerformanceFrequency(&f);
    for (int i = 0; i < L + PAD; i++)
        a[i] = (float)((i * 17 + 1) % 101) * 0.015625f - 0.5f;
    for (int i = 0; i < L; i++)
        b[i] = (float)((i * 17 + 2) % 101) * 0.015625f - 0.5f;
    for (int w = 0; w < 3; w++) {
        double acc = 0.0;
        for (int r = 0; r < REPS / 8; r++)
            acc += inner(a + (r % PAD), b, L);
        sink += acc;
    }
    const double scale = (double)L * (double)REPS;
    for (int t = 0; t < trials; t++) {
        double acc = 0.0;
        QueryPerformanceCounter(&t0);
        for (int r = 0; r < REPS; r++)
            acc += inner(a + (r % PAD), b, L);
        QueryPerformanceCounter(&t1);
        sink += acc;
        printf("%.4f\n", (double)(t1.QuadPart - t0.QuadPart) * 1e9 / (double)f.QuadPart / scale);
    }
    fprintf(stderr, "sink=%g\n", sink);
    return 0;
}
