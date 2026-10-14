/* Array-of-structs kinematics. Requirement: after step(dt), each particle's
 * position is the previous position plus velocity times dt, with no wrap. */
#include <stdint.h>

#define N 4

typedef struct {
    int32_t x;
    int32_t y;
    int32_t vx;
    int32_t vy;
} Particle;

static Particle p[N];

void set_particle(int i, int32_t x, int32_t y, int32_t vx, int32_t vy) {
    p[i].x = x;
    p[i].y = y;
    p[i].vx = vx;
    p[i].vy = vy;
}

int32_t get_x(int i) { return p[i].x; }
int32_t get_y(int i) { return p[i].y; }

void step(int32_t dt) {
    for (int i = 0; i < N; i++) {
        p[i].x += p[i].vx * dt;
        p[i].y += p[i].vy * dt;
    }
}
