from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import uuid
import time

app = FastAPI()

# ===========================
# CHANGE THIS TO YOUR EMAIL
# ===========================

EMAIL = "23f1000744@ds.study.iitm.ac.in"

# ===========================
# CORS
# ===========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-j19z3r.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
    allow_credentials=False,
)

# ===========================
# Rate Limiter
# ===========================

RATE_LIMIT = 14
WINDOW = 10

rate_store = {}

# ===========================
# Request Context Middleware
# ===========================

class RequestContextMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response


app.add_middleware(RequestContextMiddleware)

# ===========================
# Rate Limit Middleware
# ===========================

class RateLimitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        # Never rate-limit CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        client = (
            request.headers.get("X-Client-Id")
            or request.headers.get("x-client-id")
            or "default"
            )
        now = time.time()

        bucket = rate_store.get(client)

        if bucket is None:
            bucket = {
                "start": now,
                "count": 0
            }
            rate_store[client] = bucket

        # Fixed 10-second window
        if now - bucket["start"] >= WINDOW:
            bucket["start"] = now
            bucket["count"] = 0

        # Limit reached
        if bucket["count"] >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )

        bucket["count"] += 1

        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

# ===========================
# Endpoint
# ===========================

from fastapi import Header

@app.get("/ping")
async def ping(
    request: Request,
    x_request_id: str | None = Header(None, alias="X-Request-ID")
):
    if x_request_id:
        request.state.request_id = x_request_id

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }

@app.get("/debug")
async def debug(request: Request):
    return {
        "headers": dict(request.headers),
        "rate_store": rate_store,
    }