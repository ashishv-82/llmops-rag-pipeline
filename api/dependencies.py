from fastapi import Header, HTTPException
from typing import Annotated

""" Logic for shared dependencies and security checks """


# Verify if a user's role allows them to access a specific knowledge domain
async def verify_domain_access(
    x_user_role: Annotated[str, Header()] = "employee", domain: str = "general"
):
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
