/* Handwritten expert oracle: CMSIS-style complex magnitude.
 * P1 = libm sqrtf(re*re+im*im) on interleaved bins
 * P* = 1/2/3-iter Quake rsqrt Newton, then mag = x * y
 * optional α-max+β-min (α=1, β=3/8)
 * Not IntentCompile. */
#include "common.h"
#include <math.h>

#define NBINS 1048576
#define STEPS 4

static float *src; /* interleaved re,im */
static float *dst;
static volatile float sink_f;
static volatile uint32_t sink;

static float rsqrt_seed(float x) {
    uint32_t i;
    memcpy(&i, &x, sizeof(i));
    i = 0x5f3759dfu - (i >> 1);
    memcpy(&x, &i, sizeof(x));
    return x;
}

static void init(void) {
    int i;
    src = (float *)malloc(sizeof(float) * 2u * (size_t)NBINS);
    dst = (float *)malloc(sizeof(float) * (size_t)NBINS);
    if (!src || !dst) {
        fprintf(stderr, "alloc failed\n");
        exit(1);
    }
    for (i = 0; i < NBINS; i++) {
        src[2 * i + 0] = 0.5f + (float)(i % 97) * 0.01f;
        src[2 * i + 1] = -0.3f + (float)(i % 53) * 0.02f;
    }
}

static uint32_t mag_sqrtf(void) {
    int s, i;
    uint32_t acc = 0;
    for (s = 0; s < STEPS; s++) {
        for (i = 0; i < NBINS; i++) {
            float re = src[2 * i], im = src[2 * i + 1];
            float m = sqrtf(re * re + im * im);
            dst[i] = m;
            acc += (uint32_t)(m * 256.0f);
        }
    }
    return acc;
}

static uint32_t mag_newton(int iters) {
    int s, i, k;
    uint32_t acc = 0;
    for (s = 0; s < STEPS; s++) {
        for (i = 0; i < NBINS; i++) {
            float re = src[2 * i], im = src[2 * i + 1];
            float x = re * re + im * im;
            float y = rsqrt_seed(x);
            for (k = 0; k < iters; k++) {
                y = y * (1.5f - 0.5f * x * y * y);
            }
            {
                float m = x * y;
                dst[i] = m;
                acc += (uint32_t)(m * 256.0f);
            }
        }
    }
    return acc;
}

static uint32_t mag_newton1(void) { return mag_newton(1); }
static uint32_t mag_newton2(void) { return mag_newton(2); }
static uint32_t mag_newton3(void) { return mag_newton(3); }

/* α-max + β-min, α=1, β=3/8. */
static uint32_t mag_alphamax(void) {
    int s, i;
    uint32_t acc = 0;
    for (s = 0; s < STEPS; s++) {
        for (i = 0; i < NBINS; i++) {
            float re = src[2 * i], im = src[2 * i + 1];
            float a = fabsf(re), b = fabsf(im);
            float mx = a > b ? a : b;
            float mn = a > b ? b : a;
            float m = mx + 0.375f * mn;
            dst[i] = m;
            acc += (uint32_t)(m * 256.0f);
        }
    }
    return acc;
}

static void time_fn(const char *name, uint32_t (*fn)(void), double *out, LARGE_INTEGER hz) {
    LARGE_INTEGER t0, t1;
    int t;
    double scale = (double)NBINS * (double)STEPS;
    for (t = 0; t < CEILING_WARMUP; t++) {
        sink += fn();
    }
    for (t = 0; t < CEILING_TRIALS; t++) {
        QueryPerformanceCounter(&t0);
        sink += fn();
        QueryPerformanceCounter(&t1);
        out[t] = ceiling_nsec(t0, t1, hz) / scale;
    }
    ceiling_print(name, NBINS, out, CEILING_TRIALS);
}

int main(void) {
    LARGE_INTEGER hz;
    double t_sqrt[CEILING_TRIALS], t1[CEILING_TRIALS], t2[CEILING_TRIALS], t3[CEILING_TRIALS], ta[CEILING_TRIALS];
    int i;
    double max_rel1 = 0, max_rel2 = 0, max_rel3 = 0, max_rela = 0;

    QueryPerformanceFrequency(&hz);
    init();
    printf("kernel=mag  handwritten_oracle  NBINS=%d  STEPS=%d  interleaved\n", NBINS, STEPS);

    time_fn("mag_sqrtf_p1", mag_sqrtf, t_sqrt, hz);
    time_fn("mag_newton1_pstar", mag_newton1, t1, hz);
    time_fn("mag_newton2_pstar", mag_newton2, t2, hz);
    time_fn("mag_newton3_pstar", mag_newton3, t3, hz);
    time_fn("mag_alphamax_pstar", mag_alphamax, ta, hz);

    /* One-pass max relative |P*-sqrtf| (not timed). */
    for (i = 0; i < NBINS; i++) {
        float re = src[2 * i], im = src[2 * i + 1];
        float x = re * re + im * im;
        float ref = sqrtf(x);
        float y, m, rel;
        if (ref <= 0.0f) {
            continue;
        }
        y = rsqrt_seed(x);
        y = y * (1.5f - 0.5f * x * y * y);
        m = x * y;
        rel = fabsf(m - ref) / ref;
        if (rel > max_rel1) {
            max_rel1 = rel;
        }
        y = y * (1.5f - 0.5f * x * y * y);
        m = x * y;
        rel = fabsf(m - ref) / ref;
        if (rel > max_rel2) {
            max_rel2 = rel;
        }
        y = y * (1.5f - 0.5f * x * y * y);
        m = x * y;
        rel = fabsf(m - ref) / ref;
        if (rel > max_rel3) {
            max_rel3 = rel;
        }
        {
            float a = fabsf(re), b = fabsf(im);
            float mx = a > b ? a : b;
            float mn = a > b ? b : a;
            m = mx + 0.375f * mn;
            rel = fabsf(m - ref) / ref;
            if (rel > max_rela) {
                max_rela = rel;
            }
        }
    }
    printf("mag_max_rel_err  n1=%.6f  n2=%.6f  n3=%.6f  alphamax=%.6f  (bits differ)\n",
           max_rel1, max_rel2, max_rel3, max_rela);
    printf("sink=%u  sink_f=%g\n", (unsigned)sink, (double)sink_f);
    return 0;
}
