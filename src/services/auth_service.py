"""Authentication service handling MSAL flows and claims validation."""

import time
import uuid
import logging
from typing import Dict, Any

import msal

from src.config import settings

logger = logging.getLogger(__name__)


def get_msal_client() -> msal.ConfidentialClientApplication:
    """
    Get an ephemeral MSAL ConfidentialClientApplication instance.
    Does not use a persistent token cache to ensure zero token persistence.
    """
    return msal.ConfidentialClientApplication(
        client_id=settings.ENTRA_CLIENT_ID,
        client_credential=settings.ENTRA_CLIENT_SECRET,
        authority=settings.ENTRA_AUTHORITY,
        # Intentionally omitting token_cache to prevent any persistence
    )


def validate_id_token_claims(claims: Dict[str, Any]) -> None:
    """
    Validate ID token claims returned by MSAL according to the approved trust model.

    Raises:
        ValueError: If any claim validation fails.
    """
    if not claims:
        raise ValueError("No claims provided")

    # 1. tid exists and is a valid UUID
    tid = claims.get("tid")
    if not tid:
        raise ValueError("Missing 'tid' claim")
    try:
        uuid.UUID(tid)
    except ValueError:
        raise ValueError("Invalid 'tid' claim format")

    # 2. oid exists and is non-empty
    oid = claims.get("oid")
    if not oid or not str(oid).strip():
        raise ValueError("Missing or empty 'oid' claim")

    # 3. ver == "2.0"
    ver = claims.get("ver")
    if ver != "2.0":
        raise ValueError(f"Invalid 'ver' claim: expected '2.0', got '{ver}'")

    # 4. iss == https://login.microsoftonline.com/{tid}/v2.0
    iss = claims.get("iss")
    expected_iss = f"https://login.microsoftonline.com/{tid}/v2.0"
    if iss != expected_iss:
        raise ValueError(f"Invalid 'iss' claim: expected '{expected_iss}', got '{iss}'")

    # 5. aud == ENTRA_CLIENT_ID
    aud = claims.get("aud")
    if aud != settings.ENTRA_CLIENT_ID:
        raise ValueError(f"Invalid 'aud' claim: expected '{settings.ENTRA_CLIENT_ID}', got '{aud}'")

    current_time = time.time()
    clock_skew = settings.AUTH_TOKEN_CLOCK_SKEW_SECONDS

    # 6. exp exists and current_time <= exp + clock_skew
    exp = claims.get("exp")
    if exp is None:
        raise ValueError("Missing 'exp' claim")
    if not isinstance(exp, (int, float)):
        raise ValueError("Invalid 'exp' claim format")
    if current_time > exp + clock_skew:
        raise ValueError("Token is expired")

    # 7. nbf (if present): current_time + clock_skew >= nbf
    nbf = claims.get("nbf")
    if nbf is not None:
        if not isinstance(nbf, (int, float)):
            raise ValueError("Invalid 'nbf' claim format")
        if current_time + clock_skew < nbf:
            raise ValueError("Token is not yet valid")

    # 8. iat (if present): iat <= current_time + clock_skew
    iat = claims.get("iat")
    if iat is not None:
        if not isinstance(iat, (int, float)):
            raise ValueError("Invalid 'iat' claim format")
        if iat > current_time + clock_skew:
            raise ValueError("Token issued in the future")

    logger.debug(f"Claims validation successful for oid {oid} in tid {tid}")
