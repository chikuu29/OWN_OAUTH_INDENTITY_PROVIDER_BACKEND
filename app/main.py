
# from typing import Union
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from app.routers.client import router as OAuthClient_router
from app.core.response import ResponseHandler
from typing import Union

app=FastAPI()

@app.get("/")
def get_root():
    #how to return html content
    return  "🚀 Welcome to Oauth2.0 OpenID Connect Server 🚀"



# Exception handling for FastAPI
@app.exception_handler(Union[RequestValidationError])
async def http_exception_handler(request: Request, exc:RequestValidationError):
    return ResponseHandler.handle_exception(request, exc)




app.include_router(OAuthClient_router)