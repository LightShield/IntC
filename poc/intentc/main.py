"""CLI: `intentc <contract.yaml> [-o out.c]`
         `intentc <source.c> <contract.yaml> [-o out.c]`  (v1-style; source must match contract.baseline)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from intentc.pipeline import compile_intent, summary
from intentc.contract import load as load_contract


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="intentc",
        description="Compile a C baseline against its intent contract.",
    )
    ap.add_argument("paths", type=Path, nargs="+", help="contract.yaml, or baseline.c contract.yaml")
    ap.add_argument("-o", "--output", type=Path, default=None)
    ap.add_argument("--workdir", type=Path, default=Path("tmp/intentc"))
    args = ap.parse_args(argv)
    if len(args.paths) == 1:
        contract = args.paths[0]
        source = None
    elif len(args.paths) == 2:
        source, contract = args.paths
    else:
        ap.error("expected <contract.yaml> or <source.c> <contract.yaml>")
        return 2
    if not contract.is_file():
        print(f"contract not found: {contract}", file=sys.stderr)
        return 2
    if source is not None and not source.is_file():
        print(f"source not found: {source}", file=sys.stderr)
        return 2
    spec = load_contract(contract)
    if source is not None and spec.baseline.resolve() != source.resolve():
        print(
            f"error: source {source} does not match contract baseline {spec.baseline}",
            file=sys.stderr,
        )
        return 2
    ctx = compile_intent(contract, args.workdir, args.output)
    print(summary(ctx))
    # Exit 1 only when nothing was admitted. A failed TheoryLower that GeneratePool
    # recovers from is still a successful compile. P1 winning the measurement leaves
    # winner unset but the pool nonempty.
    return 0 if ctx.pool else 1


if __name__ == "__main__":
    sys.exit(main())
