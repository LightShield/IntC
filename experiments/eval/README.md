# Evaluation tables for §7

Do not hand-edit `*.tex`. Times in JSON are one run. Outcomes below must hold
on a replay.

## One command

From `poc/` (Python 3.13, CBMC 6.11.0, MSVC 19.29, packages in `pyproject.toml`):

```
pip install -e .
python reproduce.py
```

Wall clock is about 12 minutes on the paper machine (i7-14700K). Then:

```
python reproduce.py --tex-only    # rebuild .tex from JSON
python reproduce.py --check       # outcomes only, no CBMC
```

Writes `experiments/eval/{catalog,ablations,workhorse}.{json,tex}` and
`asif_slot.asm`. `_work/` is a scratch tree (gitignored). Opcode counts on
those listings use `poc/eval_listings.py`, not `intentc`.

`pytest tests` is the pipeline test suite. It is not a substitute for
`reproduce.py`.

## Expected outcomes (check)

- Catalog: all fourteen rows admitted.
- Ring, ring-physical, hash: \(V\) on \(P_1\) is `unknown` (timeout). Winners proved. As-if class: ring/hash leave it; ring-physical is unexposed slack.
- Decimation, scale: leave as-if (divisor/gain). \(P_1\) proved (small harness).
- Particles, flecs, stencil, ogre: layout rewrites. \(P_1\) proved. Particles: TheoryLower fails, GeneratePool still admits SoA.
- FIR: align-loop-bound on BLOCK, leave as-if, \(P_1\) proved.
- In-range: squared-compare, leave as-if, \(P_1\) proved. Inner-product: narrow-accum, \(P_1\) proved. Luma: Q15, \(P_1\) unknown at 60\,s, winner proved. Fat particles: SoA at n=4, measured at N=1e5.
- Ablations: colliding `& 999` proved at \(K=4\), counterexample at \(K=10\); occupancy-only proves a LIFO stack, FIFO refutes it; 8016 B emit is \(P_1\).
- As-if listing: reciprocal multiply for `% 1000`, `and` 1023 for `% 1024` and the mask.
- Timed contracts: ring `CAPACITY=1024`, hash `NBUCKETS=16384`. Each ns cell is median ± sample stdev of 31 trials. Six rows: winner median strictly below \(P_1\). FIR: admitted `BLOCK=8` slower than \(P_1\), emit is \(P_1\).

Solver seconds may move. Parameter values and proved/unknown/counterexample must not.
