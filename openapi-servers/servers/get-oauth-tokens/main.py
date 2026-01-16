from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="Token Extractor API",
    version="1.0.0",
    description="Extract oauth_id_token and oauth_access_token from cookies.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You may restrict this to certain domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/tokens",
    summary="Extract oauth tokens from cookies",
    description="Parse cookies and return oauth_id_token and oauth_access_token.",
)
async def get_oauth_tokens(request: Request):
    cookies = request.cookies
    print(cookies)

    headers = request.headers
    print(headers)

    oauth_id_token = cookies.get("oauth_id_token")
    oauth_access_token = None

    if headers.get("Authorization"):
        if token := headers.get("Authorization").split(" ")[1]:
            oauth_access_token = token

    if oauth_id_token is None and oauth_access_token is None:
        raise HTTPException(
            status_code=401,
            detail="Missing oauth_id_token cookie and oauth_access_token header",
        )

    return {
        "oauth_id_token": oauth_id_token,
        "oauth_access_token": oauth_access_token,
    }
