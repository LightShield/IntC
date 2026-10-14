"""Every catalog case that is supposed to admit a candidate must do so via compile_intent."""
from pathlib import Path

import pytest

from intentc.pipeline import compile_intent, summary
from intentc.target import VCVARS
from intentc.verify.cbmc import CBMC

HAVE = CBMC.is_file() and VCVARS.is_file()
pytestmark = pytest.mark.skipif(not HAVE, reason="CBMC or MSVC not installed")

# (contract, substring that must appear in the emitted winner)
ADMIT = [
    ("cases/ringbuffer/contract_ci.yaml", "& (CAPACITY - 1)"),
    ("cases/ringbuffer_exact/contract_ci.yaml", "& (STORAGE - 1)"),
    ("cases/hashset/contract_ci.yaml", "& (NBUCKETS - 1)"),
    ("cases/decimation/contract_ci.yaml", ">> SHIFT"),
    ("cases/scale/contract_ci.yaml", "<< SH_GAIN"),
    ("cases/particles/contract_ci.yaml", "p_x[N]"),
    ("cases/flecs_pool/contract_ci.yaml", "* (alive[i])"),
    ("cases/stencil1d/contract_ci.yaml", "halo_in"),
    ("cases/fir_block/contract_ci.yaml", "#define BLOCK 8"),
    ("cases/ogre_pack/contract_ci.yaml", "uint8_t space"),
    ("cases/inrange/contract_ci.yaml", "(d2) < (R)*(R)"),
    ("cases/innerprod/contract_ci.yaml", "float result"),
    ("cases/luma/contract_ci.yaml", "9798"),
    ("cases/particles_fat/contract_ci.yaml", "p_x[N]"),
]


@pytest.mark.parametrize("contract,marker", ADMIT, ids=[Path(c).parent.name for c, _ in ADMIT])
def test_catalog_case_admits_through_pipeline(tmp_path, contract, marker):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path(contract), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.pool, summary(ctx)
    assert ctx.winner is not None, summary(ctx)
    assert "baseline kept unchanged" not in text
    assert marker in text, summary(ctx)
