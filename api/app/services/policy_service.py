"""
SteerPlane API — Policy Service

Business logic layer for policy CRUD and evaluation.
"""

import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from typing import Optional

from ..models.policy import Policy


class PolicyService:
    """Service layer for policy operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_policy(
        self,
        name: str,
        description: str | None = None,
        allowed_actions: list[str] | None = None,
        denied_actions: list[str] | None = None,
        rate_limits: list[dict] | None = None,
        require_approval: list[str] | None = None,
        is_active: bool = True,
    ) -> Policy:
        """Create a new policy."""
        policy = Policy(
            id=f"pol_{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            allowed_actions=allowed_actions,
            denied_actions=denied_actions,
            rate_limits=rate_limits,
            require_approval=require_approval,
            is_active=is_active,
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self.db.query(Policy).filter(Policy.id == policy_id).first()

    def get_policy_by_name(self, name: str) -> Optional[Policy]:
        """Get a policy by name."""
        return self.db.query(Policy).filter(Policy.name == name).first()

    def list_policies(
        self,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Policy], int]:
        """List policies with pagination."""
        query = self.db.query(Policy)
        if active_only:
            query = query.filter(Policy.is_active == True)
        total = query.count()
        policies = (
            query
            .order_by(Policy.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return policies, total

    def update_policy(
        self,
        policy_id: str,
        name: str | None = None,
        description: str | None = None,
        allowed_actions: list[str] | None = None,
        denied_actions: list[str] | None = None,
        rate_limits: list[dict] | None = None,
        require_approval: list[str] | None = None,
        is_active: bool | None = None,
    ) -> Optional[Policy]:
        """Update an existing policy."""
        policy = self.get_policy(policy_id)
        if not policy:
            return None

        if name is not None:
            policy.name = name
        if description is not None:
            policy.description = description
        if allowed_actions is not None:
            policy.allowed_actions = allowed_actions
        if denied_actions is not None:
            policy.denied_actions = denied_actions
        if rate_limits is not None:
            policy.rate_limits = rate_limits
        if require_approval is not None:
            policy.require_approval = require_approval
        if is_active is not None:
            policy.is_active = is_active

        policy.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy. Returns True if found and deleted."""
        policy = self.get_policy(policy_id)
        if not policy:
            return False
        self.db.delete(policy)
        self.db.commit()
        return True

    def evaluate_action(self, policy_id: str, action: str) -> dict:
        """
        Evaluate whether an action is allowed under a policy.

        Returns a decision dict with 'allowed' status and 'reason'.
        Uses fnmatch-style glob matching, same as the SDK PolicyEngine.
        """
        import fnmatch

        policy = self.get_policy(policy_id)
        if not policy:
            return {"allowed": True, "reason": "Policy not found; defaulting to allow"}

        if not policy.is_active:
            return {"allowed": True, "reason": "Policy is inactive; defaulting to allow"}

        # Check deny list first (deny takes priority)
        if policy.denied_actions:
            for pattern in policy.denied_actions:
                if fnmatch.fnmatch(action, pattern):
                    return {
                        "allowed": False,
                        "reason": f"Action '{action}' matches deny pattern '{pattern}'",
                    }

        # Check allow list (if specified, action must match at least one)
        if policy.allowed_actions:
            for pattern in policy.allowed_actions:
                if fnmatch.fnmatch(action, pattern):
                    return {"allowed": True, "reason": f"Matches allow pattern '{pattern}'"}
            return {
                "allowed": False,
                "reason": f"Action '{action}' not in allowed actions list",
            }

        # Check approval requirement
        if policy.require_approval:
            for pattern in policy.require_approval:
                if fnmatch.fnmatch(action, pattern):
                    return {
                        "allowed": True,
                        "requires_approval": True,
                        "reason": f"Action '{action}' requires human approval",
                    }

        return {"allowed": True, "reason": "No restrictions matched"}
