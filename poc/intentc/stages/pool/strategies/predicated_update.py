"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch
from intentc.stages.pool.strategies.helpers import subscript_index as _subscript_index


class PredicatedUpdate:
    """`if (flag[i]) x[i] += e` -> `x[i] += (e) * (flag[i])` when the if has no else.

    Equivalent when flag[i] is 0 or 1. The harness must keep that. Removes a
    data-dependent branch on a sparse active mask (Flecs-style iteration).
    """

    name = "predicated-update"

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        del params
        tree, data = syntax.parse(sk.code)
        edits: list[tuple[int, int, str]] = []
        for n in syntax.walk(tree.root_node):
            if n.type != "if_statement":
                continue
            if n.child_by_field_name("alternative") is not None:
                continue
            cond = n.child_by_field_name("condition")
            body = n.child_by_field_name("consequence")
            if cond is None or body is None:
                continue
            inner = cond
            if inner.type == "condition_clause":
                inner = inner.child_by_field_name("value") or (
                    inner.named_children[0] if inner.named_children else inner
                )
            if inner.type == "parenthesized_expression" and inner.named_children:
                inner = inner.named_children[0]
            if inner.type == "unary_expression":
                continue
            sub = _subscript_index(inner, data)
            if sub is None:
                continue
            flag, idx = sub
            stmt = body
            if stmt.type == "compound_statement":
                stmts = [c for c in stmt.named_children]
                if len(stmts) != 1:
                    continue
                stmt = stmts[0]
            if stmt.type != "expression_statement" or not stmt.named_children:
                continue
            expr = stmt.named_children[0]
            if expr.type != "assignment_expression":
                continue
            left = expr.child_by_field_name("left")
            right = expr.child_by_field_name("right")
            op = expr.child_by_field_name("operator")
            if left is None or right is None or op is None or op.text.decode() != "+=":
                continue
            lhs = _subscript_index(left, data)
            if lhs is None or lhs[1] != idx:
                continue
            rhs = data[right.start_byte:right.end_byte].decode()
            edits.append((
                n.start_byte, n.end_byte,
                f"{lhs[0]}[{idx}] += ({rhs}) * ({flag}[{idx}]);",
            ))
        if not edits:
            return []
        code = syntax.replace_spans(data, edits)
        return [Sketch(code, sk.side_constraints, sk.applied + (self.name,), sk.extra_params)]
