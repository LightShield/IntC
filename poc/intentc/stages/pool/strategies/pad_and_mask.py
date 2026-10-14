"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class PadAndMask:
    """Split a logical capacity N into N (fullness) and STORAGE (array and index).

    Indexing becomes a mask on STORAGE. Fullness comparisons on N are left alone.
    Requires N to be an array bound, a remainder, and a comparison operand, and
    requires STORAGE not already defined. The candidate is verified against the
    contract before it can be used.
    """

    name = "pad-and-mask"
    STORE = "STORAGE"

    def _logical(self, code: str, params: set[str]) -> str | None:
        if self.STORE in syntax.defines(code):
            return None
        tree, _ = syntax.parse(code)
        array_bounds, remainders, compared = set(), set(), set()
        for n in syntax.walk(tree.root_node):
            if n.type == "array_declarator":
                size = n.child_by_field_name("size")
                if size is not None and size.type == "identifier" and size.text.decode() in params:
                    array_bounds.add(size.text.decode())
            elif n.type == "binary_expression":
                op = n.child_by_field_name("operator")
                right = n.child_by_field_name("right")
                left = n.child_by_field_name("left")
                if op is None:
                    continue
                sym = op.text.decode()
                if sym == "%" and right is not None and right.type == "identifier":
                    remainders.add(right.text.decode())
                if sym in {"==", "!=", "<", ">", "<=", ">="}:
                    for side in (left, right):
                        if side is not None and side.type == "identifier":
                            compared.add(side.text.decode())
        candidates = (array_bounds & remainders & compared) & params
        if len(candidates) != 1:
            return None
        return next(iter(candidates))

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        n = self._logical(sk.code, params)
        if n is None:
            return []
        tree, data = syntax.parse(sk.code)
        edits: list[tuple[int, int, str]] = []
        insert_at = None
        for node in syntax.walk(tree.root_node):
            if node.type == "preproc_def":
                name = node.child_by_field_name("name")
                if name is not None and name.text.decode() == n:
                    insert_at = node.end_byte
            elif node.type == "array_declarator":
                size = node.child_by_field_name("size")
                if size is not None and size.type == "identifier" and size.text.decode() == n:
                    edits.append((size.start_byte, size.end_byte, self.STORE))
            elif node.type == "binary_expression":
                op = node.child_by_field_name("operator")
                right = node.child_by_field_name("right")
                left = node.child_by_field_name("left")
                if op is None or op.text.decode() != "%" or right is None or right.type != "identifier":
                    continue
                if right.text.decode() != n or left is None:
                    continue
                edits.append((node.start_byte, node.end_byte,
                              f"(({left.text.decode()}) & ({self.STORE} - 1))"))
        if insert_at is None or not edits:
            return []
        value = syntax.defines(sk.code)[n].value
        edits.append((insert_at, insert_at, f"#define {self.STORE} {value}\n"))
        code = syntax.replace_spans(data, edits)
        return [Sketch(
            code,
            sk.side_constraints + (f"is_pow2({self.STORE})", f"{self.STORE} >= {n}"),
            sk.applied + (self.name,),
            sk.extra_params + (self.STORE,),
        )]
