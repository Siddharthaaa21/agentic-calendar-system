"""Automated tests for Google OAuth Web Flow and Session Isolation."""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config.google_config import (
    get_google_client_config,
    create_authorization_url,
    _pending_oauth,
)
from app.services.calendar_service import (
    is_google_calendar_connected,
    get_connected_account,
    set_session_token,
    disconnect_session,
    _session_tokens,
)


class TestGoogleOAuth(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_client_config_resolved(self):
        cfg = get_google_client_config()
        self.assertIsNotNone(cfg)
        self.assertTrue(cfg.get("client_id"))
        self.assertTrue(cfg.get("client_secret"))

    def test_create_authorization_url(self):
        redirect_uri = "https://axon-calender.streamlit.app"
        res = create_authorization_url(redirect_uri, session_id="test_sess_abc")
        self.assertIn("auth_url", res)
        self.assertIn("accounts.google.com", res["auth_url"])
        self.assertIn("https%3A%2F%2Faxon-calender.streamlit.app", res["auth_url"])
        self.assertIn("test_sess_abc", res["state"])

    def test_endpoint_auth_url(self):
        resp = self.client.get("/auth/google/url?redirect_uri=https://axon-calender.streamlit.app&session_id=sess_123")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertTrue(data.get("auth_url").startswith("https://accounts.google.com/o/oauth2/auth"))

    def test_session_isolation(self):
        sess_a = "user_alpha"
        sess_b = "user_beta"

        # Initially neither is connected
        self.assertFalse(is_google_calendar_connected(sess_a))
        self.assertFalse(is_google_calendar_connected(sess_b))

        # Mock mock-token for session A
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds.refresh_token = "dummy_refresh"
        mock_creds.to_json.return_value = '{"token": "dummy"}'

        with patch("app.services.calendar_service.build") as mock_build:
            mock_service = MagicMock()
            mock_service.calendarList().get().execute.return_value = {"id": "alpha@example.com"}
            mock_build.return_value = mock_service

            set_session_token(sess_a, mock_creds)

            # Session A is connected to alpha@example.com
            self.assertTrue(is_google_calendar_connected(sess_a))
            self.assertEqual(get_connected_account(sess_a), "alpha@example.com")

            # Session B is strictly isolated and NOT connected
            self.assertFalse(is_google_calendar_connected(sess_b))
            self.assertIsNone(get_connected_account(sess_b))

            # Disconnect session A
            disconnect_session(sess_a)
            self.assertFalse(is_google_calendar_connected(sess_a))


if __name__ == "__main__":
    unittest.main()
