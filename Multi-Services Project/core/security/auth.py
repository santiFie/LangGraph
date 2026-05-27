import os
import json
from langgraph_sdk import Auth

auth = Auth()

# Initialize from VALID_TOKENS_JSON environment variable if available, else keep defaults
tokens_env = os.getenv("VALID_TOKENS_JSON")
if tokens_env:
    try:
        VALID_TOKENS = json.loads(tokens_env)
    except json.JSONDecodeError:
        VALID_TOKENS = {}
else:
    VALID_TOKENS = {
        "secure_token_123": {"id": "user_123", "name": "John Doe", "role": "admin"},
        "secure_token_456": {"id": "user_456", "name": "Jane Smith", "role": "user"}
    }

@auth.authenticate
async def get_current_user(authorization: str | None):
    """Check if user is valid"""
    if not authorization:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Missing authorization header")

    parts = authorization.split()
    if len(parts) != 2:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid authorization header format")

    scheme, token = parts
    if scheme.lower() != "bearer":
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid authentication scheme")
    
    # Check if the token is valid
    if token not in VALID_TOKENS:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid token")
    
    # Return user information if is valid
    user_data = VALID_TOKENS[token]

    return {
        "identity": user_data["id"],
        "role": [user_data["role"]],
    }


@auth.on
async def add_owner(
    ctx: Auth.types.AuthContext,
    value: dict, 
):
    """Make resources private for their creator"""
    # Add owner when creating a resource
    filters = {"owner": ctx.user["identity"]}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)

    # Only let users see their own resources
    return filters
