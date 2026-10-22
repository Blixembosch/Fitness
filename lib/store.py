"""Persistent state storage: local SQLite database (`data/fitness.db`) synchronized with GitHub `data`
branch (and optional GitHub Gist) for ATES FAM Fitness.

Why?
- Streamlit Community Cloud runs in ephemeral containers. Whenever new code is pushed to `main`,
  the container is rebuilt and local container storage is wiped.
- To prevent ANY data loss across deployments or container restarts (exactly like ATES FAM Budget),
  state is synchronized in SQL format (`fitness.sql` and `fitness.db`) on the dedicated `data` branch
  at `Blixembosch/fitness`.
- When the app starts up, `hydrate_session()` pulls the latest `fitness.sql` from the `data` branch
  if local SQLite is unpopulated, restoring the user's customized calories (2000 kcal), weights,
  workouts, and logs instantly.
"""
from __future__ import annotations
import base64
import datetime as dt
import json
import os
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path
import pandas as pd

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "fitness.db"
DEFAULT_SQL_PATH = Path(__file__).resolve().parent.parent / "data" / "fitness.sql"
GITHUB_REPO = "Blixembosch/fitness"
DATA_BRANCH = "data"

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


def dump_sql(db_path: Path) -> str:
    """Dump SQLite database to plain-text SQL script using standard library iterdump."""
    db_path = Path(db_path)
    if not db_path.exists():
        return ""
    con = sqlite3.connect(str(db_path))
    try:
        return "\n".join(con.iterdump())
    finally:
        con.close()


def restore_sql(sql_text: str, db_path: Path) -> bool:
    """Restore SQLite database from plain-text SQL script."""
    if not sql_text or not sql_text.strip():
        return False
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), timeout=5)
    try:
        con.executescript(sql_text)
        con.commit()
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        con.close()


def _gh_creds(secrets=None) -> tuple[str | None, str, str]:
    """Retrieve GitHub token, repo, and branch from Streamlit secrets or environment variables."""
    if secrets is None:
        try:
            import streamlit as st
            secrets = st.secrets
        except Exception:  # noqa: BLE001
            secrets = {}
    token = None
    repo = GITHUB_REPO
    branch = DATA_BRANCH
    try:
        token = (
            secrets.get("GITHUB_TOKEN")
            or secrets.get("GH_TOKEN")
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN")
        )
        repo = secrets.get("GITHUB_REPO") or GITHUB_REPO
        branch = secrets.get("DATA_BRANCH") or DATA_BRANCH
    except Exception:  # noqa: BLE001
        pass
    return (str(token) if token else None, str(repo), str(branch))


def pull_github_sql(repo: str = GITHUB_REPO, branch: str = DATA_BRANCH, token: str | None = None) -> str | None:
    """Pull the latest `fitness.sql` from the GitHub `data` branch."""
    # 1. Try public raw url (zero auth required for public repo)
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/fitness.sql"
    try:
        req = urllib.request.Request(
            raw_url,
            headers={"User-Agent": "ates-fam-fitness", "Cache-Control": "no-cache"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status == 200:
                data = r.read().decode("utf-8")
                if "CREATE TABLE" in data or "INSERT INTO" in data:
                    return data
    except Exception:  # noqa: BLE001
        pass

    # 2. Try GitHub Contents API (useful when private or behind auth)
    if token:
        api_url = f"https://api.github.com/repos/{repo}/contents/fitness.sql?ref={branch}"
        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "ates-fam-fitness",
                },
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                payload = json.load(r)
                content_b64 = payload.get("content", "")
                if content_b64:
                    return base64.b64decode(content_b64).decode("utf-8")
        except Exception:  # noqa: BLE001
            pass
    return None


def push_github_sql(sql_content: str, repo: str = GITHUB_REPO, branch: str = DATA_BRANCH, token: str | None = None) -> bool:
    """Push updated SQL dump to the GitHub `data` branch via GitHub API or git."""
    if not token:
        token, r_name, b_name = _gh_creds()
        repo = repo or r_name
        branch = branch or b_name

    if token:
        api_url = f"https://api.github.com/repos/{repo}/contents/fitness.sql"
        sha = None
        try:
            req_get = urllib.request.Request(
                f"{api_url}?ref={branch}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "ates-fam-fitness",
                },
            )
            with urllib.request.urlopen(req_get, timeout=5) as r:
                data = json.load(r)
                sha = data.get("sha")
        except Exception:  # noqa: BLE001
            sha = None

        payload = {
            "message": f"data: sync fitness.sql ({dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M')}) [skip ci]",
            "content": base64.b64encode(sql_content.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        try:
            req_put = urllib.request.Request(
                api_url,
                data=json.dumps(payload).encode("utf-8"),
                method="PUT",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                    "User-Agent": "ates-fam-fitness",
                },
            )
            with urllib.request.urlopen(req_put, timeout=7):
                return True
        except Exception:  # noqa: BLE001
            pass

    return False


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
    """Load persisted state dictionary from SQLite.
    If local SQLite is empty (e.g. freshly deployed container on Streamlit Cloud),
    automatically restore from GitHub `data` branch (`fitness.sql`).
    """
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

    # If local SQLite is empty or missing vital keys, pull SQL from GitHub data branch
    if not out or not out.get("body"):
        token, repo, branch = _gh_creds(secrets)
        remote_sql = pull_github_sql(repo=repo, branch=branch, token=token)
        if remote_sql:
            restored = restore_sql(remote_sql, path)
            if restored:
                try:
                    with _conn(path) as con:
                        rows = con.execute("SELECT key, value FROM kv").fetchall()
                    for k, v in rows:
                        try:
                            out[k] = json.loads(v)
                        except Exception:  # noqa: BLE001
                            pass
                except Exception:  # noqa: BLE001
                    pass

    # Optional fallback to Gist if configured and still empty
    if not out:
        t_gist, gist_id = _gist_creds(secrets)
        if t_gist and gist_id:
            remote = _pull_gist(t_gist, gist_id)
            if isinstance(remote, dict) and remote:
                out = remote
                save_raw(out, db_path=path, sync_cloud=False)
    return out


def save_raw(data: dict, db_path: Path | str | None = None, sync_cloud: bool = True, secrets=None) -> None:
    """Write a dictionary of key->json-serializable values into SQLite and sync SQL to GitHub `data` branch."""
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

    # Dump to local fitness.sql alongside fitness.db
    sql_dump = None
    try:
        sql_dump = dump_sql(path)
        sql_path = path.parent / "fitness.sql"
        sql_path.write_text(sql_dump, encoding="utf-8")
    except Exception:  # noqa: BLE001
        sql_dump = None

    if sync_cloud and sql_dump:
        token, repo, branch = _gh_creds(secrets)
        push_github_sql(sql_dump, repo=repo, branch=branch, token=token)

        # Also push to Gist if configured
        t_gist, gist_id = _gist_creds(secrets)
        if t_gist and gist_id:
            _push_gist(t_gist, gist_id, data)


def hydrate_session(session_state, db_path: Path | str | None = None, secrets=None) -> bool:
    """Hydrate `st.session_state` once per browser session from SQLite/GitHub data branch."""
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
    """Snapshot tracked keys from `st.session_state` into SQLite and GitHub `data` branch."""
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
    token, repo, branch = _gh_creds(secrets)
    if token:
        return {"mode": "github_data_branch", "label": f"SQLite + GitHub `{branch}` Branch ({repo}) ✓"}
    return {"mode": "github_data_public", "label": f"SQLite + GitHub `{branch}` Branch (Otomatik Bulut Senkronizasyonu)"}
