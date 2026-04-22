import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config import SUPABASE_JWT_SECRET

_bearer = HTTPBearer()


def _decode(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")


def require_auth(cred: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    return _decode(cred.credentials)


def require_admin(claims: dict = Depends(require_auth)) -> dict:
    role = (claims.get("app_metadata") or {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    return claims
