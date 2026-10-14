"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class LumaQ15:
    """BT.601 float MAC `0.299*r + 0.587*g + 0.114*b` -> Q15 `(9798*r+19235*g+3735*b)>>15`.

    Matches the three BT.601 coefficients in the source, not a named kernel.
    """

    name = "luma-q15"
    _Q15 = {"0.299": 9798, "0.587": 19235, "0.114": 3735}

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        del params
        tree, data = syntax.parse(sk.code)
        edits: list[tuple[int, int, str]] = []
        for n in syntax.walk(tree.root_node):
            if n.type != "binary_expression":
                continue
            if any(s <= n.start_byte < e for s, e, _ in edits):
                continue
            parts = self._bt601(n, data)
            if parts is None:
                continue
            r, g, b = parts
            edits.append((
                n.start_byte, n.end_byte,
                f"({self._Q15['0.299']}*({r})+{self._Q15['0.587']}*({g})+{self._Q15['0.114']}*({b}))>>15",
            ))
        if not edits:
            return []
        code = syntax.replace_spans(data, edits)
        return [Sketch(code, sk.side_constraints, sk.applied + (self.name,), sk.extra_params)]

    def _bt601(self, n, data: bytes) -> tuple[str, str, str] | None:
        terms = self._addends(n)
        if len(terms) != 3:
            return None
        found: dict[str, str] = {}
        for t in terms:
            pair = self._coeff_expr(t, data)
            if pair is None:
                return None
            key, expr = pair
            if key in found:
                return None
            found[key] = expr
        if set(found) != set(self._Q15):
            return None
        return found["0.299"], found["0.587"], found["0.114"]

    def _addends(self, n) -> list:
        if n.type == "parenthesized_expression" and n.named_children:
            return self._addends(n.named_children[0])
        if n.type == "binary_expression":
            op = n.child_by_field_name("operator")
            if op is not None and op.text.decode() == "+":
                left = n.child_by_field_name("left")
                right = n.child_by_field_name("right")
                if left is None or right is None:
                    return [n]
                return self._addends(left) + self._addends(right)
        return [n]

    def _coeff_expr(self, n, data: bytes) -> tuple[str, str] | None:
        cur = n
        if cur.type == "parenthesized_expression" and cur.named_children:
            cur = cur.named_children[0]
        if cur.type != "binary_expression":
            return None
        op = cur.child_by_field_name("operator")
        left = cur.child_by_field_name("left")
        right = cur.child_by_field_name("right")
        if op is None or left is None or right is None or op.text.decode() != "*":
            return None
        for a, b in ((left, right), (right, left)):
            key = self._coeff_key(a, data)
            if key is not None:
                return key, self._drop_float_cast(b, data)
        return None

    def _coeff_key(self, n, data: bytes) -> str | None:
        t = data[n.start_byte:n.end_byte].decode().strip().lower().rstrip("f")
        return t if t in self._Q15 else None

    def _drop_float_cast(self, n, data: bytes) -> str:
        cur = n
        if cur.type == "parenthesized_expression" and cur.named_children:
            cur = cur.named_children[0]
        if cur.type == "cast_expression":
            ty = cur.child_by_field_name("type")
            val = cur.child_by_field_name("value")
            if ty is not None and val is not None:
                if "float" in data[ty.start_byte:ty.end_byte].decode():
                    return data[val.start_byte:val.end_byte].decode()
        return data[n.start_byte:n.end_byte].decode()
