/* Baseline: bounded packet queue with a separate backing store.
 * Logical fullness is CAPACITY. Indexing uses STORAGE. They start equal. */
#include <stdint.h>
#include <stdbool.h>

#define CAPACITY 1000
#define STORAGE 1000

uint64_t ring[STORAGE];
uint64_t head = 0;
uint64_t tail = 0;

bool enqueue(uint64_t pkt) {
    if (tail - head == CAPACITY) return false;
    ring[tail % STORAGE] = pkt;
    tail++;
    return true;
}

bool dequeue(uint64_t *out) {
    if (tail == head) return false;
    *out = ring[head % STORAGE];
    head++;
    return true;
}
