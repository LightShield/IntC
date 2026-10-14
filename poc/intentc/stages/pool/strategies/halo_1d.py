"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class Halo1D:
    """3-point 1D stencil with zero edges -> padded interior loop.

    Matches a for-loop over a parameter N whose body uses `i == 0` and `i == N - 1`
    (or `i == N-1`) to clamp neighbours. Introduces PN = N+2 and a halo buffer.
    """

    name = "halo-1d"

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        if "PN" in syntax.defines(sk.code) or "halo_in" in sk.code:
            return []
        tree, data = syntax.parse(sk.code)
        loop = None
        nname = None
        for n in syntax.walk(tree.root_node):
            if n.type != "for_statement":
                continue
            text = data[n.start_byte:n.end_byte].decode()
            if "i == 0" not in text:
                continue
            if "N - 1" not in text and "N-1" not in text:
                continue
            cond = n.child_by_field_name("condition")
            if cond is None:
                continue
            for b in syntax.walk(cond):
                if b.type == "binary_expression":
                    right = b.child_by_field_name("right")
                    if right is not None and right.type == "identifier" and right.text.decode() in params:
                        nname = right.text.decode()
            if nname is None:
                continue
            loop = n
            break
        if loop is None or nname is None:
            return []
        defined = syntax.defines(sk.code)
        if nname not in defined:
            return []
        insert_at = None
        for node in syntax.walk(tree.root_node):
            if node.type == "preproc_def":
                name = node.child_by_field_name("name")
                if name is not None and name.text.decode() == nname:
                    insert_at = node.end_byte
        if insert_at is None:
            return []
        halo = (
            f"\n#define PN 0\n"
            f"static int32_t halo_in[PN];\n"
        )
        body = (
            "{\n"
            "    halo_in[0] = 0;\n"
            f"    halo_in[{nname} + 1] = 0;\n"
            f"    for (int i = 0; i < {nname}; i++) halo_in[i + 1] = in[i];\n"
            f"    for (int i = 1; i <= {nname}; i++)\n"
            "        out[i - 1] = halo_in[i] + halo_in[i - 1] + halo_in[i + 1];\n"
            "}"
        )
        # Replace the for-loop, including a following compound body if present.
        end = loop.end_byte
        nxt = loop.next_named_sibling
        # for_statement usually includes its body as a child; loop.end_byte is enough.
        edits = [
            (insert_at, insert_at, halo),
            (loop.start_byte, end, body),
        ]
        code = syntax.replace_spans(data, edits)
        nval = defined[nname].value
        return [Sketch(
            code,
            sk.side_constraints + (f"PN == {nname} + 2",),
            sk.applied + (self.name,),
            sk.extra_params + ("PN",),
        )]
