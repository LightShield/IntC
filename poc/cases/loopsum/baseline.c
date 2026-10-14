/* Sum of a small array. N is a parameter but not a remainder or divisor, so
 * TheoryLower has no applicable rewrite and should fail the stage. */
#define N 8

int a[N];

int sum(void) {
    int s = 0;
    for (int i = 0; i < N; i++) s += a[i];
    return s;
}
