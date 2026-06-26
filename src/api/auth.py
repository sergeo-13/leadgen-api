"""Authentication router."""

import hashlib
import logging
import secrets
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Request, Response, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse

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
        expires_in_seconds=settings.AUTH_LOGIN_TRANSACTION_TTL_SECONDS
    )
    
    return RedirectResponse(url=flow["auth_uri"])


@router.get("/callback")
async def callback_get():
    """GET is not allowed for the form_post response mode."""
    return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, content="Method Not Allowed. Use POST.")


@router.post("/callback")
async def callback_post(request: Request, state: str = Form(...), code: Optional[str] = Form(None), error: Optional[str] = Form(None), error_description: Optional[str] = Form(None)):
    """Process MSAL auth code flow callback."""
    if not settings.ENTRA_ENABLED:
        return Response(status_code=status.HTTP_400_BAD_REQUEST, content="Entra is disabled")

    # 1. State validation
    if not state or len(state) > 1024:
        logger.warning("Invalid state parameter size")
        return HTMLResponse("<h1>Authentication Error</h1><p>Invalid state.</p>", status_code=400)

    state_hash = _hash_state(state)
    
    # 2. Fetch and consume transaction
    transaction = await database.consume_login_transaction(state_hash)
    if not transaction:
        logger.warning("Auth transaction not found or expired")
        return HTMLResponse("<h1>Authentication Error</h1><p>Login session expired or invalid. Please try again.</p>", status_code=400)
    
    msal_flow, return_to = transaction
    
    # Handle Microsoft OAuth error
    if error:
        logger.warning(f"OAuth error from Microsoft: {error} - {error_description}")
        if error == "access_denied":
            user_msg = "Authentication was cancelled or administrator approval is required. Please try again or contact your administrator."
        else:
            user_msg = "An error occurred during authentication. Please try again."
        return HTMLResponse(f"<h1>Authentication Error</h1><p>{user_msg}</p>", status_code=400)
        
    # Get form data dict
    form_data = dict(await request.form())
    
    # 3. MSAL Exchange
    msal_client = auth_service.get_msal_client()
    result = msal_client.acquire_token_by_auth_code_flow(
        auth_code_flow=msal_flow,
        auth_response=form_data
    )
    
    if "error" in result:
        logger.warning(f"MSAL acquire_token_by_auth_code_flow failed: {result.get('error')} - {result.get('error_description')}")
        return HTMLResponse("<h1>Authentication Error</h1><p>Failed to acquire token.</p>", status_code=400)
        
    # 4. Claim validation
    try:
        auth_service.validate_id_token_claims(result.get("id_token_claims", {}))
    except ValueError as e:
        logger.warning(f"Identity claim validation failed: {str(e)}")
        return HTMLResponse("<h1>Authentication Error</h1><p>Identity validation failed.</p>", status_code=403)
        
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
    request.session.clear()
    if not settings.ENTRA_ENABLED:
        return RedirectResponse(url="/auth/signed-out", status_code=status.HTTP_303_SEE_OTHER)
        
    # We must redirect to the end-session endpoint with the post-logout redirect URI
    # https://login.microsoftonline.com/{tenant}/oauth2/v2.0/logout?post_logout_redirect_uri=...
    # But because it's multitenant organizations, we can use the authority URL
    logout_url = f"{settings.ENTRA_AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={settings.ENTRA_POST_LOGOUT_REDIRECT_URI}"
    return RedirectResponse(
        url=logout_url,
        status_code=status.HTTP_303_SEE_OTHER
    )


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
    """Signed out confirmation page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Signed Out</title>
        <style>
            body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f5f5f5; margin: 0; }
            .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }
            a { color: #0066cc; text-decoration: none; margin-top: 1rem; display: inline-block; padding: 0.5rem 1rem; border: 1px solid #0066cc; border-radius: 4px; }
            a:hover { background-color: #f0f7ff; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Signed Out</h1>
            <p>You have been signed out. Sign in again.</p>
            <a href="/ui">Return to Login</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)
