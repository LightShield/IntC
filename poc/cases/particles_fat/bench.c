/* N=1e5, 200 noinline steps. Prints ns per particle-step. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <windows.h>
#define N 100000
#define STEPS 200
#include "candidate.c"

static volatile int32_t sink;

int main(int argc, char **argv) {
    int trials = argc > 1 ? atoi(argv[1]) : 15;
    LARGE_INTEGER f, t0, t1;
    QueryPerformanceFrequency(&f);
    for (int i = 0; i < N; i++)
        set_particle(i, i, 1, 3, 4);
    for (int w = 0; w < 3; w++) {
        for (int s = 0; s < 4; s++)
            step(N, 1);
        sink += get_x(0) + get_x(N / 2) + get_x(N - 1);
    }
    void (*volatile fp)(int, int32_t) = step;
    const double scale = (double)N * (double)STEPS;
    for (int t = 0; t < trials; t++) {
        QueryPerformanceCounter(&t0);
        for (int s = 0; s < STEPS; s++)
            fp(N, 1);
        QueryPerformanceCounter(&t1);
        sink += get_x(0) + get_x(N / 2) + get_x(N - 1);
        printf("%.4f\n", (double)(t1.QuadPart - t0.QuadPart) * 1e9 / (double)f.QuadPart / scale);
    }
    fprintf(stderr, "sink=%d\n", (int)sink);
    return 0;
}
