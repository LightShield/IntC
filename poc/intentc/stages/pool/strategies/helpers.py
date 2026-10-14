"""Shared AST helpers for GeneratePool strategies."""

from __future__ import annotations


def subscript_index(node, data: bytes) -> tuple[str, str] | None:
    """Return (array_name, index_text) for `a[i]`, or None."""
    if node.type != "subscript_expression":
        return None
    base = node.child_by_field_name("argument")
    idx = node.child_by_field_name("index")
    if idx is None:
        for c in node.children:
            if c.type == "subscript_argument_list":
                inner = [x for x in c.children if x.type not in {"[", "]", ","}]
                idx = inner[0] if inner else None
                break
    if base is None or idx is None or base.type != "identifier":
        return None
    return base.text.decode(), data[idx.start_byte:idx.end_byte].decode()
