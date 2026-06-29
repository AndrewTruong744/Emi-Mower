# src/services/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth

# auto_error=True forces FastAPI to automatically reject requests missing an Authorization header
security_scheme = HTTPBearer(auto_error=True)

async def verify_gcp_identity(cred: HTTPAuthorizationCredentials = Depends(security_scheme)) -> dict:
    """
    FastAPI dependency that extracts the Bearer token, validates it against 
    GCP Identity Platform, and returns the decoded user profile claims.
    """
    token = cred.credentials
    try:
        # Perform offline cryptographical signature and expiration validation
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or tampered authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )