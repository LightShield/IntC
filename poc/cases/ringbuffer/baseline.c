/* Baseline: bounded packet queue. Requirement: at least 1000 slots (25% headroom over 800-packet bursts). */
#include <stdint.h>
#include <stdbool.h>

#define CAPACITY 1000

uint64_t ring[CAPACITY];
uint64_t head = 0;  /* number of packets dequeued so far */
uint64_t tail = 0;  /* number of packets enqueued so far */

bool enqueue(uint64_t pkt) {
    if (tail - head == CAPACITY) return false;
    ring[tail % CAPACITY] = pkt;
    tail++;
    return true;
}

bool dequeue(uint64_t *out) {
    if (tail == head) return false;
    *out = ring[head % CAPACITY];
    head++;
    return true;
}
