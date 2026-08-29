from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PermissionPolicy:
    """Declares which tools an agent role may access."""

    role: str
    allowed_tools: set[str] = field(default_factory=set)
    max_tool_calls: int = 50
    can_write_filesystem: bool = False
    can_write_github: bool = False
    can_write_database: bool = False

    def is_allowed(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools


PREDEFINED_ROLES: dict[str, PermissionPolicy] = {
    "readonly": PermissionPolicy(
        role="readonly",
        allowed_tools={"filesystem", "github", "arxiv", "search", "calculator"},
        can_write_filesystem=False,
        can_write_github=False,
    ),
    "research": PermissionPolicy(
        role="research",
        allowed_tools={"arxiv", "search", "calculator", "filesystem"},
        can_write_filesystem=True,
    ),
    "write": PermissionPolicy(
        role="write",
        allowed_tools={"filesystem", "github", "search", "calculator"},
        can_write_filesystem=True,
        can_write_github=True,
    ),
}
