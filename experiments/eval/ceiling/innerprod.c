/* Handwritten expert oracle: Opus SILK-style inner product.
 * P1 = double accum on float vectors (silk_inner_product_FLP shape, 4x unroll)
 * P* = float accum, same unroll
 * Lengths 256 (SILK-like) and 4096. Not IntentCompile. */
#include "common.h"
#include <math.h>

#define L256 256
#define L4096 4096
#define REPS256 200000
#define REPS4096 20000
#define PAD 32

static float *a256, *b256, *a4096, *b4096;
static volatile double sink_d;
static volatile float sink_f;

static float *alloc_vec(int n, int seed) {
    int i;
    float *p = (float *)malloc(sizeof(float) * (size_t)n);
    if (!p) {
        fprintf(stderr, "alloc failed\n");
        exit(1);
    }
    for (i = 0; i < n; i++) {
        p[i] = (float)((i * 17 + seed) % 101) * 0.015625f - 0.5f;
    }
    return p;
}

/* Tagged xiph/opus v1.4 silk/float/inner_product_FLP.c shape. */
static double inner_double(const float *data1, const float *data2, int n) {
    int i;
    int n4 = n & ~3;
    double result = 0.0;
    for (i = 0; i < n4; i += 4) {
        result += data1[i + 0] * (double)data2[i + 0] +
                  data1[i + 1] * (double)data2[i + 1] +
                  data1[i + 2] * (double)data2[i + 2] +
                  data1[i + 3] * (double)data2[i + 3];
    }
    for (; i < n; i++) {
        result += data1[i] * (double)data2[i];
    }
    return result;
}

static float inner_float(const float *data1, const float *data2, int n) {
    int i;
    int n4 = n & ~3;
    float result = 0.0f;
    for (i = 0; i < n4; i += 4) {
        result += data1[i + 0] * data2[i + 0] +
                  data1[i + 1] * data2[i + 1] +
                  data1[i + 2] * data2[i + 2] +
                  data1[i + 3] * data2[i + 3];
    }
    for (; i < n; i++) {
        result += data1[i] * data2[i];
    }
    return result;
}

static double run_double(const float *a, const float *b, int n, int reps) {
    int r;
    double acc = 0.0;
    /* Sliding start kills LICM of a single invariant dot; PAD keeps it cache-hot. */
    for (r = 0; r < reps; r++) {
        acc += inner_double(a + (r % PAD), b, n);
    }
    return acc;
}

static float run_float(const float *a, const float *b, int n, int reps) {
    int r;
    float acc = 0.0f;
    for (r = 0; r < reps; r++) {
        acc += inner_float(a + (r % PAD), b, n);
    }
    return acc;
}

static void time_len(const char *tag, const float *a, const float *b, int n, int reps, LARGE_INTEGER hz) {
    LARGE_INTEGER t0, t1;
    double p1[CEILING_TRIALS], ps[CEILING_TRIALS];
    double scale = (double)n * (double)reps;
    int t;
    double dref, fref, rel;

    for (t = 0; t < CEILING_WARMUP; t++) {
        sink_d += run_double(a, b, n, reps / 8 > 0 ? reps / 8 : 1);
        sink_f += run_float(a, b, n, reps / 8 > 0 ? reps / 8 : 1);
    }
    for (t = 0; t < CEILING_TRIALS; t++) {
        QueryPerformanceCounter(&t0);
        sink_d += run_double(a, b, n, reps);
        QueryPerformanceCounter(&t1);
        p1[t] = ceiling_nsec(t0, t1, hz) / scale;

        QueryPerformanceCounter(&t0);
        sink_f += run_float(a, b, n, reps);
        QueryPerformanceCounter(&t1);
        ps[t] = ceiling_nsec(t0, t1, hz) / scale;
    }
    ceiling_print(tag[0] == '2' ? "inner_double_p1_L256" : "inner_double_p1_L4096", n, p1, CEILING_TRIALS);
    ceiling_print(tag[0] == '2' ? "inner_float_pstar_L256" : "inner_float_pstar_L4096", n, ps, CEILING_TRIALS);

    dref = inner_double(a, b, n);
    fref = inner_float(a, b, n);
    rel = dref != 0.0 ? fabs((double)fref - dref) / fabs(dref) : 0.0;
    printf("inner_rel_|float-double|  L=%d  rel=%.6e  (bits differ)\n", n, rel);
}

int main(void) {
    LARGE_INTEGER hz;
    QueryPerformanceFrequency(&hz);
    a256 = alloc_vec(L256 + PAD, 1);
    b256 = alloc_vec(L256, 2);
    a4096 = alloc_vec(L4096 + PAD, 3);
    b4096 = alloc_vec(L4096, 4);
    printf("kernel=innerprod  handwritten_oracle  L256=%d reps=%d  L4096=%d reps=%d\n",
           L256, REPS256, L4096, REPS4096);
    time_len("256", a256, b256, L256, REPS256, hz);
    time_len("4096", a4096, b4096, L4096, REPS4096, hz);
    printf("sink_d=%g  sink_f=%g\n", sink_d, (double)sink_f);
    return 0;
}
