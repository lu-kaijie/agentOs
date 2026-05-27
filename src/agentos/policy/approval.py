"""Explicit approval policy for command execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePath


@dataclass(slots=True)
class ApprovalDecision:
    """Inspectable decision produced by the approval policy."""

    requires_approval: bool
    reason: str
    matched_rule: str
    risk_level: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class CommandApprovalPolicy:
    """Apply explicit approval rules to command execution."""

    def evaluate(self, command: list[str]) -> ApprovalDecision:
        if not command:
            return ApprovalDecision(
                requires_approval=False,
                reason="No command provided.",
                matched_rule="empty-command",
                risk_level="none",
            )

        head = PurePath(command[0]).name
        if self._is_shell_wrapper(command):
            return ApprovalDecision(
                requires_approval=True,
                reason=(
                    f"Command head '{head}' runs an inline shell script. "
                    "Use structured tools for reads/searches/tests, or request approval for shell execution."
                ),
                matched_rule="shell-wrapper",
                risk_level="medium",
            )
        if head in {"rm", "sudo"}:
            return ApprovalDecision(
                requires_approval=True,
                reason=f"Command head '{head}' is treated as destructive or privileged.",
                matched_rule="destructive-command",
                risk_level="high",
            )
        if head == "mv":
            return ApprovalDecision(
                requires_approval=True,
                reason="Command head 'mv' mutates workspace state and requires review.",
                matched_rule="workspace-mutation",
                risk_level="medium",
            )
        return ApprovalDecision(
            requires_approval=False,
            reason=f"Command head '{head}' is allowed by the default safe-command rule.",
            matched_rule="safe-command",
            risk_level="low",
        )

    def _is_shell_wrapper(self, command: list[str]) -> bool:
        if len(command) < 2:
            return False
        head = PurePath(command[0]).name
        return head in {"bash", "sh", "zsh", "fish"} and any(
            arg == "-c" or (arg.startswith("-") and not arg.startswith("--") and "c" in arg[1:])
            for arg in command[1:]
        )
