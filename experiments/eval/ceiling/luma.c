/* Handwritten expert oracle: OpenCV-style RGB->gray.
 * P1  = float BT.601 MAC on uint8 (promote in the loop)
 * P*  = Q15 integer (RY15*r+GY15*g+BY15*b)>>15
 * Coefficients from OpenCV 4.10. Not IntentCompile. */
#include "common.h"

#define NPIX (1920 * 1080)
#define STEPS 8

/* OpenCV 4.10 modules/imgproc/src/color.simd_helpers.hpp */
#define RY15 9798
#define GY15 19235
#define BY15 3735
#define GRAY_SHIFT 15
#define R2YF 0.299f
#define G2YF 0.587f
#define B2YF 0.114f

static uint8_t *rgb;
static uint8_t *gray;
static volatile uint32_t sink;

static void init(void) {
    int i;
    rgb = (uint8_t *)malloc((size_t)NPIX * 3u);
    gray = (uint8_t *)malloc((size_t)NPIX);
    if (!rgb || !gray) {
        fprintf(stderr, "alloc failed\n");
        exit(1);
    }
    for (i = 0; i < NPIX; i++) {
        rgb[3 * i + 0] = (uint8_t)(i * 13u);
        rgb[3 * i + 1] = (uint8_t)(i * 29u);
        rgb[3 * i + 2] = (uint8_t)(i * 47u);
    }
}

static uint32_t luma_float(void) {
    int s, i;
    uint32_t acc = 0;
    for (s = 0; s < STEPS; s++) {
        for (i = 0; i < NPIX; i++) {
            float r = (float)rgb[3 * i + 0];
            float g = (float)rgb[3 * i + 1];
            float b = (float)rgb[3 * i + 2];
            uint8_t y = (uint8_t)(R2YF * r + G2YF * g + B2YF * b);
            gray[i] = y;
            acc += y;
        }
    }
    return acc;
}

static uint32_t luma_q15(void) {
    int s, i;
    uint32_t acc = 0;
    for (s = 0; s < STEPS; s++) {
        for (i = 0; i < NPIX; i++) {
            int r = rgb[3 * i + 0];
            int g = rgb[3 * i + 1];
            int b = rgb[3 * i + 2];
            uint8_t y = (uint8_t)((RY15 * r + GY15 * g + BY15 * b) >> GRAY_SHIFT);
            gray[i] = y;
            acc += y;
        }
    }
    return acc;
}

int main(void) {
    LARGE_INTEGER hz, t0, t1;
    double p1[CEILING_TRIALS], ps[CEILING_TRIALS];
    double scale = (double)NPIX * (double)STEPS;
    int t, i, maxabs;
    uint8_t *gfloat;

    QueryPerformanceFrequency(&hz);
    init();
    printf("kernel=luma  handwritten_oracle  NPIX=%d  STEPS=%d  sizeof_pixel_in=3\n", NPIX, STEPS);

    for (t = 0; t < CEILING_WARMUP; t++) {
        sink += luma_float();
        sink += luma_q15();
    }
    for (t = 0; t < CEILING_TRIALS; t++) {
        QueryPerformanceCounter(&t0);
        sink += luma_float();
        QueryPerformanceCounter(&t1);
        p1[t] = ceiling_nsec(t0, t1, hz) / scale;

        QueryPerformanceCounter(&t0);
        sink += luma_q15();
        QueryPerformanceCounter(&t1);
        ps[t] = ceiling_nsec(t0, t1, hz) / scale;
    }
    ceiling_print("luma_float_p1", NPIX, p1, CEILING_TRIALS);
    ceiling_print("luma_q15_pstar", NPIX, ps, CEILING_TRIALS);

    /* Cheap |Y_float - Y_q15| on one pass (not timed). */
    gfloat = (uint8_t *)malloc((size_t)NPIX);
    if (!gfloat) {
        fprintf(stderr, "alloc failed\n");
        return 1;
    }
    for (i = 0; i < NPIX; i++) {
        float r = (float)rgb[3 * i + 0];
        float g = (float)rgb[3 * i + 1];
        float b = (float)rgb[3 * i + 2];
        gfloat[i] = (uint8_t)(R2YF * r + G2YF * g + B2YF * b);
        gray[i] = (uint8_t)((RY15 * rgb[3 * i] + GY15 * rgb[3 * i + 1] + BY15 * rgb[3 * i + 2]) >> GRAY_SHIFT);
    }
    maxabs = 0;
    for (i = 0; i < NPIX; i++) {
        int d = (int)gfloat[i] - (int)gray[i];
        if (d < 0) {
            d = -d;
        }
        if (d > maxabs) {
            maxabs = d;
        }
    }
    printf("luma_max_abs_u8_diff=%d  (bits differ; as-if cannot retarget float to Q15)\n", maxabs);
    printf("sink=%u\n", (unsigned)sink);
    return 0;
}
