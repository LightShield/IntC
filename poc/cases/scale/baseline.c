/* Integer gain. Requirement: GAIN in [8, 16]. A non-power-of-two baseline is
 * allowed; the contract is in terms of the candidate's GAIN, not the literal 10. */
#include <stdint.h>

#define GAIN 10

uint32_t apply_gain(uint32_t sample) {
    return sample * GAIN;
}
