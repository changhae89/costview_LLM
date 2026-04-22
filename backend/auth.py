import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config import SUPABASE_URL, SUPABASE_ANON_KEY

_bearer = HTTPBearer()


def _get_user(token: str) -> dict:
    """Supabase Auth API로 토큰 검증 후 유저 정보 반환."""
    resp = httpx.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": SUPABASE_ANON_KEY,
        },
        timeout=5,
    )
    if resp.status_code == 401:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    if not resp.is_success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="auth_failed")
    return resp.json()


def require_auth(cred: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    return _get_user(cred.credentials)


def require_admin(user: dict = Depends(require_auth)) -> dict:
    role = (user.get("app_metadata") or {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    return user
