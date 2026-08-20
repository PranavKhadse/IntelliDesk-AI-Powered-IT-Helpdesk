import json
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def log_ticket_event(
    db: Session,
    ticket_id: str,
    actor_id: Optional[str],
    action: str,
    previous_state: Optional[Any] = None,
    new_state: Optional[Any] = None
) -> AuditLog:
    """Create an immutable audit log record for a ticket action."""
    prev_str = json.dumps(previous_state) if isinstance(previous_state, (dict, list)) else str(previous_state) if previous_state is not None else None
    new_str = json.dumps(new_state) if isinstance(new_state, (dict, list)) else str(new_state) if new_state is not None else None

    audit_entry = AuditLog(
        ticket_id=ticket_id,
        actor_id=actor_id,
        action=action,
        previous_state=prev_str,
        new_state=new_str
    )
    db.add(audit_entry)
    db.flush()
    return audit_entry
