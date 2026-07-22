"""The ``custom`` escape hatch: a sandboxed expression language (ADR-004).

Expressions are parsed with ``ast`` and evaluated against a restricted namespace
of the row's fields plus a small allowlist of functions. Only a whitelist of AST
node types is permitted — no attribute access, imports, comprehensions, lambdas,
or calls to anything outside the allowlist — and expression length is bounded.
This is security-critical: extend the allowlists deliberately and with tests.
"""

from __future__ import annotations

import ast
import operator
from collections.abc import Callable
from typing import Any

from mmm_os.transform.conditions import matches
from mmm_os.transform.registry import RuleContext, TransformError, register
from mmm_os.transform.types import RuleSpec, Table

MAX_EXPRESSION_LENGTH = 500

_BINOPS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
}
_COMPARE: dict[type[ast.cmpop], Callable[[Any, Any], Any]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}
_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "len": len,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "lower": lambda s: str(s).lower(),
    "upper": lambda s: str(s).upper(),
    "strip": lambda s: str(s).strip(),
    "coalesce": lambda *args: next((a for a in args if a is not None), None),
}


class SandboxError(TransformError):
    """Raised when an expression is disallowed or fails to evaluate safely."""


def evaluate(expression: str, names: dict[str, Any]) -> Any:
    """Evaluate a sandboxed expression against a namespace.

    Args:
        expression: The expression source.
        names: Variable bindings available to the expression (the row's fields).

    Returns:
        The evaluated value.

    Raises:
        SandboxError: If the expression is too long, unparseable, or uses a
            disallowed construct.
    """
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise SandboxError("expression exceeds maximum length")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise SandboxError(f"invalid expression: {exc}") from exc
    return _eval(tree.body, names)


def _eval(node: ast.AST, names: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in names:
            return names[node.id]
        raise SandboxError(f"unknown name: {node.id!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval(node.left, names), _eval(node.right, names))
    if isinstance(node, ast.UnaryOp):
        operand = _eval(node.operand, names)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.Not):
            return not operand
        raise SandboxError("disallowed unary operator")
    if isinstance(node, ast.BoolOp):
        return _eval_boolop(node, names)
    if isinstance(node, ast.Compare):
        return _eval_compare(node, names)
    if isinstance(node, ast.IfExp):
        return _eval(node.body, names) if _eval(node.test, names) else _eval(node.orelse, names)
    if isinstance(node, ast.Call):
        return _eval_call(node, names)
    if isinstance(node, ast.List):
        return [_eval(el, names) for el in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval(el, names) for el in node.elts)
    raise SandboxError(f"disallowed expression element: {type(node).__name__}")


def _eval_boolop(node: ast.BoolOp, names: dict[str, Any]) -> Any:
    if isinstance(node.op, ast.And):
        result: Any = True
        for value in node.values:
            result = _eval(value, names)
            if not result:
                return result
        return result
    result = False
    for value in node.values:
        result = _eval(value, names)
        if result:
            return result
    return result


def _eval_compare(node: ast.Compare, names: dict[str, Any]) -> bool:
    left = _eval(node.left, names)
    for op, comparator in zip(node.ops, node.comparators, strict=True):
        func = _COMPARE.get(type(op))
        if func is None:
            raise SandboxError("disallowed comparison operator")
        right = _eval(comparator, names)
        if not func(left, right):
            return False
        left = right
    return True


def _eval_call(node: ast.Call, names: dict[str, Any]) -> Any:
    if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
        raise SandboxError("disallowed function call")
    if node.keywords:
        raise SandboxError("keyword arguments are not allowed")
    args = [_eval(arg, names) for arg in node.args]
    return _FUNCTIONS[node.func.id](*args)


@register("custom")
def custom(table: Table, rule: RuleSpec, ctx: RuleContext) -> Table:
    """Evaluate a sandboxed expression per row and assign it to a field.

    ``params.expression`` is the expression; ``params.output`` names the target
    field (defaults to ``target_field``). The row's fields are the variables.
    """
    expression = rule.params.get("expression")
    if not expression:
        raise TransformError("custom requires params.expression")
    output = rule.params.get("output", rule.target_field)
    for row in table:
        if not matches(row, rule.condition):
            continue
        row[output] = evaluate(expression, dict(row))
    return table
