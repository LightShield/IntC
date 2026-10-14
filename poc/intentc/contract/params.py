"""Parameter constraints (I and rewrite side constraints) as Z3 formulas.

Constraint expressions use Python/C-like syntax over parameter names:
comparisons, + - * // %, constant <<, and/or/not, and the predicates
is_pow2(x) and pow2_pair(x, s) meaning x == 2**s. Arithmetic is unbounded-integer
arithmetic, so a constraint means what it says mathematically; bit-width limits
are added separately.
"""

from __future__ import annotations

import ast

import z3

_BIN = {
    ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
    ast.FloorDiv: lambda a, b: a / b, ast.Mod: lambda a, b: a % b,
}
_CMP = {
    ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b, ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b,
}


def is_pow2(x: z3.ArithRef, bits: int) -> z3.BoolRef:
    return z3.Or([x == (1 << i) for i in range(bits)])


def compile_constraint(expr: str, env: dict[str, z3.ArithRef], bits: int = 64) -> z3.BoolRef:
    def ev(n: ast.AST):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Name):
            if n.id not in env:
                raise ValueError(f"unknown parameter '{n.id}' in constraint '{expr}'")
            return env[n.id]
        if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool):
            return z3.IntVal(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            return z3.Not(ev(n.operand))
        if isinstance(n, ast.BoolOp):
            vals = [ev(v) for v in n.values]
            return z3.And(vals) if isinstance(n.op, ast.And) else z3.Or(vals)
        if isinstance(n, ast.Compare):
            parts, left = [], ev(n.left)
            for op, c in zip(n.ops, n.comparators):
                right = ev(c)
                if type(op) not in _CMP:
                    raise ValueError(f"unsupported comparison in '{expr}'")
                parts.append(_CMP[type(op)](left, right))
                left = right
            return z3.And(parts)
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.LShift):
            left, right = ev(n.left), ev(n.right)
            if z3.is_int_value(left) and z3.is_int_value(right):
                lv, rv = left.as_long(), right.as_long()
                if rv < 0 or rv >= bits:
                    raise ValueError(f"shift out of range in '{expr}'")
                return z3.IntVal(lv << rv)
            raise ValueError(f"non-constant << in '{expr}'; use pow2_pair(x, s)")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "is_pow2" and len(n.args) == 1:
            return is_pow2(ev(n.args[0]), bits)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "pow2_pair" and len(n.args) == 2:
            value, shift = ev(n.args[0]), ev(n.args[1])
            # Exponents 0..31 only: Optimize rejects 2**63 numerals in this encoding.
            return z3.Or([z3.And(shift == i, value == (1 << i)) for i in range(min(bits, 32))])
        raise ValueError(f"unsupported construct in constraint '{expr}': {ast.dump(n)[:80]}")

    return ev(ast.parse(expr, mode="eval"))
