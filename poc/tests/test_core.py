"""Unit tests for the parts that do not need CBMC or MSVC."""
from pathlib import Path

import z3
import pytest

import eval_listings
from intentc.contract import params
from intentc.contract.spec import load as load_contract
from intentc import syntax
from intentc.syntax import Sketch
from intentc.pipeline import compile_intent
from intentc.pipeline.context import Candidate, Context
from intentc.stages.pool.strategies import (
    AlignLoopBound,
    ArrayOfStructsToSoA,
    Halo1D,
    LumaQ15,
    NarrowAccum,
    NarrowIntField,
    PadAndMask,
    PredicatedUpdate,
    SquaredCompare,
)
from intentc.stages.s1_check_realiz import check_realiz
from intentc.stages.s6_winner_selection import select_winner
from intentc.stages.theory_lowering import kappa
from intentc.stages.theory_lowering.rules import Pow2Mask, Pow2Mul, Pow2Shift

RING = open("cases/ringbuffer/baseline.c", encoding="utf-8").read()


def test_defines_and_set_parameters():
    assert syntax.defines(RING)["CAPACITY"].value == 1000
    out = syntax.set_parameters(RING, {"CAPACITY": 1024})
    assert syntax.defines(out)["CAPACITY"].value == 1024
    assert out.count("1024") == 1


def test_set_unknown_parameter_rejected():
    with pytest.raises(KeyError):
        syntax.set_parameters(RING, {"NOPE": 1})


def test_unparseable_source_is_rejected():
    with pytest.raises(ValueError, match="does not parse"):
        syntax.parse("not C @@@@")


def test_overlapping_edits_are_errors():
    with pytest.raises(ValueError):
        syntax.replace_spans(b"abcdef", [(0, 3, "x"), (2, 4, "y")])


def test_pow2_mask_rewrites_every_site_with_side_constraint():
    sk = Sketch(RING, (), ())
    once = Pow2Mask().apply_once(sk, {"CAPACITY"})
    assert len(once) == 2 and all("is_pow2(CAPACITY)" in o.side_constraints for o in once)
    twice = Pow2Mask().apply_once(once[0], {"CAPACITY"})
    assert len(twice) == 1 and "% CAPACITY" not in twice[0].code


def test_pow2_mask_ignores_non_parameters():
    assert Pow2Mask().sites("unsigned f(unsigned x){return x % 1000;}", {"CAPACITY"}) == []


def test_kappa_depends_on_parameter_values():
    assert kappa(RING, {"CAPACITY": 1000}) > kappa(RING, {"CAPACITY": 1024})


def test_constraints_compile_and_pow2():
    x = z3.Int("C")
    s = z3.Solver()
    s.add(params.compile_constraint("C >= 1000 and is_pow2(C)", {"C": x}, 64))
    s.add(x <= 1024)
    assert s.check() == z3.sat and s.model()[x].as_long() == 1024


def test_constraint_unknown_name_rejected():
    with pytest.raises(ValueError):
        params.compile_constraint("D > 1", {"C": z3.Int("C")})


def test_check_realiz_sat():
    ctx = Context(load_contract(Path("cases/ringbuffer/contract.yaml")), Path("tmp/test_sat"))
    ok, details = check_realiz(ctx)
    assert ok and ctx.baseline_params["CAPACITY"] == 1000
    assert "satisfiable" in details


def test_check_realiz_unsat_core():
    ctx = Context(load_contract(Path("cases/ringbuffer/contract_unsat.yaml")), Path("tmp/test_unsat"))
    ok, details = check_realiz(ctx)
    assert not ok and "contradictory" in details


def test_check_realiz_missing_define_emits_baseline(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/ringbuffer/contract_missing_param.yaml"), tmp_path / "work", out)
    assert ctx.winner is None
    assert any(s.stage.startswith("S1") and not s.ok for s in ctx.steps)
    assert "NOT_IN_SOURCE" in " ".join(s.details for s in ctx.steps)
    text = out.read_text(encoding="utf-8")
    assert "baseline kept unchanged" in text
    assert "#define CAPACITY 1000" in text


def test_contract_requires_a_harness(tmp_path):
    p = tmp_path / "empty.yaml"
    (tmp_path / "baseline.c").write_text("#define N 1\nint n = N;\n")
    p.write_text(
        "name: empty-post\nbaseline: baseline.c\n"
        "parameters:\n  - name: N\n    constraints: [\"N >= 1\"]\n"
        "harnesses: []\n"
    )
    with pytest.raises(Exception, match="at least one harness"):
        load_contract(p)


def test_cegis_max_tries_must_be_positive(tmp_path):
    p = tmp_path / "cap.yaml"
    (tmp_path / "baseline.c").write_text("#define N 1\nint n = N;\n")
    (tmp_path / "h.c").write_text("void harness(void) {}\n")
    p.write_text(
        "name: bad-cap\nbaseline: baseline.c\n"
        "parameters:\n  - name: N\n    constraints: [\"N >= 1\"]\n"
        "harnesses:\n  - file: h.c\n    unwind: 1\n"
        "cegis_max_tries: 0\n"
    )
    with pytest.raises(Exception, match="cegis_max_tries"):
        load_contract(p)


def test_pow2_shift_rewrites_div_with_pair_constraint():
    code = open("cases/decimation/baseline.c", encoding="utf-8").read()
    sk = Sketch(code, (), ())
    once = Pow2Shift().apply_once(sk, {"DIVISOR", "SHIFT"})
    assert len(once) == 1
    assert ">> SHIFT" in once[0].code
    assert "/ DIVISOR" not in once[0].code
    assert "pow2_pair(DIVISOR, SHIFT)" in once[0].side_constraints


def test_pow2_shift_needs_shift_parameter():
    code = "uint64_t f(uint64_t x){return x / DIVISOR;}"
    assert Pow2Shift().sites(code, {"DIVISOR"}) == []


def test_pow2_pair_and_constant_shift():
    d, s = z3.Int("D"), z3.Int("S")
    sol = z3.Solver()
    sol.add(params.compile_constraint("pow2_pair(D, S)", {"D": d, "S": s}, 16))
    sol.add(params.compile_constraint("D >= 1000", {"D": d, "S": s}))
    sol.add(params.compile_constraint("D <= 1024", {"D": d, "S": s}))
    assert sol.check() == z3.sat
    assert sol.model()[d].as_long() == 1024
    assert sol.model()[s].as_long() == 10
    assert params.compile_constraint("1 << 10", {}).as_long() == 1024


def test_physical_ring_mask_targets_storage():
    code = open("cases/ringbuffer_exact/baseline.c", encoding="utf-8").read()
    sites = Pow2Mask().sites(code, {"CAPACITY", "STORAGE"})
    assert {p for _, _, _, p in sites} == {"STORAGE"}


def test_pad_and_mask_introduces_storage_on_one_parameter_ring():
    sk = Sketch(RING, (), ())
    out = PadAndMask().apply_once(sk, {"CAPACITY"})
    assert len(out) == 1
    code = out[0].code
    assert "#define STORAGE 1000" in code
    assert "& (STORAGE - 1)" in code
    assert "% CAPACITY" not in code
    assert "tail - head == CAPACITY" in code
    assert "ring[STORAGE]" in code
    assert out[0].extra_params == ("STORAGE",)
    assert "is_pow2(STORAGE)" in out[0].side_constraints
    assert "STORAGE >= CAPACITY" in out[0].side_constraints


def test_pad_and_mask_skips_existing_storage_and_hashset():
    exact = open("cases/ringbuffer_exact/baseline.c", encoding="utf-8").read()
    hashset = open("cases/hashset/baseline.c", encoding="utf-8").read()
    assert PadAndMask().apply_once(Sketch(exact, (), ()), {"CAPACITY", "STORAGE"}) == []
    assert PadAndMask().apply_once(Sketch(hashset, (), ()), {"NBUCKETS", "MAXPROBE"}) == []


def test_unsat_contract_emits_baseline(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/ringbuffer/contract_unsat.yaml"), tmp_path / "work", out)
    assert ctx.winner is None
    text = out.read_text(encoding="utf-8")
    assert "baseline kept unchanged" in text
    assert "#define CAPACITY 1000" in text
    assert "% CAPACITY" in text


def test_cli_rejects_mismatched_source_and_unsat_exit(tmp_path):
    from intentc.main import main
    assert main(["cases/hashset/baseline.c", "cases/ringbuffer/contract_unsat.yaml"]) == 2
    rc = main([
        "cases/ringbuffer/contract_unsat.yaml",
        "-o", str(tmp_path / "out.c"),
        "--workdir", str(tmp_path / "work"),
    ])
    assert rc == 1


def test_theory_lower_stuck_emits_baseline(tmp_path):
    out = tmp_path / "out.c"
    ctx = compile_intent(Path("cases/loopsum/contract.yaml"), tmp_path / "work", out)
    assert ctx.winner is None
    assert any(s.stage.startswith("S2") and not s.ok for s in ctx.steps)
    text = out.read_text(encoding="utf-8")
    assert "baseline kept unchanged" in text
    assert "stuck" in " ".join(s.details for s in ctx.steps)
    assert "for (int i = 0; i < N; i++)" in text


def test_pow2_mask_on_hashset_four_remainder_sites():
    code = open("cases/hashset/baseline.c", encoding="utf-8").read()
    sites = Pow2Mask().sites(code, {"NBUCKETS", "MAXPROBE"})
    assert len(sites) == 4 and {p for _, _, _, p in sites} == {"NBUCKETS"}


def test_pow2_mul_introduces_shift_hole():
    code = open("cases/scale/baseline.c", encoding="utf-8").read()
    sk = Sketch(code, (), ())
    once = Pow2Mul().apply_once(sk, {"GAIN"})
    assert len(once) == 1
    assert "sample * GAIN" not in once[0].code
    assert "<< SH_GAIN" in once[0].code
    assert "#define SH_GAIN 0" in once[0].code
    assert "pow2_pair(GAIN, SH_GAIN)" in once[0].side_constraints
    assert once[0].extra_params == ("SH_GAIN",)


def test_pow2_mul_ignores_literals_and_non_parameters():
    code = "uint32_t f(uint32_t x){return x * 10;}"
    assert Pow2Mul().sites(code, {"GAIN"}) == []
    code = "uint32_t f(uint32_t x){return x * GAIN;}"
    assert Pow2Mul().sites(code, {"DIVISOR"}) == []


def test_aos_to_soa_splits_particle_array():
    code = open("cases/particles/baseline.c", encoding="utf-8").read()
    out = ArrayOfStructsToSoA().apply_once(Sketch(code, (), ()), {"N"})
    assert len(out) == 1
    soa = out[0].code
    assert "p[i].x" not in soa
    assert "p_x[i]" in soa and "p_vx[i]" in soa
    assert "static int32_t p_x[N];" in soa
    assert "typedef struct" in soa
    assert out[0].applied == ("aos-to-soa",)


def test_aos_to_soa_skips_ring_hash_scale():
    for path, names in [
        ("cases/ringbuffer/baseline.c", {"CAPACITY"}),
        ("cases/hashset/baseline.c", {"NBUCKETS", "MAXPROBE"}),
        ("cases/scale/baseline.c", {"GAIN"}),
    ]:
        code = open(path, encoding="utf-8").read()
        assert ArrayOfStructsToSoA().apply_once(Sketch(code, (), ()), names) == []


def test_align_loop_bound_on_fir_block():
    code = open("cases/fir_block/baseline.c", encoding="utf-8").read()
    out = AlignLoopBound().apply_once(Sketch(code, (), ()), {"BLOCK", "TAPS"})
    assert len(out) == 1
    assert "BLOCK % 4 == 0" in out[0].side_constraints
    assert "for (int i = 0; i < BLOCK; i++)" in out[0].code


def test_predicated_update_on_flecs():
    code = open("cases/flecs_pool/baseline.c", encoding="utf-8").read()
    out = PredicatedUpdate().apply_once(Sketch(code, (), ()), {"CAP"})
    assert len(out) == 1
    assert "if (alive[i]) x[i] += d" not in out[0].code
    assert "x[i] += (d) * (alive[i])" in out[0].code
    assert "if (!alive[i])" in out[0].code


def test_halo_1d_on_stencil():
    code = open("cases/stencil1d/baseline.c", encoding="utf-8").read()
    out = Halo1D().apply_once(Sketch(code, (), ()), {"N"})
    assert len(out) == 1
    assert "halo_in" in out[0].code
    assert "PN == N + 2" in out[0].side_constraints
    assert out[0].extra_params == ("PN",)


def test_narrow_int_field_on_ogre():
    code = open("cases/ogre_pack/baseline.c", encoding="utf-8").read()
    out = NarrowIntField().apply_once(Sketch(code, (), ()), {"N"})
    assert len(out) == 1
    assert "uint8_t space" in out[0].code
    assert "typedef struct {\n    uint8_t space;" in out[0].code


def test_pow2_mask_parenthesizes_under_equality():
    code = "int f(int x){return x % N == 0;}"
    out = Pow2Mask().apply_once(Sketch(code, (), ()), {"N"})
    assert len(out) == 1
    assert "((x) & (N - 1)) == 0" in out[0].code


def test_pow2_mul_parenthesizes_under_add():
    code = "#define M 8\nuint32_t f(uint32_t a, uint32_t x){return a + x * M;}\n"
    out = Pow2Mul().apply_once(Sketch(code, (), ()), {"M"})
    assert len(out) == 1
    assert "a + ((x) << SH_M)" in out[0].code


def test_squared_compare_bound_lt_sqrt():
    code = "int f(float d2, float R){return R < sqrtf(d2);}\n"
    out = SquaredCompare().apply_once(Sketch(code, (), ()), set())
    assert len(out) == 1
    assert "(R)*(R) < (d2)" in out[0].code
    assert ">" not in out[0].code


def test_squared_compare_drops_sqrtf():
    code = open("cases/inrange/baseline.c", encoding="utf-8").read()
    out = SquaredCompare().apply_once(Sketch(code, (), ()), {"RBOUND"})
    assert len(out) == 1
    assert "sqrtf" not in out[0].code
    assert "(d2) < (R)*(R)" in out[0].code
    assert out[0].applied == ("squared-compare",)


def test_narrow_accum_drops_double_cast():
    code = open("cases/innerprod/baseline.c", encoding="utf-8").read()
    out = NarrowAccum().apply_once(Sketch(code, (), ()), {"LEN"})
    assert len(out) == 1
    assert "double result" not in out[0].code
    assert "float result" in out[0].code
    assert "(double)" not in out[0].code
    assert "double inner" in out[0].code


def test_luma_q15_rewrites_bt601_mac():
    code = open("cases/luma/baseline.c", encoding="utf-8").read()
    out = LumaQ15().apply_once(Sketch(code, (), ()), {"NPX"})
    assert len(out) == 1
    assert "0.299f" not in out[0].code
    assert "(9798*(rgb[3 * i + 0])+19235*(rgb[3 * i + 1])+3735*(rgb[3 * i + 2]))>>15" in out[0].code


def test_aos_to_soa_on_fat_particles():
    code = open("cases/particles_fat/baseline.c", encoding="utf-8").read()
    out = ArrayOfStructsToSoA().apply_once(Sketch(code, (), ()), {"N"})
    assert len(out) == 1
    assert "p[i].x" not in out[0].code
    assert "p_x[i]" in out[0].code and "p_density[i]" in out[0].code
    assert "static int32_t p_x[N];" in out[0].code


EVAL = Path(__file__).resolve().parents[2] / "experiments" / "eval"


def test_bench_stats_report_spread():
    from intentc.target import BenchStats
    s = BenchStats.from_values([1.0, 1.0, 2.0, 3.0, 3.0])
    assert s.median == 2.0
    assert s.min == 1.0 and s.max == 3.0
    assert s.stdev > 0
    assert s.q1 <= s.median <= s.q3
    assert s.as_json()["n"] == 5


def test_slot_1000_listing_has_ten_instructions_before_ret():
    asm = (EVAL / "asif_slot.asm").read_text(encoding="utf-8")
    ops = eval_listings.masm_proc_instructions(asm, "slot_1000")
    assert len(ops) == 10
    assert any("imul" in o.lower() for o in ops)


def test_inrange_baseline_listing_has_sqrtss():
    asm = (EVAL / "inrange_baseline.asm").read_text(encoding="utf-8")
    assert "sqrtss" in asm.lower()


def test_div1024_misses_2_5_percent_below_pre_floor():
    def rel_ok(tick: int, divisor: int) -> bool:
        got = tick // divisor
        diff = abs(got * 1000 - tick)
        return diff * 40 <= tick

    assert not rel_ok(599000, 1024)
    assert rel_ok(600000, 1024)
    assert rel_ok(640000, 1024)
    assert rel_ok(640000, 1000)


def test_winner_prefers_baseline_on_equal_median(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "intentc.stages.s6_winner_selection.target.run_bench",
        lambda *a, **k: 4.0,
    )
    ctx = Context(load_contract(Path("cases/ringbuffer/contract_measure_ci.yaml")), tmp_path)
    ctx.baseline_code = RING
    ctx.pool = [Candidate("tie", RING, {"CAPACITY": 1024}, proofs=[])]
    ok, msg = select_winner(ctx)
    assert ok
    assert ctx.winner is None
    assert ctx.baseline_measured == 4.0
    assert "baseline kept" in msg


def test_winner_takes_strictly_faster_candidate(tmp_path, monkeypatch):
    def fake(_code, _bench, _trials, _workdir, tag):
        return 4.0 if tag == "baseline" else 3.0

    monkeypatch.setattr("intentc.stages.s6_winner_selection.target.run_bench", fake)
    ctx = Context(load_contract(Path("cases/ringbuffer/contract_measure_ci.yaml")), tmp_path)
    ctx.baseline_code = RING
    ctx.pool = [Candidate("faster", RING, {"CAPACITY": 1024}, proofs=[])]
    ok, msg = select_winner(ctx)
    assert ok
    assert ctx.winner is not None and ctx.winner.name == "faster"
    assert "winner faster" in msg


def test_winner_keeps_earlier_on_near_tie(tmp_path, monkeypatch):
    from intentc.target import BenchStats

    def fake(_code, _bench, _trials, _workdir, tag):
        if tag == "baseline":
            return BenchStats.from_values([4.0] * 31)
        return BenchStats.from_values([3.5] * 16 + [4.5] * 15)

    monkeypatch.setattr("intentc.stages.s6_winner_selection.target.run_bench", fake)
    ctx = Context(load_contract(Path("cases/ringbuffer/contract_measure_ci.yaml")), tmp_path)
    ctx.baseline_code = RING
    ctx.pool = [Candidate("noise", RING, {"CAPACITY": 1024}, proofs=[])]
    ok, msg = select_winner(ctx)
    assert ok
    assert ctx.winner is None
    assert "baseline kept" in msg

