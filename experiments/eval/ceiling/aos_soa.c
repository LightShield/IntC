/* Handwritten expert oracle: fat AoS vs SoA particle Euler.
 * Godot/PARSEC-scale layout ceiling at N=1e5, 64-byte record.
 * Hot: pos/vel. Cold: mass/acc/density/pressure (+pad).
 * Not IntentCompile. */
#include "common.h"

#define N 100000
#define STEPS 200

typedef struct {
    int32_t x, y, z, vx, vy, vz;
    int32_t mass, ax, ay, az, density, pressure;
    int32_t pad[4];
} Fat;

static Fat *aos;
static int32_t *sx, *sy, *sz, *svx, *svy, *svz;
static int32_t *smass, *sax, *say, *saz, *sden, *spre;
static volatile int32_t sink;

static void init(void) {
    int i;
    aos = (Fat *)malloc(sizeof(Fat) * (size_t)N);
    sx = (int32_t *)malloc(4u * (size_t)N);
    sy = (int32_t *)malloc(4u * (size_t)N);
    sz = (int32_t *)malloc(4u * (size_t)N);
    svx = (int32_t *)malloc(4u * (size_t)N);
    svy = (int32_t *)malloc(4u * (size_t)N);
    svz = (int32_t *)malloc(4u * (size_t)N);
    smass = (int32_t *)malloc(4u * (size_t)N);
    sax = (int32_t *)malloc(4u * (size_t)N);
    say = (int32_t *)malloc(4u * (size_t)N);
    saz = (int32_t *)malloc(4u * (size_t)N);
    sden = (int32_t *)malloc(4u * (size_t)N);
    spre = (int32_t *)malloc(4u * (size_t)N);
    if (!aos || !sx || !sy || !sz || !svx || !svy || !svz ||
        !smass || !sax || !say || !saz || !sden || !spre) {
        fprintf(stderr, "alloc failed\n");
        exit(1);
    }
    for (i = 0; i < N; i++) {
        aos[i].x = sx[i] = i;
        aos[i].y = sy[i] = 1;
        aos[i].z = sz[i] = 2;
        aos[i].vx = svx[i] = 3;
        aos[i].vy = svy[i] = 4;
        aos[i].vz = svz[i] = 5;
        aos[i].mass = smass[i] = 1;
        aos[i].ax = sax[i] = 0;
        aos[i].ay = say[i] = 0;
        aos[i].az = saz[i] = 0;
        aos[i].density = sden[i] = 0;
        aos[i].pressure = spre[i] = 0;
        aos[i].pad[0] = aos[i].pad[1] = aos[i].pad[2] = aos[i].pad[3] = 0;
    }
}

/* noinline: MSVC /O2 interchanges fused for-s-for-i into a per-particle
 * register loop of STEPS adds for AoS, while SoA still RMW memory 200 times.
 * That is not the layout ceiling. One pass per call keeps Euler-step traffic. */
__declspec(noinline) static int32_t step_aos_once(int32_t dt) {
    int i;
    for (i = 0; i < N; i++) {
        aos[i].x += aos[i].vx * dt;
        aos[i].y += aos[i].vy * dt;
        aos[i].z += aos[i].vz * dt;
    }
    return aos[0].x;
}

__declspec(noinline) static int32_t step_soa_once(int32_t dt) {
    int i;
    int32_t * __restrict x = sx;
    int32_t * __restrict y = sy;
    int32_t * __restrict z = sz;
    int32_t * __restrict vx = svx;
    int32_t * __restrict vy = svy;
    int32_t * __restrict vz = svz;
    for (i = 0; i < N; i++) {
        x[i] += vx[i] * dt;
        y[i] += vy[i] * dt;
        z[i] += vz[i] * dt;
    }
    return x[0];
}

static int32_t step_aos(int32_t dt) {
    int s, i;
    int32_t a = 0;
    for (s = 0; s < STEPS; s++) {
        a += step_aos_once(dt);
    }
    for (i = 0; i < N; i++) {
        a += aos[i].x;
    }
    return a;
}

static int32_t step_soa(int32_t dt) {
    int s, i;
    int32_t a = 0;
    for (s = 0; s < STEPS; s++) {
        a += step_soa_once(dt);
    }
    for (i = 0; i < N; i++) {
        a += sx[i];
    }
    return a;
}

int main(void) {
    LARGE_INTEGER hz, t0, t1;
    double p1[CEILING_TRIALS], ps[CEILING_TRIALS];
    double scale = (double)N * (double)STEPS;
    int t;

    QueryPerformanceFrequency(&hz);
    init();
    printf("kernel=aos_soa  handwritten_oracle  N=%d  STEPS=%d  sizeof_Fat=%zu\n",
           N, STEPS, sizeof(Fat));

    for (t = 0; t < CEILING_WARMUP; t++) {
        sink += step_aos(1);
        sink += step_soa(1);
    }
    for (t = 0; t < CEILING_TRIALS; t++) {
        QueryPerformanceCounter(&t0);
        sink += step_aos(1);
        QueryPerformanceCounter(&t1);
        p1[t] = ceiling_nsec(t0, t1, hz) / scale;

        QueryPerformanceCounter(&t0);
        sink += step_soa(1);
        QueryPerformanceCounter(&t1);
        ps[t] = ceiling_nsec(t0, t1, hz) / scale;
    }
    ceiling_print("fat_aos_p1", N, p1, CEILING_TRIALS);
    ceiling_print("soa_pstar", N, ps, CEILING_TRIALS);
    printf("sink=%d  (layout only; observational index API)\n", (int)sink);
    return 0;
}
