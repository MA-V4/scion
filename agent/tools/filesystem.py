from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from agent.tools.base import Tool, ToolPermission, ToolResult

ALLOWED_ROOT = Path("/tmp/scion-sandbox")


class ReadFileInput(BaseModel):
    path: str


class WriteFileInput(BaseModel):
    path: str
    content: str


class ListDirInput(BaseModel):
    path: str = "."


class FilesystemTool(Tool):
    """
    Sandboxed filesystem tool. All paths are resolved relative to ALLOWED_ROOT.
    Raises PermissionError if a path escapes the sandbox.
    """

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "Read, write, and list files within the sandboxed workspace directory."

    @property
    def input_schema(self) -> type[BaseModel]:
        return ReadFileInput

    @property
    def permissions(self) -> set[ToolPermission]:
        return {ToolPermission.READ, ToolPermission.WRITE}

    def _safe_path(self, path: str) -> Path:
        ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)
        resolved = (ALLOWED_ROOT / path).resolve()
        if not str(resolved).startswith(str(ALLOWED_ROOT)):
            raise PermissionError(f"Path '{path}' escapes sandbox")
        return resolved

    async def execute(self, input: BaseModel) -> ToolResult:
        # TODO: dispatch on operation field; implement read/write/list
        raise NotImplementedError
