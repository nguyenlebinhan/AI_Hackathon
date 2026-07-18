from types import SimpleNamespace

import pytest

from app.core.permissions import UserRole
from app.model.documents import DocumentApprovalStatus
from app.model.users import UserStatus
from app.policies.document_policy import DocumentPolicy


def _actor(*, role: UserRole = UserRole.USER) -> SimpleNamespace:
    return SimpleNamespace(
        id="user-a",
        commune_id="commune-a",
        role=role,
        is_active=True,
        status=UserStatus.ACTIVE,
    )


def _document(**updates: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "owner_id": "user-a",
        "commune_id": "commune-a",
        "meeting_id": None,
        "approval_status": DocumentApprovalStatus.DRAFT,
        "is_deleted": False,
        "deleted_at": None,
    }
    values.update(updates)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    ("updates", "allowed"),
    [
        ({}, True),
        ({"owner_id": "other"}, False),
        ({"commune_id": "commune-b"}, False),
        ({"meeting_id": "meeting-1"}, False),
        ({"approval_status": DocumentApprovalStatus.APPROVED}, False),
        ({"approval_status": DocumentApprovalStatus.PENDING_APPROVAL}, False),
        ({"is_deleted": True}, False),
    ],
)
def test_user_delete_policy_requires_all_conditions(
    updates: dict[str, object],
    allowed: bool,
) -> None:
    assert DocumentPolicy.can_delete(_actor(), _document(**updates)) is allowed


def test_admin_is_still_tenant_scoped() -> None:
    actor = _actor(role=UserRole.ADMIN)
    assert DocumentPolicy.can_delete(actor, _document()) is True
    assert DocumentPolicy.can_delete(actor, _document(commune_id="commune-b")) is False
