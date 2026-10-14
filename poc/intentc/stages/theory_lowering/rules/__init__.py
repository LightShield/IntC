"""Finite TheoryLower catalog: remainder, division, and multiply by a parameter."""

from intentc.stages.theory_lowering.rules.pow2_mask import Pow2Mask
from intentc.stages.theory_lowering.rules.pow2_mul import Pow2Mul
from intentc.stages.theory_lowering.rules.pow2_shift import Pow2Shift

CATALOG = [Pow2Mask(), Pow2Shift(), Pow2Mul()]

__all__ = ["CATALOG", "Pow2Mask", "Pow2Shift", "Pow2Mul"]
