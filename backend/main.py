from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict, deque
from time import monotonic
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine
from app.models import Base
from app.api.router import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DATABASE_URL.startswith("sqlite"):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    if settings.ENABLE_TELEGRAM_SCHEDULER:
        from app.bot.scheduler import start_scheduler
        start_scheduler()
    yield
    await engine.dispose()


app = FastAPI(title="Smart Finance", docs_url="/api/docs", redoc_url="/api/redoc", lifespan=lifespan)
app.include_router(api_router, prefix="/api")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


auth_attempts = defaultdict(deque)


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    if request.method == "POST" and request.url.path in {"/api/v1/auth/login", "/api/v1/auth/register"}:
        now = monotonic()
        host = request.client.host if request.client else "unknown"
        # Ограничиваем память и перебор. Для нескольких серверов нужен общий limiter на reverse proxy.
        for key in list(auth_attempts):
            if not auth_attempts[key] or now - auth_attempts[key][-1] > 60:
                del auth_attempts[key]
        attempts = auth_attempts[host]
        while attempts and now - attempts[0] > 60:
            attempts.popleft()
        if len(attempts) >= 30:
            return JSONResponse({"detail": "Слишком много попыток. Подождите минуту."}, status_code=429, headers={"Retry-After": "60"})
        attempts.append(now)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        same_origin = f"{request.url.scheme}://{request.url.netloc}"
        if origin and origin != same_origin and origin not in settings.CORS_ORIGINS:
            return JSONResponse({"detail": "Недопустимый источник запроса"}, status_code=403)
        if not origin and request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Недопустимый источник запроса"}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/api/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def api_not_found(path: str):
    return JSONResponse({"detail": "API endpoint not found"}, status_code=404)


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="web")
