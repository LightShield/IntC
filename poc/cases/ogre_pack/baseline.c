/* OGRE-style transform-space tag on a command. space is 0 local, 1 parent, 2 world. */
#include <stdint.h>

#define N 4

typedef struct {
    int space;
    int32_t x;
    int32_t y;
} Cmd;

static Cmd cmds[N];

void set_cmd(int i, int space, int32_t x, int32_t y) {
    cmds[i].space = space;
    cmds[i].x = x;
    cmds[i].y = y;
}

int32_t eval_x(int i) {
    int32_t f = (cmds[i].space == 2) ? 2 : 1;
    return cmds[i].x * f;
}
