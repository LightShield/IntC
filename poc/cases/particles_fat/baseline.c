/* Fat array-of-structs Euler step. Requirement: after step(n, dt), each
 * particle's position is previous plus velocity times dt. Layout of the
 * record is not in the index API. N defaults to the BMC size; a benchmark
 * may define N larger before including this file. */
#include <stdint.h>

#ifndef N
#define N 4
#endif

typedef struct {
    int32_t x;
    int32_t y;
    int32_t z;
    int32_t vx;
    int32_t vy;
    int32_t vz;
    int32_t mass;
    int32_t ax;
    int32_t ay;
    int32_t az;
    int32_t density;
    int32_t pressure;
    int32_t pad0;
    int32_t pad1;
    int32_t pad2;
    int32_t pad3;
} Particle;

static Particle p[N];

void set_particle(int i, int32_t x, int32_t y, int32_t vx, int32_t vy) {
    p[i].x = x;
    p[i].y = y;
    p[i].z = 0;
    p[i].vx = vx;
    p[i].vy = vy;
    p[i].vz = 0;
    p[i].mass = 1;
    p[i].ax = 0;
    p[i].ay = 0;
    p[i].az = 0;
    p[i].density = 0;
    p[i].pressure = 0;
    p[i].pad0 = 0;
    p[i].pad1 = 0;
    p[i].pad2 = 0;
    p[i].pad3 = 0;
}

int32_t get_x(int i) { return p[i].x; }
int32_t get_y(int i) { return p[i].y; }

void step(int n, int32_t dt) {
    for (int i = 0; i < n; i++) {
        p[i].x += p[i].vx * dt;
        p[i].y += p[i].vy * dt;
        p[i].z += p[i].vz * dt;
    }
}
