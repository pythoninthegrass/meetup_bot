from app.config import ALGORITHM, COOKIE_NAME, IS_DEV, SECRET_KEY, TOKEN_EXPIRE
from app.core.db import (
    Token,
    TokenData,
    User,
    UserInDB,
    authenticate_user,
    create_access_token,
    get_user,
    load_user,
    verify_password,
)
from datetime import UTC, datetime, timedelta
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.openapi.models import SecuritySchemeType
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security.base import SecurityBase
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Union

__all__ = [
    'Token',
    'TokenData',
    'User',
    'check_auth',
    'current_active_user_dependency',
    'current_user_dependency',
    'ip_whitelist_auth_dependency',
    'oauth_form_dependency',
    'OAuth2PasswordRequestForm',
]

# Authentication schemes
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    auto_error=False
)


class CookieOrHeaderToken(SecurityBase):
    def __init__(
        self,
        *,
        cookie_name: str = COOKIE_NAME,
        scheme_name: str | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ):
        self.cookie_name = cookie_name
        self.scheme_name = scheme_name or self.__class__.__name__
        self.description = description
        self.auto_error = auto_error
        self.model = {
            "type": SecuritySchemeType.http,
            "scheme": "bearer",
        }

    async def __call__(self, request: Request) -> str | None:
        # First try cookie
        cookie_token = request.cookies.get(self.cookie_name)
        if cookie_token:
            return cookie_token

        # Then try Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            return None

        return token


# Security schemes
security = CookieOrHeaderToken(auto_error=False)  # Don't auto-error so we can try form auth
oauth_form_dependency = Depends(OAuth2PasswordRequestForm)


class IPConfig(BaseModel):
    whitelist: list[str] = ["localhost", "127.0.0.1"]
    public_ips: list[str] = []  # TODO: add whitelisted public IPs here


ip_config = IPConfig()


def is_ip_allowed(request: Request):
    """Check if the client IP is in the whitelist"""
    client_host = request.client.host
    return client_host in ip_config.whitelist or client_host in ip_config.public_ips


async def get_current_user(
    request: Request,
    token: str | None = Depends(security),
    form_token: str | None = Depends(oauth2_scheme),
):
    """Get current user from session cookie, bearer token, or form authentication"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try cookie/header token first, then form token
    token_to_verify = token or form_token
    if not token_to_verify:
        raise credentials_exception

    try:
        payload = jwt.decode(token_to_verify, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as err:
        raise credentials_exception from err

    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Get current active user"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def ip_whitelist_or_auth(request: Request, current_user: User = Depends(get_current_active_user)):
    """Check if request is from whitelisted IP or authenticated user"""
    if is_ip_allowed(request):
        return {"bypass_auth": True}
    return current_user


def check_auth(auth: dict | User) -> None:
    """
    Shared function to check authentication result.
    Raises an HTTPException if authentication fails.
    """
    if isinstance(auth, dict) and auth.get("bypass_auth"):
        print("Authentication bypassed due to whitelisted IP")
    elif not isinstance(auth, User):
        raise HTTPException(status_code=401, detail="Unauthorized")


# Dependencies
current_user_dependency = Depends(get_current_user)
current_active_user_dependency = Depends(get_current_active_user)
ip_whitelist_auth_dependency = Depends(ip_whitelist_or_auth)
