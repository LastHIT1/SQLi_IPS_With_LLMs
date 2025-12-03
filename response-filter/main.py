import re
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from redis.asyncio import ConnectionPool, Redis

SQL_ERROR_FILTER_KEY: Final[str] = "sql_error_filter_status"

SQL_ERROR_PATTERNS: Final[list[str]] = [
    # PostgreSQL
    r"ProgrammingError",
    r"psycopg2\.errors\.",
    r"syntax error at or near",
    r"relation .* does not exist",
    r"column .* does not exist",
    r"unterminated quoted string",
    r"invalid input syntax",
    # MySQL
    r"MySQLdb\.OperationalError",
    r"You have an error in your SQL syntax",
    r"Unknown column",
    r"Table .* doesn't exist",
    # SQLite
    r"sqlite3\.OperationalError",
    r'near ".*": syntax error',
    r"no such table",
    r"no such column",
    # Generic SQL/Django
    r"DataError",
    r"IntegrityError",
    r"OperationalError",
    r"DatabaseError",
    r"ProgrammingError at",
    r"Exception Value:",
    r"Exception Type:",
]

SQL_ERROR_REGEX: Final[re.Pattern] = re.compile(
    "|".join(SQL_ERROR_PATTERNS), re.IGNORECASE
)

ALLOWED_RESPONSE: Final[Response] = Response(
    content=b'{"allowed":true}',
    media_type="application/json",
)

ERROR_PAGE: Final[str] = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error | FIU BookStore</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root{--fiu-blue:#081E3F;--fiu-gold:#B6862C;--warning:#fd7e14}
        body{background:#f5f5f5;min-height:100vh;display:flex;flex-direction:column}
        .navbar-fiu{background:var(--fiu-blue)!important}
        .card-warning{background:linear-gradient(135deg,var(--warning),#e65c00);color:#fff;padding:2rem;text-align:center}
        .info-box{background:#fff3cd;border-left:4px solid var(--warning);padding:1rem;margin-bottom:1rem;border-radius:0 8px 8px 0}
        .btn-gold{background:var(--fiu-gold);border-color:var(--fiu-gold);color:#fff}
        .btn-gold:hover{background:#C9A227;color:#fff}
        .footer-fiu{background:var(--fiu-blue);color:#fff;padding:1rem;text-align:center;margin-top:auto}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark navbar-fiu">
        <div class="container-fluid">
            <a class="navbar-brand fw-bold" href="/">FIU BookStore</a>
        </div>
    </nav>
    <div class="container py-5 flex-grow-1">
        <div class="card shadow mx-auto" style="max-width:550px">
            <div class="card-warning">
                <div style="font-size:3.5rem">⚠️</div>
                <h2 class="mt-2">Request Error</h2>
                <p class="mb-0">We couldn't process your request</p>
            </div>
            <div class="card-body p-4">
                <div class="info-box">
                    <strong>What happened?</strong>
                    <p class="mb-0 mt-2">Your request contained characters or patterns that could not be processed safely.</p>
                </div>
                <div class="info-box">
                    <strong>What can you do?</strong>
                    <ul class="mb-0 mt-2">
                        <li>Try a simpler search term</li>
                        <li>Avoid using special characters like quotes or semicolons</li>
                        <li>Return to the homepage and try again</li>
                    </ul>
                </div>
                <div class="text-center mt-4">
                    <a href="/" class="btn btn-gold btn-lg">Return to BookStore</a>
                </div>
            </div>
        </div>
    </div>
    <footer class="footer-fiu"><small>FIU BookStore - Florida International University</small></footer>
</body>
</html>"""

redis_pool: ConnectionPool | None = None
redis_client: Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_pool, redis_client

    redis_pool = ConnectionPool(host="cache", port=6379, db=0, decode_responses=True)
    redis_client = Redis(connection_pool=redis_pool)

    yield

    await redis_client.aclose()
    await redis_pool.disconnect()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


async def get_filter_status() -> bool:
    value = await redis_client.get(SQL_ERROR_FILTER_KEY)
    if value is None:
        await redis_client.set(SQL_ERROR_FILTER_KEY, "1")
        return True
    return value == "1"


def contains_sql_error(content: str) -> bool:
    return bool(SQL_ERROR_REGEX.search(content))


@app.post("/", response_model=None)
async def check_response(request: Request) -> Response:
    if not await get_filter_status():
        return ALLOWED_RESPONSE

    body = await request.body()
    content = body.decode("utf-8", errors="replace") if body else ""

    content_type = request.headers.get("X-Original-Content-Type", "")
    if "text/html" not in content_type:
        return ALLOWED_RESPONSE

    if not contains_sql_error(content):
        return ALLOWED_RESPONSE

    return HTMLResponse(content=ERROR_PAGE, status_code=200)


@app.get("/status")
async def status() -> dict[str, bool]:
    return {"active": await get_filter_status()}


@app.get("/activate")
async def activate() -> dict[str, str]:
    await redis_client.set(SQL_ERROR_FILTER_KEY, "1")
    return {"status": "activated"}


@app.get("/deactivate")
async def deactivate() -> dict[str, str]:
    await redis_client.set(SQL_ERROR_FILTER_KEY, "0")
    return {"status": "deactivated"}
