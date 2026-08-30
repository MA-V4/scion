from __future__ import annotations

import ast
import math
import operator

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult


class CalculatorInput(BaseModel):
    expression: str


SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

SAFE_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "log": math.log,
    "abs": abs,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op = SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {node.op}")
        return op(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {node.op}")
        return op(_safe_eval(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls allowed")
        fn = SAFE_NAMES.get(node.func.id)
        if fn is None:
            raise ValueError(f"Unknown function: {node.func.id}")
        args = [_safe_eval(a) for a in node.args]
        return fn(*args)
    if isinstance(node, ast.Name):
        val = SAFE_NAMES.get(node.id)
        if val is None:
            raise ValueError(f"Unknown name: {node.id}")
        return val
    raise ValueError(f"Unsupported expression type: {type(node)}")


class CalculatorTool(Tool):
    """Safely evaluates mathematical expressions."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluate mathematical expressions. "
            "Supports +, -, *, /, **, sqrt, sin, cos, log, pi, e. "
            "Example: '847 * 0.15' or 'sqrt(144)'"
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return CalculatorInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ}

    async def execute(self, input: BaseModel) -> ToolResult:
        assert isinstance(input, CalculatorInput)
        try:
            tree = ast.parse(input.expression, mode="eval")
            result = _safe_eval(tree.body)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))