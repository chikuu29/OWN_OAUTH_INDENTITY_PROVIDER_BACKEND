

import os
import json
import base64
import hashlib
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

KEYS_DIR = "keys"  # Directory for storing private keys
print("OS PATH",os.path)
os.makedirs(KEYS_DIR, exist_ok=True)
# Store keys persistently
KEYS_FILE = os.path.join(KEYS_DIR, "keys.json") 

def generate_rsa_key():
    """Generate a new RSA key pair."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def rotate_key():
    """Rotate the signing key while keeping old keys for validation."""
    keys = load_keys()

    # Generate new key pair
    private_key, public_key = generate_rsa_key()
    new_kid = generate_kid(public_key)

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    # Add new private key to storage
    keys["keys"][new_kid] = {"private_key": private_pem, "created_at": str(datetime.utcnow())}

    # Set new key as active
    keys["active_kid"] = new_kid
    save_keys(keys)

    print(f"🔄 New key rotated! Active `kid`: {new_kid}")

def save_keys(keys):
    """Save keys to a JSON file."""
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f)

def generate_kid(public_key):
    """Generate a unique `kid` as a SHA-256 hash of the modulus."""
    public_numbers = public_key.public_numbers()
    n_bytes = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, byteorder="big")
    kid_hash = hashlib.sha256(n_bytes).digest()
    return base64.urlsafe_b64encode(kid_hash).rstrip(b'=').decode('utf-8')



def load_keys():
    """Load existing keys or generate new ones if not found."""
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return json.load(f)

    # Generate initial key if no keys exist
    private_key, public_key = generate_rsa_key()
    kid = generate_kid(public_key)

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    keys = {
        "active_kid": kid,
        "keys": {kid: {"private_key": private_pem, "created_at": str(datetime.now())}}
    }
    save_keys(keys)
    return keys

def get_active_private_key():
    """Retrieve the active private key for signing tokens."""
    keys = load_keys()
    active_kid = keys["active_kid"]
    private_pem = keys["keys"][active_kid]["private_key"]

    return serialization.load_pem_private_key(private_pem.encode(), password=None), active_kid





def get_jwks():
    """Generate JWKS JSON response."""
    keys = load_keys()
    jwks = {"keys": []}

    for kid, key_data in keys["keys"].items():
        private_key = serialization.load_pem_private_key(key_data["private_key"].encode(), password=None)
        public_key = private_key.public_key()
        public_numbers = public_key.public_numbers()

        # Convert to Base64 URL encoding
        e = base64.urlsafe_b64encode(public_numbers.e.to_bytes(3, byteorder="big")).decode().rstrip("=")
        n = base64.urlsafe_b64encode(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, byteorder="big")).decode().rstrip("=")

        jwks["keys"].append({
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": kid,
            "n": n,
            "e": e
        })

    return jwks

