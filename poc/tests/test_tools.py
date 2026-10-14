"""Integration tests that run CBMC and MSVC (skipped if the tools are missing)."""
from pathlib import Path
import shutil
import subprocess
import pytest

from intentc import target
from intentc import syntax
from intentc.pipeline import compile_intent
from intentc.verify import cbmc

HAVE = cbmc.CBMC.is_file() and target.VCVARS.is_file()
pytestmark = pytest.mark.skipif(not HAVE, reason="CBMC or MSVC not installed")
RING = Path("cases/ringbuffer")
STACK = (RING / "handwritten/stack.c").read_text(encoding="utf-8")


def _cand(tmp_path, code, values):
    (tmp_path / "candidate.c").write_text(code)
    (tmp_path / "intent_params.h").write_text(syntax.params_header(values))
    return tmp_path / "candidate.c"


def _masked(cap):
    code = (RING / "baseline.c").read_text().replace("% CAPACITY", "& (CAPACITY - 1)")
    return syntax.set_parameters(code, {"CAPACITY": cap})


def test_mask_1024_proved(tmp_path):
    c = _cand(tmp_path, _masked(1024), {"CAPACITY": 1024})
    r = cbmc.verify([c, RING / "harness_fifo.c"], [tmp_path], "harness", 8, 120, {"K": "4"})
    assert r.outcome == "proved"


def test_seeded_bug_gives_counterexample(tmp_path):
    code = _masked(1024).replace("    head++;", "    /* bug */")
    c = _cand(tmp_path, code, {"CAPACITY": 1024})
    r = cbmc.verify([c, RING / "harness_fifo.c"], [tmp_path], "harness", 8, 120, {"K": "4"})
    assert r.outcome == "counterexample" and r.failed


def test_too_small_unwind_is_unknown_not_proved(tmp_path):
    c = _cand(tmp_path, _masked(1024), {"CAPACITY": 1024})
    r = cbmc.verify([c, RING / "harness_fifo.c"], [tmp_path], "harness", 3, 120, {"K": "4"})
    assert r.outcome == "unknown" and "unwinding" in r.reason


def test_mixed_unwind_and_property_failure_is_unknown(tmp_path):
    """K larger than the unwind bound can fail both unwind and Post. That is unknown."""
    c = _cand(tmp_path, _masked(1024), {"CAPACITY": 1024})
    r = cbmc.verify([c, RING / "harness_fifo.c"], [tmp_path], "harness", 2, 120, {"K": "10"})
    assert r.outcome == "unknown"
    assert "unwinding" in r.reason


def test_mask_with_non_pow2_capacity_is_refuted(tmp_path):
    c = _cand(tmp_path, _masked(1000), {"CAPACITY": 1000})
    weak = cbmc.verify([c, RING / "harness_fifo.c"], [tmp_path], "harness", 6, 120, {"K": "4"})
    assert weak.outcome == "proved"
    strong = cbmc.verify([c, RING / "harness_fifo.c"], [tmp_path], "harness", 12, 300, {"K": "10"})
    assert strong.outcome == "counterexample"


def test_static_memory_is_compiled_sizeof(tmp_path):
    assert target.static_memory(_masked(1024), tmp_path) == 1024 * 8 + 16
    assert target.static_memory((RING / "baseline.c").read_text(), tmp_path) == 1000 * 8 + 16


def test_capacity_only_harness_accepts_stack(tmp_path):
    c = _cand(tmp_path, STACK, {"CAPACITY": 1024})
    r = cbmc.verify(
        [c, RING / "harness_capacity_only.c"], [tmp_path], "harness", 8, 120, {"K": "4"}
    )
    assert r.outcome == "proved"


def test_fifo_harness_refutes_stack(tmp_path):
    c = _cand(tmp_path, STACK, {"CAPACITY": 1024})
    r = cbmc.verify([c, RING / "harness_fifo.c"], [tmp_path], "harness", 8, 120, {"K": "4"})
    assert r.outcome == "counterexample"


def test_physical_storage_1024_capacity_1000_proved(tmp_path):
    exact = Path("cases/ringbuffer_exact")
    code = (exact / "baseline.c").read_text().replace("% STORAGE", "& (STORAGE - 1)")
    code = syntax.set_parameters(code, {"CAPACITY": 1000, "STORAGE": 1024})
    c = _cand(tmp_path, code, {"CAPACITY": 1000, "STORAGE": 1024})
    r = cbmc.verify([c, exact / "harness_fifo.c"], [tmp_path], "harness", 8, 120, {"K": "4"})
    assert r.outcome == "proved"


def test_physical_slack_pipeline_emits_padded_storage(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/ringbuffer_exact/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "#define CAPACITY 1000" in text
    assert "#define STORAGE 1024" in text
    assert "& (STORAGE - 1)" in text
    assert "% STORAGE" not in text


def test_decimation_shift_proved(tmp_path):
    dec = Path("cases/decimation")
    code = (dec / "baseline.c").read_text().replace("/ DIVISOR", ">> SHIFT")
    code = syntax.set_parameters(code, {"DIVISOR": 1024, "SHIFT": 10})
    c = _cand(tmp_path, code, {"DIVISOR": 1024, "SHIFT": 10})
    r = cbmc.verify([c, dec / "harness_error.c"], [tmp_path], "harness", 1, 120, {})
    assert r.outcome == "proved"


def test_decimation_pipeline_emits_shift(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/decimation/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "#define DIVISOR 1024" in text
    assert "#define SHIFT 10" in text
    assert ">> SHIFT" in text
    assert "/ DIVISOR" not in text


def test_tight_memory_keeps_baseline(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(RING / "contract_tight_memory.yaml", tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is None
    assert "#define CAPACITY 1000" in text
    assert "% CAPACITY" in text
    assert "baseline kept unchanged" in text
    mem_notes = " ".join(s.details for s in ctx.steps if s.stage.startswith("S4"))
    assert ">" in mem_notes and "8016" in mem_notes


def test_generate_pool_adds_physical_pad_from_one_parameter_ring(tmp_path):
    ctx = compile_intent(RING / "contract_ci.yaml", tmp_path / "work", tmp_path / "out.c")
    logical = [c for c in ctx.pool if "STORAGE" not in c.params]
    physical = [c for c in ctx.pool if c.params.get("STORAGE") == 1024 and c.params.get("CAPACITY") == 1000]
    assert len(logical) == 1 and logical[0].params["CAPACITY"] == 1024
    assert len(physical) == 1
    assert "& (STORAGE - 1)" in physical[0].code
    assert "tail - head == CAPACITY" in physical[0].code
    assert "% CAPACITY" not in physical[0].code
    text = (tmp_path / "out.c").read_text(encoding="utf-8")
    assert "admitted: 2 candidate" in text
    assert "no objective; emitted first admitted candidate" in text


def test_cegis_unknown_stops_and_keeps_baseline(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(RING / "contract_timeout.yaml", tmp_path / "work", out)
    assert ctx.winner is None
    log = "\n".join(ctx.log)
    assert "unknown" in log.lower()
    assert "not refuted" in log
    assert "CEGIS try " in log
    text = out.read_text(encoding="utf-8")
    assert "baseline kept unchanged" in text
    assert "% CAPACITY" in text
    assert "#define CAPACITY 1000" in text


def test_winner_selection_measures_pool(tmp_path):
    ctx = compile_intent(RING / "contract_measure_ci.yaml", tmp_path / "work", tmp_path / "out.c")
    assert ctx.baseline_measured is not None
    assert ctx.pool and all(c.measured is not None for c in ctx.pool)
    text = (tmp_path / "out.c").read_text(encoding="utf-8")
    assert "admitted:" in text
    if ctx.winner is not None:
        assert ctx.winner.measured < ctx.baseline_measured
        assert "measured:" in text
    else:
        assert "no admitted candidate measured faster" in text


def test_cegis_excludes_refuted_1024_and_proves_2048(tmp_path):
    ctx = compile_intent(RING / "contract_cegis_skip.yaml", tmp_path / "work", tmp_path / "out.c")
    log = "\n".join(ctx.log)
    assert "CAPACITY': 1024" in log.replace(" ", "") or "{'CAPACITY': 1024}" in log
    assert "counterexample" in log
    assert ctx.winner is not None
    assert ctx.winner.params["CAPACITY"] == 2048
    text = (tmp_path / "out.c").read_text(encoding="utf-8")
    assert "#define CAPACITY 2048" in text
    assert "& (CAPACITY - 1)" in text
    assert "harness_floor.c" in text
    assert "harness_fifo.c" in text


def test_impossible_budget_still_emits_baseline(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(RING / "contract_impossible_budget.yaml", tmp_path / "work", out)
    assert ctx.winner is None
    notes = " ".join(s.details for s in ctx.steps if s.stage.startswith("S4"))
    assert "also exceeds" in notes
    text = out.read_text(encoding="utf-8")
    assert "baseline kept unchanged" in text
    assert "% CAPACITY" in text
    assert "#define CAPACITY 1000" in text


def test_cegis_attempt_cap_stops_after_refuted_1024(tmp_path):
    ctx = compile_intent(RING / "contract_cegis_cap.yaml", tmp_path / "work", tmp_path / "out.c")
    log = "\n".join(ctx.log)
    assert ctx.winner is None
    assert "gave up after 1 tries" in log
    assert "2048" not in log
    text = (tmp_path / "out.c").read_text(encoding="utf-8")
    assert "baseline kept unchanged" in text
    assert "#define CAPACITY 1000" in text
    assert "% CAPACITY" in text


def test_scale_pipeline_emits_shift(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/scale/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "#define GAIN 8" in text
    assert "#define SH_GAIN 3" in text
    assert "<< SH_GAIN" in text
    assert "sample * GAIN" not in text


def test_particles_pipeline_emits_soa_after_theory_lower_stuck(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/particles/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert any(s.stage.startswith("S2") and not s.ok for s in ctx.steps)
    assert any(s.stage.startswith("S5") and s.ok for s in ctx.steps)
    assert ctx.winner is not None
    assert "p_x[N]" in text
    assert "p[i].x" not in text
    assert "aos-to-soa" in ctx.winner.name


def test_flecs_pipeline_predications(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/flecs_pool/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "x[i] += (d) * (alive[i])" in text
    assert "if (alive[i]) x[i] += d" not in text


def test_stencil_pipeline_emits_halo(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/stencil1d/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "halo_in" in text
    assert "#define PN 6" in text


def test_fir_pipeline_aligns_block(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/fir_block/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "#define BLOCK 8" in text
    assert "BLOCK % 4 == 0" in " ".join(ctx.log) or ctx.winner.params["BLOCK"] == 8


def test_ogre_pipeline_narrows_space(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/ogre_pack/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert any("uint8_t space" in c.code for c in ctx.pool)
    assert "uint8_t space" in text or "cmds_space" in text


def test_hashset_pipeline_emits_mask(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/hashset/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert ctx.winner.params["NBUCKETS"] == 16384
    assert "& (NBUCKETS - 1)" in text
    assert "% NBUCKETS" not in text


def test_inrange_pipeline_emits_squared_compare(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/inrange/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "sqrtf" not in text
    assert "(d2) < (R)*(R)" in text
    assert "squared-compare" in ctx.winner.name


def test_innerprod_pipeline_emits_float_accum(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/innerprod/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "float result" in text
    assert "(double)data2" not in text
    assert "narrow-accum" in ctx.winner.name


def test_luma_pipeline_emits_q15(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/luma/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "9798" in text
    assert "0.299f" not in text
    assert "luma-q15" in ctx.winner.name


def test_particles_fat_pipeline_emits_soa(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/particles_fat/contract_ci.yaml"), tmp_path / "work", out)
    text = out.read_text(encoding="utf-8")
    assert ctx.winner is not None
    assert "p_x[N]" in text
    assert "p[i].x" not in text
    assert "aos-to-soa" in ctx.winner.name


def test_inrange_bench_tu_emits_sqrtss(tmp_path):
    d = tmp_path / "fa"
    d.mkdir()
    (d / "candidate.c").write_text(Path("cases/inrange/baseline.c").read_text(encoding="utf-8"), encoding="utf-8")
    (d / "main.c").write_text(Path("cases/inrange/bench.c").read_text(encoding="utf-8"), encoding="utf-8")
    env = target.msvc_env()
    path = env.get("PATH") or env.get("Path")
    cl = shutil.which("cl", path=path) or shutil.which("cl.exe", path=path)
    p = subprocess.run(
        [cl, "/nologo", "/O2", "/c", "/FAs", "/Fainrange.asm", "main.c"],
        cwd=d, env=env, capture_output=True, text=True,
    )
    assert p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    asm = (d / "inrange.asm").read_text(encoding="utf-8", errors="replace")
    assert "sqrtss" in asm.lower()

