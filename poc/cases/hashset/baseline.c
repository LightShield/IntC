/* Baseline: open-addressing hash set with linear probing. Requirement: at least
 * 10007 buckets (load-factor headroom). A prime bucket count was chosen to spread
 * keys; any count >= 10007 meets the requirement. */
#include <stdint.h>
#include <stdbool.h>

#define NBUCKETS 10007
#define MAXPROBE 4

uint64_t keys[NBUCKETS];
bool used[NBUCKETS];

static uint64_t mix(uint64_t k) { return k ^ (k >> 29); }

bool insert(uint64_t k) {
    uint64_t start = mix(k) % NBUCKETS;
    for (uint64_t p = 0; p < MAXPROBE; p++) {
        uint64_t s = (start + p) % NBUCKETS;
        if (!used[s]) { used[s] = true; keys[s] = k; return true; }
        if (keys[s] == k) return true;
    }
    return false;  /* probe limit reached: insertion may fail */
}

bool contains(uint64_t k) {
    uint64_t start = mix(k) % NBUCKETS;
    for (uint64_t p = 0; p < MAXPROBE; p++) {
        uint64_t s = (start + p) % NBUCKETS;
        if (!used[s]) return false;
        if (keys[s] == k) return true;
    }
    return false;
}
