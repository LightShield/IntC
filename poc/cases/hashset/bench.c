/* Benchmark driver: prints one ns/contains per trial.
 * Warmup inserts 4000 keys. The timed loop is contains() only, on an
 * xorshift stream. After the first hit, hits stays 1 on this stream, so
 * later keys are y+1 and do not serialize on the previous contains.
 * NBUCKETS is a hole with a load-factor floor; a larger table is fewer
 * probes as well as a mask. Ranking is this driver. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <windows.h>
#include "candidate.c"

int main(int argc, char **argv) {
    int trials = argc > 1 ? atoi(argv[1]) : 15;
    const uint64_t n = 20000000ull;
    LARGE_INTEGER f; QueryPerformanceFrequency(&f);
    uint64_t x = 88172645463325252ull, hits = 0;
    for (int i = 0; i < 4000; i++) { x ^= x << 13; x ^= x >> 7; x ^= x << 17; insert(x); }
    for (int t = 0; t < trials; t++) {
        LARGE_INTEGER a, b; QueryPerformanceCounter(&a);
        uint64_t y = 88172645463325252ull;
        for (uint64_t i = 0; i < n; i++) {
            y ^= y << 13; y ^= y >> 7; y ^= y << 17;
            bool r = contains(y + hits % 3);
            hits += r;
        }
        QueryPerformanceCounter(&b);
        printf("%.4f\n", (double)(b.QuadPart - a.QuadPart) * 1e9 / (double)f.QuadPart / (double)n);
    }
    fprintf(stderr, "hits=%llu\n", (unsigned long long)hits);
    return 0;
}
