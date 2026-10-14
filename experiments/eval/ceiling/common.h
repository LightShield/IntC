/* Shared timing for handwritten expert-oracle kernels. Not IntentCompile. */
#ifndef CEILING_COMMON_H
#define CEILING_COMMON_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <windows.h>

#define CEILING_TRIALS 15
#define CEILING_WARMUP 3

static double ceiling_nsec(LARGE_INTEGER a, LARGE_INTEGER b, LARGE_INTEGER hz) {
    return 1e9 * (double)(b.QuadPart - a.QuadPart) / (double)hz.QuadPart;
}

static int ceiling_cmp_d(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

static double ceiling_median(double *v, int n) {
    qsort(v, (size_t)n, sizeof(double), ceiling_cmp_d);
    return v[n / 2];
}

static void ceiling_print(const char *name, int n, const double *trials, int nt) {
    double tmp[64];
    int i;
    double med, mn, mx;
    if (nt > 64) {
        nt = 64;
    }
    for (i = 0; i < nt; i++) {
        tmp[i] = trials[i];
    }
    mn = mx = tmp[0];
    for (i = 1; i < nt; i++) {
        if (tmp[i] < mn) {
            mn = tmp[i];
        }
        if (tmp[i] > mx) {
            mx = tmp[i];
        }
    }
    med = ceiling_median(tmp, nt);
    printf("%s  N=%d  trials=%d  median_ns_elem=%.4f  min=%.4f  max=%.4f  trials_ns=",
           name, n, nt, med, mn, mx);
    for (i = 0; i < nt; i++) {
        printf("%s%.4f", i ? "," : "", trials[i]);
    }
    printf("\n");
}

#endif
