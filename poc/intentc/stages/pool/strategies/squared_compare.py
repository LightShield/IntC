"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class SquaredCompare:
    """`sqrtf(E) < R` (or `<=`, `sqrt`) -> `(E) < (R)*(R)`.

    Agrees for nonnegative E and R except at floating rounding of sqrt.
    The candidate is verified against the contract, not against P1.
    """

    name = "squared-compare"
    _SQRT = {"sqrtf", "sqrt"}
    _OPS = {"<", "<="}

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        del params
        tree, data = syntax.parse(sk.code)
        edits: list[tuple[int, int, str]] = []
        for n in syntax.walk(tree.root_node):
            if n.type != "binary_expression":
                continue
            op = n.child_by_field_name("operator")
            left = n.child_by_field_name("left")
            right = n.child_by_field_name("right")
            if op is None or left is None or right is None:
                continue
            sym = op.text.decode()
            if sym not in self._OPS:
                continue
            arg = self._sqrt_arg(left, data)
            bound = right
            if arg is None:
                if sym != "<":
                    continue
                arg = self._sqrt_arg(right, data)
                bound = left
                if arg is None:
                    continue
                repl = f"({data[bound.start_byte:bound.end_byte].decode()})*({data[bound.start_byte:bound.end_byte].decode()}) < ({data[arg.start_byte:arg.end_byte].decode()})"
            else:
                repl = (
                    f"({data[arg.start_byte:arg.end_byte].decode()}) {sym} "
                    f"({data[bound.start_byte:bound.end_byte].decode()})*"
                    f"({data[bound.start_byte:bound.end_byte].decode()})"
                )
            edits.append((n.start_byte, n.end_byte, repl))
        if not edits:
            return []
        code = syntax.replace_spans(data, edits)
        return [Sketch(code, sk.side_constraints, sk.applied + (self.name,), sk.extra_params)]

    def _sqrt_arg(self, n, data: bytes):
        cur = n
        if cur.type == "parenthesized_expression" and cur.named_children:
            cur = cur.named_children[0]
        if cur.type != "call_expression":
            return None
        fn = cur.child_by_field_name("function")
        args = cur.child_by_field_name("arguments")
        if fn is None or args is None or fn.type != "identifier":
            return None
        if fn.text.decode() not in self._SQRT:
            return None
        named = list(args.named_children)
        if len(named) != 1:
            return None
        return named[0]
