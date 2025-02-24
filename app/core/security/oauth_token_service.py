import jwt
from datetime import datetime, timedelta
import secrets
import string
from passlib.context import CryptContext


# Token Expiration Time
ACCESS_TOKEN_EXPIRY = 3600  # 1 hour
REFRESH_TOKEN_EXPIRY = 86400*15  # 24 hours
ID_TOKEN_EXPIRY = 3600  # 1 hour

from app.core.security.rsa_key_generator import load_rsa_keys

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_auth_code(length=32, expires_in=300):
    """
    Generate a secure authorization code with expiration.

    Args:
        length (int): Length of the authorization code.
        expires_in (int): Expiration time in seconds (default is 5 minutes).

    Returns:
        dict: Contains the authorization code and its expiration time.
    """
    # Generate the authorization code
    allowed_chars = string.ascii_letters + string.digits
    auth_code = "".join(secrets.choice(allowed_chars) for _ in range(length))

    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    return auth_code, expires_at


def generate_oauth_tokens(
    payload: dict, include_refresh: bool = True, include_id_token: bool = True
):
    """
    Generates OAuth tokens based on the given payload.

    Args:
        payload (dict): The payload containing user/client details.
        include_refresh (bool): If True, generates a refresh token.
        include_id_token (bool): If True, generates an ID token.

    Returns:
        dict: A dictionary containing the generated tokens.
    """
    private_key, public_key = load_rsa_keys()
    print("===PRIVATE_KEY===", private_key)

    issued_at = datetime.utcnow()
    access_exp = issued_at + timedelta(seconds=ACCESS_TOKEN_EXPIRY)
    refresh_exp = issued_at + timedelta(seconds=REFRESH_TOKEN_EXPIRY)
    id_token_exp = issued_at + timedelta(seconds=ID_TOKEN_EXPIRY)

    # Access Token
    access_token_payload = {
        "sub": "payload.get('sub')",
        "client_id": payload.get("client_id"),
        "scope": payload.get("scope"),
        "iat": issued_at.timestamp(),
        "exp": access_exp.timestamp(),
        "token_type": "access_token",
    }
    access_token = jwt.encode(
        access_token_payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "OAUTH_UNIQUE_KEY"},
    )

    # Refresh Token
    refresh_token = None
    if include_refresh:
        refresh_token_payload = {
            "sub": payload.get("sub"),
            "client_id": payload.get("client_id"),
            "iat": issued_at.timestamp(),
            "exp": refresh_exp.timestamp(),
            "token_type": "refresh_token",
        }
        refresh_token = jwt.encode(
            refresh_token_payload, private_key, algorithm="RS256"
        )

    # ID Token
    id_token = None
    if include_id_token:
        id_token_payload = {
            "sub": payload.get("sub"),
            "client_id": payload.get("client_id"),
            "iat": issued_at.timestamp(),
            "exp": id_token_exp.timestamp(),
            "token_type": "id_token",
        }
        id_token = jwt.encode(id_token_payload, private_key, algorithm="RS256")

    return access_token, refresh_token, id_token, refresh_exp.timestamp(), id_token_exp.timestamp()
