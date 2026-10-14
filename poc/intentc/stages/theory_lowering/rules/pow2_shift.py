"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class Pow2Shift:
    """`e / D` -> `(e) >> S` where D and S are parameters; requires pow2_pair(D, S).

    Integer division by D and a right shift by S agree on non-negative e only when
    D == 2**S. The candidate is verified against the contract before it can be used.
    """

    name = "pow2-shift"

    def sites(self, code: str, params: set[str]) -> list[tuple[int, int, str, str, str]]:
        tree, data = syntax.parse(code)
        out = []
        if "SHIFT" not in params:
            return out
        for n in syntax.walk(tree.root_node):
            if n.type != "binary_expression":
                continue
            op = n.child_by_field_name("operator")
            right = n.child_by_field_name("right")
            left = n.child_by_field_name("left")
            if op is None or op.text.decode() != "/" or right is None or right.type != "identifier":
                continue
            d = right.text.decode()
            if d not in params or d == "SHIFT":
                continue
            out.append((n.start_byte, n.end_byte, f"(({left.text.decode()}) >> SHIFT)", d, "SHIFT"))
        return out

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        _, data = syntax.parse(sk.code)
        results = []
        for s, e, text, d, sh in self.sites(sk.code, params):
            code = syntax.replace_spans(data, [(s, e, text)])
            results.append(Sketch(
                code,
                sk.side_constraints + (f"pow2_pair({d}, {sh})",),
                sk.applied + (f"{self.name}@{s}",),
                sk.extra_params,
            ))
        return results
