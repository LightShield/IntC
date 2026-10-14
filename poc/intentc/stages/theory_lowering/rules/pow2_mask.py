"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class Pow2Mask:
    """`e % N` -> `(e) & (N - 1)` where N is an implementation parameter; requires is_pow2(N).

    The two agree only for non-negative e. The rewrite does not check this
    syntactically. The candidate is verified against the contract, including CBMC's
    UB checks, before it can be used.
    """

    name = "pow2-mask"

    def sites(self, code: str, params: set[str]) -> list[tuple[int, int, str, str]]:
        tree, data = syntax.parse(code)
        out = []
        for n in syntax.walk(tree.root_node):
            if n.type != "binary_expression":
                continue
            op = n.child_by_field_name("operator")
            right = n.child_by_field_name("right")
            left = n.child_by_field_name("left")
            if op is None or op.text.decode() != "%" or right is None or right.type != "identifier":
                continue
            p = right.text.decode()
            if p not in params:
                continue
            out.append((n.start_byte, n.end_byte, f"(({left.text.decode()}) & ({p} - 1))", p))
        return out

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        """One sketch per site (a rewrite may apply at several sites)."""
        _, data = syntax.parse(sk.code)
        results = []
        for s, e, text, p in self.sites(sk.code, params):
            code = syntax.replace_spans(data, [(s, e, text)])
            results.append(Sketch(code, sk.side_constraints + (f"is_pow2({p})",),
                                  sk.applied + (f"{self.name}@{s}",), sk.extra_params))
        return results
