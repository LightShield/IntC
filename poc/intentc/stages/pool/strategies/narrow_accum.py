"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class NarrowAccum:
    """`double acc = 0.0` plus `(double)` casts in that function -> `float` accum, casts dropped.

    Changes bits relative to a double MAC. Admission is the harness, not as-if.
    """

    name = "narrow-accum"

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        del params
        tree, data = syntax.parse(sk.code)
        edits: list[tuple[int, int, str]] = []
        for fn in syntax.walk(tree.root_node):
            if fn.type != "function_definition":
                continue
            body = fn.child_by_field_name("body")
            if body is None:
                continue
            accs: list = []
            casts: list = []
            for n in syntax.walk(body):
                if n.type == "declaration":
                    ty = n.child_by_field_name("type")
                    d = n.child_by_field_name("declarator")
                    if ty is None or d is None:
                        continue
                    if data[ty.start_byte:ty.end_byte].decode().strip() != "double":
                        continue
                    if d.type == "init_declarator":
                        inner = d.child_by_field_name("declarator")
                        val = d.child_by_field_name("value")
                        if inner is None or inner.type != "identifier" or val is None:
                            continue
                        vt = data[val.start_byte:val.end_byte].decode().strip()
                        if vt in {"0", "0.0", "0.0f", "0.f"}:
                            accs.append(ty)
                    elif d.type == "identifier":
                        accs.append(ty)
                elif n.type == "cast_expression":
                    ty = n.child_by_field_name("type")
                    val = n.child_by_field_name("value")
                    if ty is None or val is None:
                        continue
                    if data[ty.start_byte:ty.end_byte].decode().strip() != "double":
                        continue
                    casts.append((n, val))
            if not accs or not casts:
                continue
            for ty in accs:
                edits.append((ty.start_byte, ty.end_byte, "float"))
            for node, val in casts:
                edits.append((node.start_byte, node.end_byte,
                              data[val.start_byte:val.end_byte].decode()))
        if not edits:
            return []
        code = syntax.replace_spans(data, edits)
        return [Sketch(code, sk.side_constraints, sk.applied + (self.name,), sk.extra_params)]
