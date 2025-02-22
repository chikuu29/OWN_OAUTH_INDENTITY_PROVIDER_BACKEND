import jwt
import requests
from jwt import PyJWKClient

def verify_jwt(token):
    """Verify JWT using public key from JWKS endpoint."""

    jwks_url = "http://localhost:8000/.well-known/jwks.json"

    try:
        # Fetch JWK from the endpoint
        jwk_client = PyJWKClient(jwks_url)
        print(jwk_client)
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        print(jwk_client)
        print(signing_key.key)
        # Verify JWT
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"]
        )

        print("JWT is valid! Payload:", decoded)
        return decoded

    except jwt.ExpiredSignatureError:
        print("Token has expired.")
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")


# Example usage:
if __name__ == "__main__":
    # Use the JWT generated earlier
    jwt_token = "YOUR_GENERATED_JWT_HERE"
    jwt_token="eyJhbGciOiJSUzI1NiIsImtpZCI6Ik9BVVRIX1VOSVFVRV9LRVkiLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiJwYXlsb2FkLmdldCgnc3ViJykiLCJjbGllbnRfaWQiOiJjbGllbnRfaWQiLCJzY29wZSI6WyJvcGVuaWQiLCJwcm9maWxlIiwiZW1haWwiXSwiaWF0IjoxNzQwMjIyNDE1Ljk4MTAxOCwiZXhwIjoxNzUzMTgyNDE1Ljk4MTAxOCwidG9rZW5fdHlwZSI6ImFjY2Vzc190b2tlbiJ9.ORrRUvmxfBDyAWohCkEseh7MRq_r0IEaqRFKxaF1InC14JkFk-35kTtrzurwWPZLaypkwm9gTIQ-RQt3O82vFKBy-b2wVh3vjyMmrAHz0ldeLVW-TAhr6wrpNaKtInXrHfNx7NC--G7X8IB3YfUAetW3-z0p3T3BcEFEghejLN56gLhslQWe9I1MEsaUGA7OJuTvPiHUkUgGT64ZaduhEgFOhmfNrsUIz0pDqgOV-vD8kAcKvzgragRRVL1_KmntKp2zzsB5Y1yydbdJlPi-unIQc83NaWSL_VgGBEqXn5yhTGqJEAUX8aLhNzeKjHPxbyfUC-nUkCaioOoWDISR8Q"
    verify_jwt(jwt_token)
