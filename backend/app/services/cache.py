import json
from datetime import date

import redis

from app.config import get_settings

settings = get_settings()


def risk_cache_key(portfolio_id: int, as_of_date: date, confidence: float, lookback_days: int) -> str:
    return f"risk:{portfolio_id}:{as_of_date.isoformat()}:{confidence}:{lookback_days}"


def get_cached_risk(client: redis.Redis, key: str) -> dict | None:
    raw = client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def set_cached_risk(client: redis.Redis, key: str, payload: dict, ttl_seconds: int | None = None) -> None:
    client.set(key, json.dumps(payload), ex=ttl_seconds or settings.risk_cache_ttl_seconds)
