"""Authentication router."""

import hashlib
import logging
import secrets
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Response, Form, status
from fastapi.responses import RedirectResponse

from src.config import settings
from src.services import database, auth_service
from src.dependencies.auth import get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_safe_return_path(url: Optional[str]) -> str:
    """Validate and parse safe return path."""
    default = "/ui"
    if not url:
        return default

    try:
        parsed = urlparse(url)
        # Must not have scheme or netloc, must have path starting with exactly one slash
        if parsed.scheme or parsed.netloc:
            return default
        if not parsed.path.startswith("/"):
            return default
        if parsed.path.startswith("//"):
            return default
        # Return path and query
        safe_url = parsed.path
        if parsed.query:
            safe_url += f"?{parsed.query}"
        return safe_url
    except Exception:
        return default


def _hash_state(state: str) -> str:
    return hashlib.sha256(state.encode()).hexdigest()


@router.get("/login")
async def login(request: Request, return_to: Optional[str] = None):
    """Initiate MSAL auth code flow."""
    if not settings.ENTRA_ENABLED:
        # Mock login bypass
        request.session["user"] = {
            "tid": "00000000-0000-0000-0000-000000000000",
            "oid": "00000000-0000-0000-0000-000000000000",
            "name": "Local Dev User",
            "preferred_username": "dev@local",
        }
        return RedirectResponse(url=get_safe_return_path(return_to))

    state = secrets.token_urlsafe(32)
    state_hash = _hash_state(state)
    safe_return_to = get_safe_return_path(return_to)

    msal_client = auth_service.get_msal_client()
    flow = msal_client.initiate_auth_code_flow(
        scopes=[],
        redirect_uri=settings.ENTRA_REDIRECT_URI,
        state=state,
        response_mode="form_post",
    )

    await database.create_login_transaction(
        state_hash=state_hash,
        msal_flow=flow,
        return_to=safe_return_to,
        expires_in_seconds=settings.AUTH_LOGIN_TRANSACTION_TTL_SECONDS,
    )

    return RedirectResponse(url=flow["auth_uri"])


@router.get("/callback")
async def callback_get():
    """GET is not allowed for the form_post response mode."""
    return Response(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content="Method Not Allowed. Use POST.",
    )


@router.post("/callback")
async def callback_post(
    request: Request,
    state: str = Form(...),
    code: Optional[str] = Form(None),
    error: Optional[str] = Form(None),
    error_description: Optional[str] = Form(None),
):
    """Process MSAL auth code flow callback."""
    if not settings.ENTRA_ENABLED:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST, content="Entra is disabled"
        )

    # 1. State validation
    if not state or len(state) > 1024:
        logger.warning("Invalid state parameter size")
        return RedirectResponse(
            url="/login?error=auth_failed", status_code=status.HTTP_303_SEE_OTHER
        )

    state_hash = _hash_state(state)

    # 2. Fetch and consume transaction
    transaction = await database.consume_login_transaction(state_hash)
    if not transaction:
        logger.warning("Auth transaction not found or expired")
        return RedirectResponse(
            url="/login?error=session_expired", status_code=status.HTTP_303_SEE_OTHER
        )

    msal_flow, return_to = transaction

    # Handle Microsoft OAuth error
    if error:
        # Log the raw details securely
        logger.warning(f"OAuth error from Microsoft: {error}")
        if error == "access_denied":
            error_code = "access_denied"
        else:
            error_code = "auth_failed"
        return RedirectResponse(
            url=f"/login?error={error_code}", status_code=status.HTTP_303_SEE_OTHER
        )

    # Get form data dict
    form_data = dict(await request.form())

    # 3. MSAL Exchange
    msal_client = auth_service.get_msal_client()
    result = msal_client.acquire_token_by_auth_code_flow(
        auth_code_flow=msal_flow, auth_response=form_data
    )

    if "error" in result:
        logger.warning(
            f"MSAL acquire_token_by_auth_code_flow failed: {result.get('error')}"
        )
        return RedirectResponse(
            url="/login?error=auth_failed", status_code=status.HTTP_303_SEE_OTHER
        )

    # 4. Claim validation
    try:
        auth_service.validate_id_token_claims(result.get("id_token_claims", {}))
    except ValueError as e:
        logger.warning(f"Identity claim validation failed: {str(e)}")
        return RedirectResponse(
            url="/login?error=auth_failed", status_code=status.HTTP_303_SEE_OTHER
        )

    # 5. Set session
    claims = result["id_token_claims"]
    request.session["user"] = {
        "tid": claims["tid"],
        "oid": claims["oid"],
        "name": claims.get("name", "Unknown"),
        "preferred_username": claims.get("preferred_username", "Unknown"),
    }

    return RedirectResponse(url=return_to, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(request: Request):
    """Clear session and redirect to Microsoft logout."""
    user = await get_optional_user(request)
    if not user:
        return Response(
            status_code=status.HTTP_401_UNAUTHORIZED, content="Not authenticated"
        )

    request.session.clear()
    if not settings.ENTRA_ENABLED:
        return RedirectResponse(
            url="/auth/signed-out", status_code=status.HTTP_303_SEE_OTHER
        )

    # We must redirect to the end-session endpoint with the post-logout redirect URI
    # https://login.microsoftonline.com/{tenant}/oauth2/v2.0/logout?post_logout_redirect_uri=...
    # But because it's multitenant organizations, we can use the authority URL
    logout_url = f"{settings.ENTRA_AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={settings.ENTRA_POST_LOGOUT_REDIRECT_URI}"
    return RedirectResponse(url=logout_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/me")
async def get_me(request: Request, response: Response):
    """Return current user identity."""
    user = await get_optional_user(request)
    if not user:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return "Not authenticated"
    response.headers["Cache-Control"] = "no-store"
    return user


@router.get("/signed-out")
async def signed_out():
    """Signed out confirmation redirect."""
    response = RedirectResponse(
        url="/login?logged_out=1", status_code=status.HTTP_303_SEE_OTHER
    )
    response.headers["Cache-Control"] = "no-store"
    return response
