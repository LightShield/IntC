"""GeneratePool ideas: layout and precision rewrites that start from P1."""

from intentc.stages.pool.strategies.align_loop_bound import AlignLoopBound
from intentc.stages.pool.strategies.halo_1d import Halo1D
from intentc.stages.pool.strategies.luma_q15 import LumaQ15
from intentc.stages.pool.strategies.narrow_accum import NarrowAccum
from intentc.stages.pool.strategies.narrow_int_field import NarrowIntField
from intentc.stages.pool.strategies.pad_and_mask import PadAndMask
from intentc.stages.pool.strategies.predicated_update import PredicatedUpdate
from intentc.stages.pool.strategies.squared_compare import SquaredCompare
from intentc.stages.pool.strategies.structure_of_arrays import ArrayOfStructsToSoA

PERFORMANCE_CATALOG = [
    PadAndMask(),
    NarrowIntField(),
    ArrayOfStructsToSoA(),
    AlignLoopBound(),
    PredicatedUpdate(),
    Halo1D(),
    SquaredCompare(),
    NarrowAccum(),
    LumaQ15(),
]

__all__ = [
    "PERFORMANCE_CATALOG",
    "PadAndMask",
    "NarrowIntField",
    "ArrayOfStructsToSoA",
    "AlignLoopBound",
    "PredicatedUpdate",
    "Halo1D",
    "SquaredCompare",
    "NarrowAccum",
    "LumaQ15",
]
