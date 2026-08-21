from dataclasses import dataclass


@dataclass
class ApprovalPolicy:
    """Small safety gate for actions that can change external state."""

    require_approval_for_external_write: bool = True
    require_approval_for_destructive_action: bool = True

    def allowed_without_approval(self, *, external_write: bool = False, destructive: bool = False) -> bool:
        if destructive and self.require_approval_for_destructive_action:
            return False
        if external_write and self.require_approval_for_external_write:
            return False
        return True
