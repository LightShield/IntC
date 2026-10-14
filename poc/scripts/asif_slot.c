/* Isolated slot map: what MSVC /O2 does with remainder vs a mask.
   Not a queue. Used only to dump assembly for the as-if column. */
#include <stdint.h>

#if !defined(__clang__)
#pragma optimize("gt", on)
#endif

#if defined(_MSC_VER)
__declspec(noinline)
#endif
uint64_t slot_1000(uint64_t i) {
    return i % 1000;
}

#if defined(_MSC_VER)
__declspec(noinline)
#endif
uint64_t slot_1024(uint64_t i) {
    return i % 1024;
}

#if defined(_MSC_VER)
__declspec(noinline)
#endif
uint64_t slot_mask(uint64_t i) {
    return i & 1023;
}
