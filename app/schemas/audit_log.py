from datetime import datetime
from typing import Any

from app.model.security import AuditLog, AuditResult
from app.schemas.base import StrictAPIModel


class AuditLogPublic(StrictAPIModel):
    id: str
    commune_id: str | None
    actor_user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    result: AuditResult
    reason: str | None
    ip_address: str | None
    request_id: str
    metadata: dict[str, Any]
    created_at: datetime


def audit_to_public(audit_log: AuditLog) -> AuditLogPublic:
    return AuditLogPublic(
        id=audit_log.id,
        commune_id=audit_log.commune_id,
        actor_user_id=audit_log.actor_user_id,
        action=audit_log.action,
        resource_type=audit_log.resource_type,
        resource_id=audit_log.resource_id,
        result=audit_log.result,
        reason=audit_log.reason,
        ip_address=audit_log.ip_address,
        request_id=audit_log.request_id,
        metadata=audit_log.metadata_json,
        created_at=audit_log.created_at,
    )
