from __future__ import annotations

import time
from pathlib import Path

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult

SANDBOX_ROOT = Path("/tmp/scion-sandbox")


class FilesystemInput(BaseModel):
    operation: str  # read, write, list
    path: str
    content: str | None = None


class FilesystemTool(Tool):
    """
    Sandboxed filesystem tool.
    All paths are resolved relative to SANDBOX_ROOT.
    Raises PermissionError if a path escapes the sandbox.
    """

    def __init__(self) -> None:
        SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return (
            "Read, write, and list files within the sandboxed workspace. "
            "Operations: 'read' (returns file content), "
            "'write' (writes content to file, creates if not exists), "
            "'list' (lists files in directory). "
            "All paths are relative to the workspace root."
        )

    @property
    def input_schema(self) -> type[BaseModel]:
        return FilesystemInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ, ToolPermission.WRITE}

    def _safe_path(self, path: str) -> Path:
        resolved = (SANDBOX_ROOT / path).resolve()
        if not str(resolved).startswith(str(SANDBOX_ROOT.resolve())):
            raise PermissionError(f"Path '{path}' escapes sandbox")
        return resolved

    async def execute(self, input: BaseModel) -> ToolResult:
        assert isinstance(input, FilesystemInput)
        start = time.time()

        try:
            path = self._safe_path(input.path)

            if input.operation == "read":
                if not path.exists():
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"File not found: {input.path}",
                        execution_time_ms=(time.time() - start) * 1000,
                    )
                content = path.read_text()
                return ToolResult(
                    success=True,
                    output=content,
                    execution_time_ms=(time.time() - start) * 1000,
                )

            elif input.operation == "write":
                if input.content is None:
                    return ToolResult(
                        success=False,
                        output=None,
                        error="Content required for write operation",
                        execution_time_ms=(time.time() - start) * 1000,
                    )
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(input.content)
                return ToolResult(
                    success=True,
                    output=f"Written {len(input.content)} characters to {input.path}",
                    execution_time_ms=(time.time() - start) * 1000,
                )

            elif input.operation == "list":
                if not path.exists():
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Directory not found: {input.path}",
                        execution_time_ms=(time.time() - start) * 1000,
                    )
                entries = [
                    {
                        "name": e.name,
                        "type": "dir" if e.is_dir() else "file",
                        "size": e.stat().st_size if e.is_file() else 0,
                    }
                    for e in sorted(path.iterdir())
                ]
                return ToolResult(
                    success=True,
                    output=entries,
                    execution_time_ms=(time.time() - start) * 1000,
                )

            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown operation: {input.operation}. Use read, write, or list.",
                    execution_time_ms=(time.time() - start) * 1000,
                )

        except PermissionError as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000,
            )
