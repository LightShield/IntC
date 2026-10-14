# Attribution — CMSIS-DSP FIR

- [ARM-software/CMSIS-DSP](https://github.com/ARM-software/CMSIS-DSP) `Source/FilteringFunctions/arm_fir_f32.c`
- Tag **v1.15.0**, peeled commit `8f8bb8d56b346274c9b2918928f2d5c3dae51758`

**What we kept.** A block FIR whose length is not a multiple of the unroll factor (upstream 441 = 4×110 + 1).

**What we changed.** Integer, 2 taps, BLOCK starts at 5. No `float`, no ARM intrinsics, no state delay line beyond `x[i+k]`. The rewrite only requires `BLOCK % 4 == 0`; CEGIS may pick 8. That is length slack, not a new convolution.
