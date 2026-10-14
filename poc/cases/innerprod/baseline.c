/* Inner product with a double accumulator on float vectors.
 * Requirement: result agrees with a float MAC on small integer-valued
 * operands (harness). The double accum is not Post. */
#include <stdint.h>

#define LEN 4

double inner(const float *data1, const float *data2, int n) {
    double result = 0.0;
    for (int i = 0; i < n; i++)
        result += data1[i] * (double)data2[i];
    return result;
}
