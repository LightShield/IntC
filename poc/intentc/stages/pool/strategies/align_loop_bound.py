"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class AlignLoopBound:
    """Keep the loop text, require the bound parameter to be a multiple of 4.

    Used when a developer allows rounding a block length up so a production
    compiler can emit a stride-4 body without a scalar remainder. No AST edit
    other than the side constraint. Skipped when the baseline value is already
    aligned, so it does not re-admit an unchanged program.
    """

    name = "align-loop-bound"
    ALIGN = 4

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        defined = syntax.defines(sk.code)
        tree, data = syntax.parse(sk.code)
        bounds: set[str] = set()
        for n in syntax.walk(tree.root_node):
            if n.type != "for_statement":
                continue
            cond = n.child_by_field_name("condition")
            if cond is None:
                continue
            for b in syntax.walk(cond):
                if b.type != "binary_expression":
                    continue
                op = b.child_by_field_name("operator")
                right = b.child_by_field_name("right")
                if op is None or right is None or op.text.decode() != "<":
                    continue
                if right.type == "identifier" and right.text.decode() in params:
                    bounds.add(right.text.decode())
        results = []
        for p in sorted(bounds):
            if p not in defined:
                continue
            if defined[p].value < self.ALIGN:
                continue
            if defined[p].value % self.ALIGN == 0:
                continue
            results.append(Sketch(
                sk.code,
                sk.side_constraints + (f"{p} % {self.ALIGN} == 0",),
                sk.applied + (f"{self.name}:{p}",),
                sk.extra_params,
            ))
        return results
