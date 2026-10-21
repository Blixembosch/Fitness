"""Persistent state storage: local SQLite database (`data/fitness.db`) with optional GitHub Gist /
Apps Script cloud sync for Streamlit Community Cloud deployments.

Why both?
- Locally and within a running Streamlit container, SQLite (`data/fitness.db`) gives instant,
  zero-config persistence across page refreshes (F5), tab closes, and restarts.
- Because `Blixembosch/fitness` is a public GitHub repo, committing personal health data directly to
  the public repo is undesirable; if `GITHUB_TOKEN` + `GIST_ID` are set in `st.secrets`, state is
  additionally mirrored to a private GitHub Gist so container redeployments on Streamlit Cloud
  never lose state either.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import sqlite3
import urllib.request
from pathlib import Path
import pandas as pd

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "fitness.db"

PERSIST_KEYS = (
    "body",
    "wegovy",
    "weights",
    "workouts",
    "padel",
    "cron_ex",
    "active_kcal",
    "setlog",
    "loadlog",
)


def _db_path(custom_path: Path | str | None = None) -> Path:
    if custom_path:
        return Path(custom_path)
    env = os.environ.get("FITNESS_DB_PATH")
    return Path(env) if env else DEFAULT_DB_PATH


def _conn(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), timeout=5)
    con.execute(
        "CREATE TABLE IF NOT EXISTS kv ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT NOT NULL,"
        "  updated_at TEXT NOT NULL"
        ")"
    )
    return con


def _gist_creds(secrets=None) -> tuple[str | None, str | None]:
    if secrets is None:
        try:
            import streamlit as st
            secrets = st.secrets
        except Exception:  # noqa: BLE001
            return None, None
    try:
        token = secrets.get("GITHUB_TOKEN") or secrets.get("GH_TOKEN")
        gist_id = secrets.get("GIST_ID") or secrets.get("FITNESS_GIST_ID")
        return (str(token), str(gist_id)) if (token and gist_id) else (None, None)
    except Exception:  # noqa: BLE001
        return None, None


def _pull_gist(token: str, gist_id: str) -> dict | None:
    url = f"https://api.github.com/gists/{gist_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "ates-fam-fitness",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            payload = json.load(r)
        files = payload.get("files") or {}
        f = files.get("fitness_state.json") or next(iter(files.values()), None)
        if f and f.get("content"):
            return json.loads(f["content"])
    except Exception:  # noqa: BLE001
        return None
    return None


def _push_gist(token: str, gist_id: str, data: dict) -> bool:
    url = f"https://api.github.com/gists/{gist_id}"
    body = json.dumps({
        "files": {
            "fitness_state.json": {
                "content": json.dumps(data, ensure_ascii=False, indent=2)
            }
        }
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "ates-fam-fitness",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=6):
            return True
    except Exception:  # noqa: BLE001
        return False


def load_all(db_path: Path | str | None = None, secrets=None) -> dict:
    """Load persisted state dictionary from SQLite (and seed from Gist if local DB is empty)."""
    path = _db_path(db_path)
    out: dict = {}
    try:
        with _conn(path) as con:
            rows = con.execute("SELECT key, value FROM kv").fetchall()
        for k, v in rows:
            try:
                out[k] = json.loads(v)
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        out = {}

    if not out:
        token, gist_id = _gist_creds(secrets)
        if token and gist_id:
            remote = _pull_gist(token, gist_id)
            if isinstance(remote, dict) and remote:
                out = remote
                save_raw(out, db_path=path, sync_cloud=False)
    return out


def save_raw(data: dict, db_path: Path | str | None = None, sync_cloud: bool = True, secrets=None) -> None:
    """Write a dictionary of key->json-serializable values into SQLite (and optional Gist)."""
    path = _db_path(db_path)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        with _conn(path) as con:
            for k, v in data.items():
                con.execute(
                    "INSERT INTO kv (key, value, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (k, json.dumps(v, ensure_ascii=False), now),
                )
            con.commit()
    except Exception:  # noqa: BLE001
        pass

    if sync_cloud:
        token, gist_id = _gist_creds(secrets)
        if token and gist_id:
            _push_gist(token, gist_id, data)


def hydrate_session(session_state, db_path: Path | str | None = None, secrets=None) -> bool:
    """Hydrate `st.session_state` once per browser session from SQLite/cloud storage."""
    if session_state.get("_hydrated"):
        return False
    stored = load_all(db_path=db_path, secrets=secrets)
    if stored:
        if isinstance(stored.get("body"), dict):
            merged_body = dict(session_state.get("body", {}))
            merged_body.update(stored["body"])
            session_state["body"] = merged_body
        if isinstance(stored.get("wegovy"), dict):
            merged_weg = dict(session_state.get("wegovy", {}))
            merged_weg.update(stored["wegovy"])
            session_state["wegovy"] = merged_weg
        for k in ("weights", "workouts", "padel", "cron_ex", "active_kcal", "setlog", "loadlog"):
            if k in stored and stored[k] is not None:
                session_state[k] = stored[k]
        if "nutrition_rows" in stored and stored["nutrition_rows"]:
            session_state["nutrition"] = pd.DataFrame(stored["nutrition_rows"])
    session_state["_hydrated"] = True
    return bool(stored)


def persist_session(session_state, db_path: Path | str | None = None, secrets=None) -> None:
    """Snapshot tracked keys from `st.session_state` into SQLite (and optional cloud Gist)."""
    payload: dict = {}
    for k in PERSIST_KEYS:
        if k in session_state:
            payload[k] = session_state[k]
    ndf = session_state.get("nutrition")
    if isinstance(ndf, pd.DataFrame) and not ndf.empty:
        payload["nutrition_rows"] = ndf.to_dict("records")
    else:
        payload["nutrition_rows"] = []
    save_raw(payload, db_path=db_path, secrets=secrets)


def status_info(secrets=None) -> dict:
    """Return storage mode metadata for UI display."""
    token, gist_id = _gist_creds(secrets)
    if token and gist_id:
        return {"mode": "sqlite+gist", "label": "SQLite + GitHub Gist (Bulut Kalıcı)"}
    return {"mode": "sqlite", "label": "SQLite (Yerel Kalıcı DB · data/fitness.db)"}
