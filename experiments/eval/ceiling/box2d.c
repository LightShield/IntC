/* Handwritten expert oracle: Box2D/Chipmunk-style length uses.
 * (a) sqrt(dx*dx+dy*dy) < R  vs  dx*dx+dy*dy < R*R   (boolean in-range)
 * (b) always-normalize vs skip-normalize on already-unit vectors
 * Not IntentCompile. (a) may be as-if-legal if the compiler folds. */
#include "common.h"
#include <math.h>

#define NPAIRS 1000000
#define NVEC 1000000
#define STEPS_A 8
#define STEPS_B 4
#define RADIUS 50.0f

static float *dx, *dy;
static float *vx, *vy, *ox, *oy;
static volatile uint32_t sink;

static void init(void) {
    int i;
    dx = (float *)malloc(sizeof(float) * (size_t)NPAIRS);
    dy = (float *)malloc(sizeof(float) * (size_t)NPAIRS);
    vx = (float *)malloc(sizeof(float) * (size_t)NVEC);
    vy = (float *)malloc(sizeof(float) * (size_t)NVEC);
    ox = (float *)malloc(sizeof(float) * (size_t)NVEC);
    oy = (float *)malloc(sizeof(float) * (size_t)NVEC);
    if (!dx || !dy || !vx || !vy || !ox || !oy) {
        fprintf(stderr, "alloc failed\n");
        exit(1);
    }
    for (i = 0; i < NPAIRS; i++) {
        dx[i] = (float)((i * 17) % 200) - 100.0f;
        dy[i] = (float)((i * 31) % 200) - 100.0f;
    }
    /* Already-unit vectors from a rational parametrization (no libm in init). */
    for (i = 0; i < NVEC; i++) {
        float t = (float)(i % 360) / 180.0f - 1.0f; /* [-1,1) */
        float n2 = 1.0f + t * t;
        vx[i] = (1.0f - t * t) / n2;
        vy[i] = (2.0f * t) / n2;
    }
}

static uint32_t inrange_sqrt(void) {
    int s, i;
    uint32_t acc = 0;
    float R = RADIUS;
    for (s = 0; s < STEPS_A; s++) {
        for (i = 0; i < NPAIRS; i++) {
            float d2 = dx[i] * dx[i] + dy[i] * dy[i];
            acc += (sqrtf(d2) < R);
        }
    }
    return acc;
}

static uint32_t inrange_sq(void) {
    int s, i;
    uint32_t acc = 0;
    float R2 = RADIUS * RADIUS;
    for (s = 0; s < STEPS_A; s++) {
        for (i = 0; i < NPAIRS; i++) {
            float d2 = dx[i] * dx[i] + dy[i] * dy[i];
            acc += (d2 < R2);
        }
    }
    return acc;
}

static uint32_t always_normalize(void) {
    int s, i;
    uint32_t acc = 0;
    for (s = 0; s < STEPS_B; s++) {
        for (i = 0; i < NVEC; i++) {
            float x = vx[i], y = vy[i];
            float len = sqrtf(x * x + y * y);
            float inv = 1.0f / len;
            float nx = x * inv, ny = y * inv;
            ox[i] = nx;
            oy[i] = ny;
            acc += (uint32_t)((nx + ny) * 256.0f);
        }
    }
    return acc;
}

static uint32_t skip_normalize(void) {
    int s, i;
    uint32_t acc = 0;
    for (s = 0; s < STEPS_B; s++) {
        for (i = 0; i < NVEC; i++) {
            float nx = vx[i], ny = vy[i];
            ox[i] = nx;
            oy[i] = ny;
            acc += (uint32_t)((nx + ny) * 256.0f);
        }
    }
    return acc;
}

int main(void) {
    LARGE_INTEGER hz, t0, t1;
    double p1a[CEILING_TRIALS], psa[CEILING_TRIALS];
    double p1b[CEILING_TRIALS], psb[CEILING_TRIALS];
    double scale_a = (double)NPAIRS * (double)STEPS_A;
    double scale_b = (double)NVEC * (double)STEPS_B;
    int t;
    uint32_t c_sqrt, c_sq;

    QueryPerformanceFrequency(&hz);
    init();
    printf("kernel=box2d  handwritten_oracle  NPAIRS=%d  NVEC=%d  R=%.1f\n",
           NPAIRS, NVEC, (double)RADIUS);

    for (t = 0; t < CEILING_WARMUP; t++) {
        sink += inrange_sqrt();
        sink += inrange_sq();
        sink += always_normalize();
        sink += skip_normalize();
    }
    for (t = 0; t < CEILING_TRIALS; t++) {
        QueryPerformanceCounter(&t0);
        sink += inrange_sqrt();
        QueryPerformanceCounter(&t1);
        p1a[t] = ceiling_nsec(t0, t1, hz) / scale_a;

        QueryPerformanceCounter(&t0);
        sink += inrange_sq();
        QueryPerformanceCounter(&t1);
        psa[t] = ceiling_nsec(t0, t1, hz) / scale_a;
    }
    ceiling_print("inrange_sqrt_p1", NPAIRS, p1a, CEILING_TRIALS);
    ceiling_print("inrange_sq_pstar", NPAIRS, psa, CEILING_TRIALS);

    c_sqrt = inrange_sqrt();
    c_sq = inrange_sq();
    printf("inrange_count  sqrt=%u  sq=%u  match=%s\n",
           (unsigned)c_sqrt, (unsigned)c_sq,
           c_sqrt == c_sq ? "yes" : "NO");

    for (t = 0; t < CEILING_TRIALS; t++) {
        QueryPerformanceCounter(&t0);
        sink += always_normalize();
        QueryPerformanceCounter(&t1);
        p1b[t] = ceiling_nsec(t0, t1, hz) / scale_b;

        QueryPerformanceCounter(&t0);
        sink += skip_normalize();
        QueryPerformanceCounter(&t1);
        psb[t] = ceiling_nsec(t0, t1, hz) / scale_b;
    }
    ceiling_print("normalize_always_p1", NVEC, p1b, CEILING_TRIALS);
    ceiling_print("normalize_skip_pstar", NVEC, psb, CEILING_TRIALS);
    printf("sink=%u  (5a: compiler may fold sqrt(d2)<R; inspect /FAs)\n", (unsigned)sink);
    return 0;
}
