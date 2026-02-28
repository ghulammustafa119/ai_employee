"""Agent roles and permission enforcement for Platinum tier."""

from enum import Enum


class AgentRole(Enum):
    CLOUD = "cloud"
    LOCAL = "local"


CAPABILITIES = {
    AgentRole.CLOUD: {
        "can_draft": True,
        "can_send": False,
        "can_approve": False,
        "can_write_dashboard": False,
        "can_write_signals": True,
        "can_triage_email": True,
        "can_schedule_drafts": True,
        "owns_whatsapp": False,
        "owns_payments": False,
    },
    AgentRole.LOCAL: {
        "can_draft": True,
        "can_send": True,
        "can_approve": True,
        "can_write_dashboard": True,
        "can_write_signals": False,
        "can_triage_email": False,
        "can_schedule_drafts": False,
        "owns_whatsapp": True,
        "owns_payments": True,
    },
}


def check_permission(role: AgentRole, action: str) -> bool:
    return CAPABILITIES.get(role, {}).get(action, False)


def require_permission(role: AgentRole, action: str) -> None:
    if not check_permission(role, action):
        raise PermissionError(f"Agent '{role.value}' lacks permission: {action}")
