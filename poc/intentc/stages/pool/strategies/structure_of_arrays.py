"""Rewrite idea. Candidates are verified before use."""

from __future__ import annotations

from intentc import syntax
from intentc.syntax import Sketch


class ArrayOfStructsToSoA:
    """Split an array of structs into one array per scalar field.

    Matches a typedef of an anonymous struct with only scalar fields and exactly
    one array of that type, then rewrites `arr[i].field` to `arr_field[i]`.
    Pointers to the struct type, nested structs, and multiple arrays are skipped.
    Layout changes are unverified until V runs.
    """

    name = "aos-to-soa"

    _SKIP_TYPES = {"struct_specifier", "union_specifier", "array_declarator", "pointer_declarator"}

    def apply_once(self, sk: Sketch, params: set[str]) -> list[Sketch]:
        del params
        try:
            tree, data = syntax.parse(sk.code)
        except ValueError:
            return []
        spec = self._match(tree, data)
        if spec is None:
            return []
        tname, fields, arr_name, arr_decl, size_text = spec
        prefix = arr_name + "_"
        if any(prefix + f in sk.code for _, f in fields):
            return []
        edits: list[tuple[int, int, str]] = []
        for n in syntax.walk(tree.root_node):
            if n.type != "field_expression":
                continue
            arg = n.child_by_field_name("argument")
            fld = n.child_by_field_name("field")
            if arg is None or fld is None or arg.type != "subscript_expression":
                continue
            base = arg.child_by_field_name("argument")
            idx = arg.child_by_field_name("index")
            if idx is None:
                for c in arg.children:
                    if c.type == "subscript_argument_list":
                        inner = [x for x in c.children if x.type not in {"[", "]", ","}]
                        idx = inner[0] if inner else None
                        break
            if base is None or idx is None or base.type != "identifier":
                continue
            if base.text.decode() != arr_name:
                continue
            fname = fld.text.decode()
            if fname not in {f for _, f in fields}:
                continue
            idx_txt = data[idx.start_byte:idx.end_byte].decode()
            edits.append((n.start_byte, n.end_byte, f"{prefix}{fname}[{idx_txt}]"))
        decls = []
        lead = data[arr_decl.start_byte:arr_decl.child_by_field_name("declarator").start_byte].decode()
        # lead is like "static Particle " — keep only specifiers before the type name.
        specifiers = lead.replace(tname, "").strip()
        specifiers = (specifiers + " ") if specifiers else ""
        for ty, f in fields:
            decls.append(f"{specifiers}{ty} {prefix}{f}[{size_text}];")
        edits.append((arr_decl.start_byte, arr_decl.end_byte, "\n".join(decls)))
        if not any(e[0] != arr_decl.start_byte for e in edits):
            return []
        code = syntax.replace_spans(data, edits)
        return [Sketch(code, sk.side_constraints, sk.applied + (self.name,), sk.extra_params)]

    def _match(self, tree, data) -> tuple | None:
        structs: list[tuple[str, list[tuple[str, str]]]] = []
        for n in syntax.walk(tree.root_node):
            if n.type != "type_definition":
                continue
            ty = n.child_by_field_name("type")
            decl = n.child_by_field_name("declarator")
            if ty is None or decl is None or ty.type != "struct_specifier":
                continue
            if ty.child_by_field_name("name") is not None:
                continue
            tname = decl.text.decode()
            fields = self._scalar_fields(ty, data)
            if not fields:
                return None
            structs.append((tname, fields))
        if len(structs) != 1:
            return None
        tname, fields = structs[0]
        arrays = []
        for n in syntax.walk(tree.root_node):
            if n.type != "declaration":
                continue
            ty = n.child_by_field_name("type")
            d = n.child_by_field_name("declarator")
            if ty is None or d is None or ty.type != "type_identifier" or ty.text.decode() != tname:
                continue
            inner, size = self._array_size(d, data)
            if inner is None or inner.type != "identifier":
                return None
            arrays.append((inner.text.decode(), n, size))
        if len(arrays) != 1:
            return None
        if self._has_pointer_to(tree, tname):
            return None
        arr_name, arr_decl, size_text = arrays[0]
        return tname, fields, arr_name, arr_decl, size_text

    def _scalar_fields(self, struct, data) -> list[tuple[str, str]]:
        body = struct.child_by_field_name("body")
        if body is None:
            return []
        fields: list[tuple[str, str]] = []
        for n in body.children:
            if n.type != "field_declaration":
                continue
            ty = n.child_by_field_name("type")
            if ty is None or ty.type in self._SKIP_TYPES:
                return []
            ty_txt = data[ty.start_byte:ty.end_byte].decode().strip()
            found = False
            for c in syntax.walk(n):
                if c.type == "field_identifier":
                    fields.append((ty_txt, c.text.decode()))
                    found = True
                if c.type in self._SKIP_TYPES:
                    return []
            if not found:
                return []
        return fields

    def _array_size(self, decl, data) -> tuple:
        n = decl
        if n.type == "init_declarator":
            n = n.child_by_field_name("declarator")
            if n is None:
                return None, ""
        if n.type != "array_declarator":
            return None, ""
        inner = n.child_by_field_name("declarator")
        size = n.child_by_field_name("size")
        if inner is None or size is None:
            return None, ""
        return inner, data[size.start_byte:size.end_byte].decode()

    def _has_pointer_to(self, tree, tname: str) -> bool:
        for n in syntax.walk(tree.root_node):
            if n.type != "pointer_declarator":
                continue
            # `Particle *p` sits under a declaration whose type is Particle.
            p = n.parent
            while p is not None and p.type not in {"declaration", "parameter_declaration", "field_declaration"}:
                p = p.parent
            if p is None:
                continue
            ty = p.child_by_field_name("type")
            if ty is not None and ty.type == "type_identifier" and ty.text.decode() == tname:
                return True
        return False
