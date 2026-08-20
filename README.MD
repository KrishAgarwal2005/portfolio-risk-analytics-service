
Portfolio Risk API

[![CI](https://github.com/KrishAgarwal2005/portfolio-risk-analytics-service/actions/workflows/ci.yml/badge.svg)](https://github.com/KrishAgarwal2005/portfolio-risk-analytics-service/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A REST service that computes portfolio risk over a position book: historical
and parametric Value at Risk, maximum drawdown, annualized volatility, and
per-asset exposure. JWT-authenticated, OpenAPI-documented, backed by
PostgreSQL and Redis, containerized with Docker Compose.

## Features

- **Risk engine** — historical-simulation VaR, parametric (variance-covariance)
  VaR, annualized volatility, maximum drawdown, and per-asset exposure, as pure
  NumPy/pandas functions decoupled from the database.
- **JWT auth** — register/login with bcrypt-hashed passwords, OAuth2 password
  flow, portfolios scoped to their owner.
- **PostgreSQL** — positions and daily price history, with a composite
  `(symbol, price_date)` index backing the lookback-window range queries the
  risk engine issues.
- **Redis caching** — computed risk metrics are cached per
  `(portfolio, as_of_date, confidence, lookback_days)` with a TTL, so repeat
  requests for an already-computed day skip both the Postgres scan and the
  NumPy computation.
- **OpenAPI docs** — interactive docs at `/docs` (Swagger UI) and `/redoc`.
- **Tested** — the risk engine is validated against an independent NumPy
  reference implementation under pytest, including edge cases (sparse price
  history, single-asset books, no data at all); API-level tests cover auth,
  ownership isolation, and cache hit/miss behavior.
- **Dockerized** — `docker compose up` brings up Postgres, Redis, and the API
  together; migrations run automatically on container start.

## Architecture

```
Client
  │  JWT bearer token
  ▼
FastAPI (routers: auth / portfolios / positions / prices / risk)
  │                                   │
  ▼                                   ▼
PostgreSQL                          Redis
 users, portfolios,          risk:{portfolio_id}:{as_of_date}:
 positions,                  {confidence}:{lookback_days}
 price_history                → cached RiskMetrics JSON, TTL
 (indexed on
  symbol, price_date)
  │
  ▼
risk_engine.py (pure NumPy/pandas — no DB/Redis imports; unit tested
                 against a hand-rolled reference implementation)
```

`GET /portfolios/{id}/risk` is the core endpoint: on a cache miss it pulls the
position book, fetches the lookback window of prices with a single indexed
range query per symbol, computes the metrics, caches the result, and returns
it. On a cache hit it returns straight from Redis.

## Tech stack

FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL · Redis · NumPy/pandas/SciPy ·
python-jose (JWT) · bcrypt · pytest · Docker Compose

## Quickstart (Docker Compose)

```bash
git clone https://github.com/KrishAgarwal2005/portfolio-risk-analytics-service.git
cd portfolio-risk-analytics-service
docker compose up --build
```

The API is now at `http://localhost:8000`, docs at `http://localhost:8000/docs`.

Seed it with a demo user, synthetic price history, and a sample portfolio:

```bash
cd backend
pip install httpx numpy  # if running the script outside the container
python scripts/seed_demo_data.py --base-url http://localhost:8000
```

This prints a login (`demo@tradesense.dev` / `demo-pass-1234`), loads ~400
days of synthetic daily prices for four symbols, opens a sample portfolio, and
prints its risk snapshot.

Measure the cache's effect on latency:

```bash
python scripts/benchmark_cache.py --base-url http://localhost:8000
```

## Local development (without Docker)

```bash
cd backend
python -m venv ../venv && ../venv/Scripts/activate  # or source ../venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env   # point at a local/hosted Postgres + Redis, or run only `docker compose up db redis`
alembic upgrade head
uvicorn app.main:app --reload
```

Run the test suite (no external services required — SQLite in-memory + fakeredis):

```bash
pytest -q
```

## API overview

| Endpoint                                   | Description                              |
| ------------------------------------------- | ----------------------------------------- |
| `POST /auth/register`                       | Create an account                         |
| `POST /auth/login`                           | OAuth2 password flow → JWT access token   |
| `POST /portfolios`                           | Create a portfolio                        |
| `GET /portfolios`                            | List your portfolios                      |
| `GET /portfolios/{id}`                       | Portfolio detail with positions           |
| `POST /portfolios/{id}/positions`            | Add a position                            |
| `PATCH /portfolios/{id}/positions/{pos_id}`  | Update quantity / cost basis              |
| `POST /prices`                               | Bulk load/refresh daily close prices      |
| `GET /portfolios/{id}/risk`                  | Historical & parametric VaR, volatility, max drawdown, per-asset exposure |

Full request/response schemas are in the generated OpenAPI docs at `/docs`.

## Risk methodology

- **Historical VaR** — historical simulation: apply each day's realized asset
  returns to the *current* position weights to build a simulated P&L
  distribution, then take the empirical quantile at `1 - confidence`.
- **Parametric VaR** — variance-covariance (delta-normal) method:
  `VaR = z(confidence) * sqrt(wᵀ Σ w) - wᵀ μ`, using the sample covariance
  matrix and mean of asset returns over the lookback window.
- **Volatility** — sample standard deviation of portfolio returns, annualized
  by `sqrt(252)`.
- **Max drawdown** — largest peak-to-trough decline of the cumulative
  portfolio return series over the window.
- **Exposure** — market value and weight of each position, priced at the
  latest close on or before `as_of_date`.

All of it lives in [`backend/app/services/risk_engine.py`](backend/app/services/risk_engine.py)
as pure functions with no database or cache dependency, which is what makes it
possible to test against a from-scratch NumPy reference implementation
(see [`backend/tests/test_risk_engine.py`](backend/tests/test_risk_engine.py)).

## Deploying

A [`render.yaml`](render.yaml) blueprint is included for a one-click deploy on
[Render](https://render.com): it provisions a free Postgres database, a free
Redis instance, and the API as a Docker web service, wired together with
environment variables (Render → New → Blueprint → point at this repo).

## License

MIT — see [LICENSE](LICENSE).
