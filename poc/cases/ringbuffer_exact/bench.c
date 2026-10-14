/* Same dependent enqueue/dequeue driver as the logical-capacity ring. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <windows.h>
#include "candidate.c"

int main(int argc, char **argv) {
    int trials = argc > 1 ? atoi(argv[1]) : 15;
    const uint64_t n = 50000000ull;
    LARGE_INTEGER f; QueryPerformanceFrequency(&f);
    uint64_t x = (uint64_t)argc, sink = 0;
    for (int w = 0; w < 500; w++) enqueue(w);
    for (int t = 0; t < trials; t++) {
        LARGE_INTEGER a, b; QueryPerformanceCounter(&a);
        for (uint64_t i = 0; i < n; i++) {
            enqueue(x);
            dequeue(&x);
            x = x * 6364136223846793005ull + 1;
        }
        QueryPerformanceCounter(&b);
        sink += x;
        printf("%.4f\n", (double)(b.QuadPart - a.QuadPart) * 1e9 / (double)f.QuadPart / (double)n);
    }
    fprintf(stderr, "sink=%llu\n", (unsigned long long)sink);
    return 0;
}
