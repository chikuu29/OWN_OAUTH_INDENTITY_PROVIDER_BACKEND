
from datetime import timedelta, datetime
from typing import Optional
from fastapi import HTTPException
from passlib.context import CryptContext
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
import secrets
import string
# JWT Configurations
SECRET_KEY = "REFRESH_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
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
    auth_code = ''.join(secrets.choice(allowed_chars) for _ in range(length))
    
    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    return auth_code, expires_at



# Utility to verify password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# 🔹 Utility to create JWT tokens
def create_jwt_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Decode Token
def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])






def verify_token(token: str, secret_key: str):
    """
    Verify and decode a JWT token.

    :param token: The JWT token to verify
    :param secret_key: The secret key used to decode the token
    :return: The payload if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload  # Returns the decoded token data
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

