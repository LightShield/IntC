# IntentCompile PoC — design and integrity rules

The package root is the CLI (`main.py`) plus owned
directories: `pipeline/` (driver + context), `contract/` (Phi and I),
`syntax/` (C text, CST edits, Sketch), `verify/` (CBMC), `target/` (L_Target),
`stages/` (s1..s7 and catalogs). Catalogs:
TheoryLower rules under `stages/theory_lowering/`, GeneratePool strategies
under `stages/pool/strategies/`. BudgetNormalize is `s4_budget_normalize.py`.
The verifier
checks the **program** against harnesses (CBMC), not formulas over
parameter names.

## Integrity rules (non-negotiable)

1. **No result without a mechanism.** No hard-coded latencies, instruction
   counts, "verified" flags, or matching on benchmark names. Every number
   comes from running code. Every "proved" comes from CBMC on the candidate
   plus harness.
2. **Unsupported means rejected.** Parse failures are errors. The pipeline
   does not skip or approximate silently.
3. **Unknown is not proved.** Timeouts, unwinding-bound exhaustion, CBMC
   errors, and undecided properties are `unknown`. Only every property
   `SUCCESS` (including unwinding assertions) is `proved`.
4. **Measurement compiles the candidate.** Footprint and timing use MSVC
   `/O2` on the generated source. Nothing is estimated in the winner step.
5. **Outputs are generated.** Emitted programs come from baseline + contract
   through the pipeline. Hand-written comparison programs live under
   `cases/*/handwritten/` or in tests, and are labeled as such.
6. **Scope is stated.** `README.md` and `CLAIMS.md` list implemented vs
   designed. A row is not "implemented" until a test or recorded run exists.

## What "proved" means

- CBMC 6.11.0, UB checks (bounds, pointers, signed overflow, div-by-zero,
  undefined shift), `--unwinding-assertions`, `--arrays-uf-always`.
- Harnesses: `nondet_*`, `__CPROVER_assert`. Parameters via `intent_params.h`.
- Admission is `⊨_K` for the harness bound K. The baseline is never required
  to be proved. If no candidate is admitted, the baseline is emitted unchanged.
