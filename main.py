from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import uuid
import time
import asyncio

app = FastAPI()

EMAIL = "23f1000744@ds.study.iitm.ac.in"

# ==================================================
# CORS
# ==================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-j19z3r.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# ==================================================
# Request ID Middleware
# ==================================================

class RequestIDMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response


app.add_middleware(RequestIDMiddleware)

# ==================================================
# Rate Limiter
# ==================================================

RATE_LIMIT = 14
WINDOW = 10

rate_store = {}
rate_lock = asyncio.Lock()


async def check_rate_limit(client_id: str):

    now = time.time()

    async with rate_lock:

        bucket = rate_store.get(client_id)

        if bucket is None:
            bucket = {
                "start": now,
                "count": 0
            }
            rate_store[client_id] = bucket

        # reset after WINDOW seconds
        if now - bucket["start"] >= WINDOW:
            bucket["start"] = now
            bucket["count"] = 0

        if bucket["count"] >= RATE_LIMIT:
            return False

        bucket["count"] += 1

        return True


# ==================================================
# Endpoint
# ==================================================

@app.options("/ping")
async def options_ping():
    return JSONResponse(content={})


@app.get("/ping")
async def ping(request: Request):

    client_id = (
        request.headers.get("X-Client-Id")
        or request.headers.get("x-client-id")
        or "default"
    )

    allowed = await check_rate_limit(client_id)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded"
            }
        )

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }