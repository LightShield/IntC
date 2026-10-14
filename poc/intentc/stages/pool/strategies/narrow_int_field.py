"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class NarrowIntField:
    """Change a struct field of type int/int32_t named `space` to uint8_t.

    For command streams whose tag cardinality fits in a byte (OGRE TransformSpace
    has three values). The candidate is still checked by V, including that
    comparisons to 0, 1, 2 remain correct.
    """

    name = "narrow-int-field"

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        del params
        tree, data = syntax.parse(sk.code)
        edits: list[tuple[int, int, str]] = []
        for n in syntax.walk(tree.root_node):
            if n.type != "field_declaration":
                continue
            ty = n.child_by_field_name("type")
            decl = n.child_by_field_name("declarator")
            if ty is None or decl is None:
                continue
            ty_txt = data[ty.start_byte:ty.end_byte].decode().strip()
            if ty_txt not in {"int", "int32_t"}:
                continue
            fname = decl.text.decode() if decl.type == "field_identifier" else None
            if fname != "space":
                continue
            edits.append((ty.start_byte, ty.end_byte, "uint8_t"))
        if not edits:
            return []
        code = syntax.replace_spans(data, edits)
        return [Sketch(code, sk.side_constraints, sk.applied + (self.name,), sk.extra_params)]
