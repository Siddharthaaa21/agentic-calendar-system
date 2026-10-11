import json
import logging
import os
import secrets
import time
from typing import Any, Dict, Optional

from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pending OAuth transactions: state -> {session_id, redirect_uri, code_verifier, timestamp}
_pending_oauth: Dict[str, Dict[str, Any]] = {}
_pending_by_session: Dict[str, str] = {}  # session_id -> state


def _find_credentials_file() -> Optional[str]:
    """Find a credentials.json file on disk."""
    env_path = os.getenv("GOOGLE_CREDENTIALS_FILE")
    if env_path and os.path.exists(env_path):
        return env_path

    candidates = [
        os.path.abspath(os.path.join(_BASE_DIR, "..", "..", "credentials.json")),  # backend/credentials.json
        os.path.abspath(os.path.join(_BASE_DIR, "..", "..", "..", "credentials.json")),  # root credentials.json
        os.path.abspath("backend/credentials.json"),
        os.path.abspath("credentials.json"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 0:
            return c
    return None


def get_google_client_config() -> Optional[Dict[str, Any]]:
    """Resolve Google OAuth client ID and Secret from environment, secrets, or file."""
    # 1. Environment variables
    cid = os.getenv("GOOGLE_CLIENT_ID")
    csecret = os.getenv("GOOGLE_CLIENT_SECRET")
    if cid and csecret:
        return {
            "client_id": cid.strip(),
            "client_secret": csecret.strip(),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

    # 2. Streamlit secrets (if available in process)
    try:
        import streamlit as st
        if "GOOGLE_CLIENT_ID" in st.secrets and "GOOGLE_CLIENT_SECRET" in st.secrets:
            return {
                "client_id": str(st.secrets["GOOGLE_CLIENT_ID"]).strip(),
                "client_secret": str(st.secrets["GOOGLE_CLIENT_SECRET"]).strip(),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
    except Exception:
        pass

    # 3. File on disk (credentials.json)
    creds_file = _find_credentials_file()
    if creds_file:
        try:
            with open(creds_file, "r") as f:
                data = json.load(f)
            client_dict = data.get("web") or data.get("installed")
            if client_dict and client_dict.get("client_id") and client_dict.get("client_secret"):
                return {
                    "client_id": client_dict["client_id"],
                    "client_secret": client_dict["client_secret"],
                    "auth_uri": client_dict.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                    "token_uri": client_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
                    "redirect_uris": client_dict.get("redirect_uris", []),
                }
        except Exception as e:
            logger.warning("Failed parsing credentials file %s: %s", creds_file, e)

    return None


def _clean_old_oauth_states() -> None:
    now = time.time()
    expired = [s for s, data in _pending_oauth.items() if now - data.get("created_at", 0) > 3600]
    for s in expired:
        _pending_oauth.pop(s, None)


def create_authorization_url(redirect_uri: str, session_id: str = "default") -> Dict[str, Any]:
    """Generate a one-click Google OAuth URL for a visitor's browser session."""
    client_config = get_google_client_config()
    if not client_config:
        raise ValueError("Google OAuth credentials are not configured. Please supply credentials.json or GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET.")

    _clean_old_oauth_states()

    web_config = {
        "web": {
            "client_id": client_config["client_id"],
            "client_secret": client_config["client_secret"],
            "auth_uri": client_config.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": client_config.get("token_uri", "https://oauth2.googleapis.com/token"),
            "redirect_uris": [redirect_uri],
        }
    }

    # State includes session_id prefix for easy tracking
    random_part = secrets.token_urlsafe(16)
    state = f"{session_id}__{random_part}"

    flow = Flow.from_client_config(
        web_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )

    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true",
        state=state,
    )

    # Save PKCE verifier and redirect_uri for later exchange
    code_verifier = getattr(flow, "code_verifier", None)
    _pending_oauth[state] = {
        "session_id": session_id,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        "created_at": time.time(),
    }
    _pending_by_session[session_id] = state

    return {
        "auth_url": auth_url,
        "state": state,
        "client_id": client_config["client_id"],
    }


def exchange_authorization_code(
    code: str,
    redirect_uri: str,
    session_id: str = "default",
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """Exchange OAuth authorization code for Google credentials and access tokens."""
    client_config = get_google_client_config()
    if not client_config:
        raise ValueError("Google OAuth credentials are not configured.")

    # Locate pending state data
    entry = None
    if state and state in _pending_oauth:
        entry = _pending_oauth.pop(state, None)
    elif session_id in _pending_by_session:
        saved_state = _pending_by_session.pop(session_id, None)
        if saved_state:
            entry = _pending_oauth.pop(saved_state, None)

    code_verifier = entry.get("code_verifier") if entry else None
    effective_redirect_uri = entry.get("redirect_uri") if entry and entry.get("redirect_uri") else redirect_uri

    web_config = {
        "web": {
            "client_id": client_config["client_id"],
            "client_secret": client_config["client_secret"],
            "auth_uri": client_config.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": client_config.get("token_uri", "https://oauth2.googleapis.com/token"),
            "redirect_uris": [effective_redirect_uri],
        }
    }

    try:
        flow_kwargs = {"redirect_uri": effective_redirect_uri}
        if code_verifier:
            flow_kwargs["code_verifier"] = code_verifier

        flow = Flow.from_client_config(
            web_config,
            scopes=SCOPES,
            **flow_kwargs,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        return {
            "token": creds.token,
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri or "https://oauth2.googleapis.com/token",
            "client_id": client_config["client_id"],
            "client_secret": client_config["client_secret"],
            "scopes": creds.scopes or SCOPES,
        }
    except Exception as e:
        logger.warning("Flow.fetch_token failed, trying direct HTTP request: %s", e)
        # Direct HTTP fallback
        import requests
        data = {
            "code": code,
            "client_id": client_config["client_id"],
            "client_secret": client_config["client_secret"],
            "redirect_uri": effective_redirect_uri,
            "grant_type": "authorization_code",
        }
        if code_verifier:
            data["code_verifier"] = code_verifier

        resp = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"Google token exchange failed ({resp.status_code}): {resp.text}")

        token_res = resp.json()
        return {
            "token": token_res.get("access_token"),
            "access_token": token_res.get("access_token"),
            "refresh_token": token_res.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": client_config["client_id"],
            "client_secret": client_config["client_secret"],
            "scopes": SCOPES,
        }
