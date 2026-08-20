from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (register models on Base.metadata)
from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, portfolios, positions, prices, risk

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "Computes portfolio risk metrics -- historical & parametric Value at Risk, "
        "annualized volatility, maximum drawdown, and per-asset exposure -- over a "
        "user's position book, with JWT-authenticated, OpenAPI-documented endpoints."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(portfolios.router)
app.include_router(positions.router)
app.include_router(prices.router)
app.include_router(risk.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
