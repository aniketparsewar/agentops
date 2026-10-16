"""X-API-Key auth with constant-time comparison. (From Project 6.)"""
import os
import secrets

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = os.environ.get("API_KEY", "")
_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_key(key: str | None = Depends(_header)) -> str:
    if not API_KEY or not key or not secrets.compare_digest(key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return key
