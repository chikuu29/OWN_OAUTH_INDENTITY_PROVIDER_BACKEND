import json
from fastapi import HTTPException,status
import jwt
from datetime import datetime, timedelta
import secrets
import string
from passlib.context import CryptContext
import hashlib
import base64


from app.core.security.key_manager import get_active_private_key, get_jwks

# Token Expiration Time
# Token Expiration Times
ACCESS_TOKEN_EXPIRY = 3600  # 1 hour
REFRESH_TOKEN_EXPIRY = 86400 * 15  # 15 days
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
    expires_at = datetime.now() + timedelta(seconds=expires_in)

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
        tuple: A tuple containing the access token, refresh token, ID token, refresh token expiration, and ID token expiration.
    """
    private_key, kid = get_active_private_key()
    print("====PAYLOAD===", payload)

    # print("===PRIVATE_KEY===", private_key)
    # print("===kid===", kid)

    issued_at = datetime.now()
    access_exp = issued_at + timedelta(seconds=ACCESS_TOKEN_EXPIRY)
    refresh_exp = issued_at + timedelta(seconds=REFRESH_TOKEN_EXPIRY)
    id_token_exp = issued_at + timedelta(seconds=ID_TOKEN_EXPIRY)

    # Access Token
    access_token_payload = {
        "sub": payload.get("login_user", {}).get("username", 'UNKNOWN'),
        "tenant_name": payload.get("login_user", {}).get("tenant_name", None),
        "client_id": payload.get("client_id", "UNKNOWN"),
        "role": "admin",
        "permissions": [],
        "scope": [],
        "iat": issued_at.timestamp(),
        "exp": access_exp.timestamp(),
        "token_type": "access_token",
        **payload
    }
    access_token = jwt.encode(
        access_token_payload,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )

    # Refresh Token
    refresh_token = None
    if include_refresh:
        refresh_token_payload = {
            "sub": payload.get("login_user", {}).get("username", 'UNKNOWN'),
            "tenant_name": payload.get("login_user", {}).get("tenant_name", None),
            "client_id": payload.get("client_id", "UNKNOWN"),
            'role':'admin',
            "iat": issued_at.timestamp(),
            "exp": refresh_exp.timestamp(),
            "token_type": "refresh_token",
            **payload
        }
        refresh_token = jwt.encode(
            refresh_token_payload,
            private_key,
            algorithm="RS256",
            headers={"kid": kid},
        )

    # ID Token
    id_token = None
    if include_id_token:
        id_token_payload = {
            "sub": payload.get("login_user", {}).get("username", 'UNKNOWN'),
            "tenant_name": payload.get("login_user", {}).get("tenant_name", None),
            "client_id": payload.get("client_id", "UNKNOWN"),
            "iat": issued_at.timestamp(),
            "exp": id_token_exp.timestamp(),
            "token_type": "id_token",
            **payload
        }
        id_token = jwt.encode(
            id_token_payload, private_key, algorithm="RS256", headers={"kid": kid}
        )

    return access_token, refresh_token, id_token, refresh_exp, id_token_exp


def generate_kid(public_key):
    """Generate a unique key ID (kid) using SHA-256 hash of the public key modulus."""
    public_numbers = public_key.public_numbers()
    n_bytes = public_numbers.n.to_bytes(
        (public_numbers.n.bit_length() + 7) // 8, byteorder="big"
    )

    # Compute SHA-256 hash and base64url encode it
    kid_hash = hashlib.sha256(n_bytes).digest()
    kid = base64.urlsafe_b64encode(kid_hash).rstrip(b"=").decode("utf-8")
    return kid


async def validate_token(TOKEN: str):
    """
    Validate the given token.

    Args:
        TOKEN (str): The access token to validate.

    Returns:
        Dict: Decoded token payload if valid.

    Raises:
        HTTPException: If token validation fails.
    """
    if not TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="TOKEN is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Fetch JWKS
        jwks = get_jwks()
        jwks_keys = jwks.get("keys", [])

        # Decode JWT header to extract 'kid'
        decoded_header = jwt.get_unverified_header(TOKEN)
        kid = decoded_header.get("kid")
        print("====kid====", decoded_header)

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain 'kid' in the header.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Find the matching JWK
        matching_jwk = next((key for key in jwks_keys if key["kid"] == kid), None)

        if not matching_jwk:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No matching JWK found for the token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Convert JWK to PEM format
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(matching_jwk))

        # Verify and decode the JWT
        decoded_payload = jwt.decode(
            TOKEN,
            public_key,
            algorithms=["RS256"],
            options={"verify_exp": True},
            verify=True,  # Ensure expiration validation
        )

        return decoded_payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating token: {e}",
        )