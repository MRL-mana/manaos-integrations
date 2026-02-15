from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import aiohttp
import os

try:
    from manaos_integrations._paths import OPEN_WEBUI_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OPEN_WEBUI_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OPEN_WEBUI_PORT = int(os.getenv("OPEN_WEBUI_PORT", "8080"))

OPEN_WEBUI_BASE_URL = os.getenv(
    "OPEN_WEBUI_BASE_URL",
    f"http://127.0.0.1:{OPEN_WEBUI_PORT}",
)

app = FastAPI(
    title="User Info Proxy API",
    version="1.0.0",
    description="Fetch user details from the internal authentication server.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You may restrict this to certain domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/get_session_user_info",
    summary="Forward auth token and retrieve session user details",
    description="Get user info from internal auth service using Authorization Bearer token.",
)
async def get_session_user_info(request: Request):
    auth_header = request.headers.get("Authorization")

    print(f"Received Authorization header: {auth_header}")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{OPEN_WEBUI_BASE_URL}/api/v1/auths/",
                headers={"Authorization": auth_header},
                timeout=aiohttp.ClientTimeout(total=10.0),
            ) as resp:

                if resp.status != 200:
                    raise HTTPException(
                        status_code=resp.status, detail="Failed to retrieve user info"
                    )

                data = await resp.json()

                return {
                    "id": data.get("id"),
                    "role": data.get("role"),
                    "name": data.get("name"),
                    "email": data.get("email"),
                }

    except aiohttp.ClientError as exc:
        raise HTTPException(
            status_code=502, detail=f"Error connecting to auth service: {exc}"
        )
