"""Logic for shared dependencies and security checks."""

from typing import Annotated
from fastapi import Header, HTTPException


# Verify if a user's role allows them to access a specific knowledge domain
async def verify_domain_access(
    x_user_role: Annotated[str, Header()] = "employee", domain: str = "general"
):
    """
    Check if the user has permission to access the requested domain.
    
    Args:
        x_user_role: User role from header
        domain: Target knowledge domain
    
    Raises:
        HTTPException: If access is denied
    """
    # Simulating RBAC logic (replace with real DB check later)
    allowed_domains = {
        "admin": ["legal", "hr", "engineering", "general"],
        "employee": ["general", "engineering"],
        "intern": ["general"],
    }

    # Check if the requested domain is within the role's permissions
    if domain and domain not in allowed_domains.get(x_user_role, []):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{x_user_role}' cannot access domain '{domain}'",
        )
    return True
