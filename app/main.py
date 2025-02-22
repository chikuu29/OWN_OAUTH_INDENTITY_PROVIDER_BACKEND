# from typing import Union
import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.security.rsa_key_generator import public_key_to_jwk
from app.routers.client import router as OAuthClient_router
from app.routers.oauth import router as OAuth_router
from app.routers.accounts import router as AuthRegister_router
from app.routers.auth import router as AuthLogin_router
from app.core.response import ResponseHandler
from app.middlewares.loggerMiddleware import LoggerMiddleware
from typing import Union
from fastapi.middleware.cors import CORSMiddleware
from app.config import ENV

app = FastAPI()

# from dotenv import load_dotenv
# import os
# load_dotenv()
# print(f"DATABASE_URL",os.getenv('DATABASE_URL'))


origins = [
    "http://localhost:5173",  # React frontend
    "http://127.0.0.1:5173",
]
# ✅ Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow only specific frontend URLs
    allow_credentials=True,  # Allow cookies & authentication headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


@app.get("/")
def get_root():
    # how to return html content
    return "🚀 Welcome to Oauth2.0 OpenID Connect Server 🚀"


@app.get("/.well-known/jwks.json")
async def jwks():
    jwk = public_key_to_jwk()
    jwks = {"keys": [jwk]}
    return JSONResponse(content=jwks)


@app.get("/.well-known/openid-configuration")
async def openid_configuration():
    # DOMAIN = (
    #     "https://yourproductiondomain.com"
    #     if ENV == "production"
    #     else "http://localhost:8000"
    # )
    DOMAIN=os.getenv("DOMAIN_NAME")
    config = {
        "issuer": f"{DOMAIN}",
        "authorization_endpoint": f"{DOMAIN}/oauth/authorize",
        "token_endpoint": f"{DOMAIN}/api/auth/token",
        "userinfo_endpoint": f"{DOMAIN}/api/userinfo",
        "jwks_uri": f"{DOMAIN}/api/.well-known/jwks.json",
        "response_types_supported": ["code", "token", "id_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
    }
    return JSONResponse(content=config)


# Exception handling for FastAPI
@app.exception_handler(Union[RequestValidationError])
async def http_exception_handler(request: Request, exc: RequestValidationError):
    return ResponseHandler.handle_exception(request, exc)


# REGISTER MIDDLEWARES
app.add_middleware(LoggerMiddleware)

app.include_router(OAuth_router)
app.include_router(OAuthClient_router)
app.include_router(AuthRegister_router)
app.include_router(AuthLogin_router)
