from fastapi import FastAPI

app=FastAPI()

@app.get("/")
def get_root():
    #how to return html content
    return  "🚀 Welcome to Oauth2.0 OpenID Connect Server 🚀"