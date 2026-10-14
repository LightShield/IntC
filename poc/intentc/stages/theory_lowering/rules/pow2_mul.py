"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class Pow2Mul:
    """`e * M` -> `(e) << SH_M` where M is a parameter; requires pow2_pair(M, SH_M).

    Introduces the shift hole. Multiplication by a literal, or by a parameter that
    I pins off the powers of two, is not rewritten. The candidate is verified
    against the contract before it can be used.
    """

    name = "pow2-mul"

    def _shift_name(self, param: str) -> str:
        return f"SH_{param}"

    def sites(self, code: str, params: set[str]) -> list[tuple[int, int, str, str]]:
        tree, data = syntax.parse(code)
        out = []
        for n in syntax.walk(tree.root_node):
            if n.type != "binary_expression":
                continue
            op = n.child_by_field_name("operator")
            right = n.child_by_field_name("right")
            left = n.child_by_field_name("left")
            if op is None or op.text.decode() != "*" or left is None or right is None:
                continue
            m = None
            expr = None
            if right.type == "identifier" and right.text.decode() in params:
                m, expr = right.text.decode(), left
            elif left.type == "identifier" and left.text.decode() in params:
                m, expr = left.text.decode(), right
            if m is None:
                continue
            sh = self._shift_name(m)
            if sh in params:
                continue
            out.append((n.start_byte, n.end_byte,
                        f"(({data[expr.start_byte:expr.end_byte].decode()}) << {sh})", m))
        return out

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        _, data = syntax.parse(sk.code)
        defined = syntax.defines(sk.code)
        results = []
        for s, e, text, m in self.sites(sk.code, params):
            sh = self._shift_name(m)
            edits = [(s, e, text)]
            extra = sk.extra_params
            if sh not in defined:
                if m not in defined:
                    continue
                insert_at = None
                tree, _ = syntax.parse(sk.code)
                for node in syntax.walk(tree.root_node):
                    if node.type == "preproc_def":
                        name = node.child_by_field_name("name")
                        if name is not None and name.text.decode() == m:
                            insert_at = node.end_byte
                if insert_at is None:
                    continue
                edits.append((insert_at, insert_at, f"#define {sh} 0\n"))
                extra = extra + (sh,)
            elif sh not in extra:
                extra = extra + (sh,)
            code = syntax.replace_spans(data, edits)
            results.append(Sketch(
                code,
                sk.side_constraints + (f"pow2_pair({m}, {sh})",),
                sk.applied + (f"{self.name}@{s}",),
                extra,
            ))
        return results
