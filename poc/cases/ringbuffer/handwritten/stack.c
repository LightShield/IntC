/* Hand-written comparison program (not produced by the pipeline).
 * LIFO stack with the ring's enqueue/dequeue API. Capacity is a power of two
 * and indexing is a mask so CBMC can decide the query. The point is the
 * occupancy contract, not the index rewrite. */
#include <stdint.h>
#include <stdbool.h>

#define CAPACITY 1024

uint64_t ring[CAPACITY];
uint64_t head = 0;
uint64_t tail = 0;

bool enqueue(uint64_t pkt) {
    if (tail - head == CAPACITY) return false;
    ring[tail & (CAPACITY - 1)] = pkt;
    tail++;
    return true;
}

bool dequeue(uint64_t *out) {
    if (tail == head) return false;
    tail--;
    *out = ring[tail & (CAPACITY - 1)];
    return true;
}
