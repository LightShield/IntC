/* Pairwise in-range: length vs radius. Requirement: true iff dx^2+dy^2 < R^2
 * for nonnegative R. The sqrt in the comparison is not Post. */
#include <math.h>
#include <stdint.h>

#define RBOUND 80

int in_range(float d2, float R) {
    return sqrtf(d2) < R;
}
