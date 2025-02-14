
from datetime import timedelta, datetime
from typing import Optional
from passlib.context import CryptContext
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

# JWT Configurations
SECRET_KEY = "REFRESH_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
        print("Token has expired")
        return None  # Token expired
    except InvalidTokenError:
        print("Invalid token")
        return None  # Invalid token
