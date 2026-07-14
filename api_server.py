"""envguard SaaS — paid API layer.

Free core (envguard package) does local validation. This FastAPI app
gates the hosted features behind an API key:

  - /v1/validate   (open core: schema validation, no key needed)
  - /v1/scan       (paid: secret-leak scan)
  - /v1/drift      (paid: compare two env snapshots, store history)
  - /v1/checkout   (returns Lemon Squeezy checkout URL)
  - /webhooks/lemonsqueezy (payment webhook -> mints API key)

MVP uses SQLite for drift history to avoid the locked hermessvc
PostgreSQL. Swap to real PG later.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from envguard.core import parse_env, validate
from envguard.leaks import find_leaks
from envguard.diff import diff_envs
from billing import (
    create_checkout,
    verify_lemonsqueezy_signature,
    handle_webhook_event,
)

app = FastAPI(title="envguard API", version="0.1.0")

DB = Path(os.environ.get("ENVGUARD_DB", "envguard.db"))
KEYS = set(k for k in os.environ.get("ENVGUARD_KEYS", "").split(",") if k)

_conn = sqlite3.connect(str(DB), check_same_thread=False)
_conn.execute(
    "CREATE TABLE IF NOT EXISTS drift_history ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, api_key TEXT, project TEXT, "
    "snap_at TEXT, env_text TEXT)"
)
_conn.execute(
    "CREATE TABLE IF NOT EXISTS api_keys (api_key TEXT PRIMARY KEY, created_at TEXT)"
)
_conn.commit()


class ValidateReq(BaseModel):
    env: str
    schema_: dict = {}


class ScanReq(BaseModel):
    env: str


class DriftReq(BaseModel):
    project: str
    env: str


class CheckoutReq(BaseModel):
    redirect_url: str = ""


def _auth(x_api_key: str = Header(None)) -> str:
    if not x_api_key or x_api_key not in KEYS:
        # also accept keys minted via webhook
        row = _conn.execute(
            "SELECT api_key FROM api_keys WHERE api_key=?", (x_api_key,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="invalid or missing API key")
    return x_api_key


@app.post("/v1/validate")
def do_validate(req: ValidateReq):
    # open core: validation available without a key
    env = parse_env(req.env)
    res = validate(env, req.schema_)
    return {
        "ok": res.ok,
        "errors": [{"key": e.key, "message": e.message} for e in res.errors],
    }


@app.post("/v1/scan")
def do_scan(req: ScanReq, api_key: str = Depends(_auth)):
    env = parse_env(req.env)
    leaks = find_leaks(env)
    return {"leaks": [{"key": k, "pattern": p} for k, p in leaks]}


@app.post("/v1/drift")
def do_drift(req: DriftReq, api_key: str = Depends(_auth)):
    snap_at = datetime.now(timezone.utc).isoformat()
    _conn.execute(
        "INSERT INTO drift_history (api_key, project, snap_at, env_text) VALUES (?,?,?,?)",
        (api_key, req.project, snap_at, req.env),
    )
    _conn.commit()
    rows = _conn.execute(
        "SELECT env_text FROM drift_history WHERE api_key=? AND project=? "
        "ORDER BY id DESC LIMIT 2",
        (api_key, req.project),
    ).fetchall()
    if len(rows) < 2:
        return {"drift": None, "note": "first snapshot stored"}
    prev = parse_env(rows[1][0])
    cur = parse_env(rows[0][0])
    return {"drift": diff_envs(prev, cur)}


@app.post("/v1/checkout")
def do_checkout(req: CheckoutReq):
    """Return a Lemon Squeezy checkout URL for the paid plan."""
    res = create_checkout(req.redirect_url)
    if not res.get("ok"):
        raise HTTPException(status_code=502, detail=res.get("error", "billing error"))
    return {"checkout_url": res["checkout_url"]}


@app.post("/webhooks/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request):
    """Receive Lemon Squeezy webhook, verify signature, mint API key on paid event."""
    raw = await request.body()
    sig = request.headers.get("X-Signature")
    if not verify_lemonsqueezy_signature(raw, sig):
        raise HTTPException(status_code=400, detail="invalid signature")
    try:
        payload = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="bad json")
    event = payload.get("meta", {}).get("event_name", "")
    key = handle_webhook_event(event, payload.get("meta", {}))
    if key:
        _conn.execute(
            "INSERT OR IGNORE INTO api_keys VALUES (?, ?)",
            (key, datetime.now(timezone.utc).isoformat()),
        )
        _conn.commit()
        return {"ok": True, "api_key": key}
    return {"ok": True, "note": "event received, no key minted"}
