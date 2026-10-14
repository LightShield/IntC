"""Verification cost model kappa_V: an estimate of proof cost from program structure.

A weighted count of features known to drive bit-precise SMT cost. Integer-valued
(granularity delta = 1), so TheoryLower terminates. The weights are a heuristic;
whether kappa_V predicts solver time is an experiment, not an assumption.
"""

from __future__ import annotations

from intentc import syntax

WEIGHTS = {
    "div_rem_nonpow2": 10,  # / or % whose divisor is not a power-of-two literal
    "mul_nonconst": 3,      # * with two non-literal operands
    "loop": 2,
    "deref": 1,
}


def _is_pow2_literal(text: str) -> bool:
    try:
        v = int(text.rstrip("uUlL"), 0)
    except ValueError:
        return False
    return v > 0 and v & (v - 1) == 0


def features(code: str, values: dict[str, int] | None = None) -> dict[str, int]:
    """Feature counts. `values` gives parameter values, so `x % N` with N a power of two is cheap."""
    tree, _ = syntax.parse(code)
    f = dict.fromkeys(WEIGHTS, 0)
    for n in syntax.walk(tree.root_node):
        if n.type == "binary_expression":
            op = n.child_by_field_name("operator").text.decode()
            l, r = n.child_by_field_name("left"), n.child_by_field_name("right")
            rt = r.text.decode()
            if r.type == "identifier" and values and rt in values:
                rt = str(values[rt])
            pow2 = (r.type in {"number_literal", "identifier"}) and _is_pow2_literal(rt)
            if op in {"/", "%"} and not pow2:
                f["div_rem_nonpow2"] += 1
            elif op == "*" and l.type != "number_literal" and r.type != "number_literal":
                f["mul_nonconst"] += 1
        elif n.type in {"for_statement", "while_statement", "do_statement"}:
            f["loop"] += 1
        elif n.type == "pointer_expression" and n.child_by_field_name("operator").text.decode() == "*":
            f["deref"] += 1
    return f


def kappa(code: str, values: dict[str, int] | None = None) -> int:
    return sum(WEIGHTS[k] * v for k, v in features(code, values).items())
