from __future__ import annotations

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult


class CalculatorInput(BaseModel):
    expression: str
    context: str | None = None


class CalculatorTool(Tool):
    """Evaluates mathematical expressions safely. No network required."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate mathematical expressions, unit conversions, and simple numerical computations."

    @property
    def input_schema(self) -> type[BaseModel]:
        return CalculatorInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ}

    async def execute(self, input: BaseModel) -> ToolResult:
        # TODO: use sympy or a safe eval for mathematical expressions
        raise NotImplementedError
