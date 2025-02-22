
import base64
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
from datetime import datetime, timedelta

# Paths to store RSA keys and JWT token
KEYS_DIR = "keys"  # Folder to store keys and token
os.makedirs(KEYS_DIR, exist_ok=True)

PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "rsa_private_key.pem")
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "rsa_public_key.pem")

def generate_rsa_keys():
    """Generate RSA private and public keys."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Serialize and save private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_pem)

    # Serialize and save public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(public_pem)

    print("RSA keys generated and saved.")


def load_rsa_keys():
    """Load RSA keys from files or generate them if not found."""
    if not os.path.exists(PRIVATE_KEY_PATH) or not os.path.exists(PUBLIC_KEY_PATH):
        generate_rsa_keys()

    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key_data = f.read()
        private_key = serialization.load_pem_private_key(
            private_key_data,
            password=None,
            backend=default_backend()
        )

    # Load public key
    with open(PUBLIC_KEY_PATH, "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read(), backend=default_backend())

    return private_key, public_key


def public_key_to_jwk():
    """Convert the RSA public key to JWK format."""
    _, public_key = load_rsa_keys()
    public_numbers = public_key.public_numbers()

    # Encode exponent 'e' and modulus 'n' in base64url without padding
    e_bytes = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, byteorder="big")
    n_bytes = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, byteorder="big")

    e = base64.urlsafe_b64encode(e_bytes).rstrip(b'=').decode('utf-8')
    n = base64.urlsafe_b64encode(n_bytes).rstrip(b'=').decode('utf-8')

    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "OAUTH_UNIQUE_KEY",  # Can be any unique string
        "n": n,
        "e": e
    }
    return jwk









