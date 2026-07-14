"""envguard SaaS — paid API layer.

Free core (envguard package) does local validation. This FastAPI app
gates the hosted features behind an API key:

  - /v1/validate   (open core: schema validation, no key needed)
  - /v1/scan       (paid: secret-leak scan)
  - /v1/drift      (paid: compare two env snapshots, store history)

MVP uses SQLite for drift history to avoid the locked hermessvc
PostgreSQL. Swap to real PG later.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from envguard.core import parse_env, validate
from envguard.leaks import find_leaks
from envguard.diff import diff_envs

app = FastAPI(title="envguard API", version="0.1.0")

DB = Path(os.environ.get("ENVGUARD_DB", "envguard.db"))
KEYS = set(k for k in os.environ.get("ENVGUARD_KEYS", "").split(",") if k)

_conn = sqlite3.connect(str(DB), check_same_thread=False)
_conn.execute(
    "CREATE TABLE IF NOT EXISTS drift_history ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, api_key TEXT, project TEXT, "
    "snap_at TEXT, env_text TEXT)"
)
_conn.commit()


class ValidateReq(BaseModel):
    env: str
    schema: dict = {}


class ScanReq(BaseModel):
    env: str


class DriftReq(BaseModel):
    project: str
    env: str


def _auth(x_api_key: str = Header(None)) -> str:
    if not x_api_key or x_api_key not in KEYS:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
    return x_api_key


@app.post("/v1/validate")
def do_validate(req: ValidateReq):
    # open core: validation available without a key
    env = parse_env(req.env)
    res = validate(env, req.schema)
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
