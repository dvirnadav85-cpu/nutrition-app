"""
Lightweight Supabase REST client using httpx directly.
This avoids the supabase-py library's pyiceberg dependency issue on Windows.
"""
import os
import httpx
import config

_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
_KEY = os.getenv("SUPABASE_KEY", "")

def _headers() -> dict:
    return {
        "apikey": _KEY,
        "Authorization": f"Bearer {_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def select(table: str, filters: dict | None = None, order: str | None = None,
           limit: int | None = None) -> list[dict]:
    """Fetch rows from a table. filters = {column: value}."""
    params = {"select": "*"}
    if order:
        params["order"] = order
    if limit:
        params["limit"] = str(limit)
    if filters:
        for col, val in filters.items():
            params[col] = f"eq.{val}"
    r = httpx.get(f"{_URL}/rest/v1/{table}", headers=_headers(), params=params)
    r.raise_for_status()
    return r.json()

def insert(table: str, data: dict) -> dict:
    """Insert a row and return the inserted record."""
    r = httpx.post(f"{_URL}/rest/v1/{table}", headers=_headers(), json=data)
    r.raise_for_status()
    result = r.json()
    return result[0] if isinstance(result, list) else result

def update(table: str, data: dict, filters: dict) -> list[dict]:
    """Update rows matching filters."""
    params = {}
    for col, val in filters.items():
        params[col] = f"eq.{val}"
    r = httpx.patch(f"{_URL}/rest/v1/{table}", headers=_headers(),
                    json=data, params=params)
    r.raise_for_status()
    return r.json()
