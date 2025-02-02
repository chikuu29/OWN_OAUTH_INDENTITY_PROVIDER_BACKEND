
# from typing import Union
from fastapi import FastAPI
from app.routers.client import router as OAuthClient_router
app=FastAPI()

@app.get("/")
def get_root():
    #how to return html content
    return  "🚀 Welcome to Oauth2.0 OpenID Connect Server 🚀"

app.include_router(OAuthClient_router)