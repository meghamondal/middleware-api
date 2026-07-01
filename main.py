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

        # Don't rate-limit CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        client = request.headers.get("X-Client-Id", "default")

        now = time.time()

        if client not in rate_store:
            rate_store[client] = []

        rate_store[client] = [
            t for t in rate_store[client]
            if now - t < WINDOW
        ]

        if len(rate_store[client]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )

        rate_store[client].append(now)

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