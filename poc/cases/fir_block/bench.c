/* Prints ns per filter() call. BLOCK is the candidate's trip count. Extra
 * outputs from rounding 5 up to 8 are extra work on this driver. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <windows.h>
#define REPS 4000000
#include "candidate.c"

static volatile int32_t sink;

int main(int argc, char **argv) {
    int trials = argc > 1 ? atoi(argv[1]) : 15;
    LARGE_INTEGER f, t0, t1;
    QueryPerformanceFrequency(&f);
    for (int i = 0; i < 32; i++)
        set_x(i, (int32_t)((i * 17) % 13) - 6);
    for (int k = 0; k < TAPS; k++)
        set_h(k, 1 + k);
    for (int w = 0; w < 3; w++) {
        for (int r = 0; r < REPS / 8; r++)
            filter();
        sink += get_y(0);
    }
    for (int t = 0; t < trials; t++) {
        QueryPerformanceCounter(&t0);
        for (int r = 0; r < REPS; r++)
            filter();
        QueryPerformanceCounter(&t1);
        sink += get_y(0);
        printf("%.4f\n", (double)(t1.QuadPart - t0.QuadPart) * 1e9
            / (double)f.QuadPart / (double)REPS);
    }
    fprintf(stderr, "sink=%d\n", (int)sink);
    return 0;
}
