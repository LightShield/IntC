# Attribution — Rec. 601 luma

- Float coefficients 0.299 / 0.587 / 0.114 and Q15 9798 / 19235 / 3735 as in
  OpenCV `modules/imgproc/src/color.simd_helpers.hpp`
  ([opencv/opencv](https://github.com/opencv/opencv)). Tag in
  `cases/real_world/CATALOG.md`.

**What we kept.** Packed 8-bit RGB to 8-bit gray with BT.601 weights.

**What we changed.** C, one loop, no SIMD dispatch. BMC NPX=4. Post allows
|Y − Q15| ≤ 1 so both the float MAC and the integerization can prove.
