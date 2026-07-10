import time

import requests

from .config import ZohoRecruitConfig

_TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS = 60


class ZohoRecruitAuthError(Exception):
    pass


class ZohoRecruitTokenManager:
    """Exchanges a long-lived refresh token for short-lived access tokens, caching until expiry."""

    def __init__(self, config: ZohoRecruitConfig):
        self._config = config
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def get_access_token(self) -> str:
        if self._access_token and time.monotonic() < self._expires_at:
            return self._access_token

        response = requests.post(
            self._config.accounts_url,
            params={
                "refresh_token": self._config.refresh_token,
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        payload = response.json()
        if response.status_code != 200 or "access_token" not in payload:
            raise ZohoRecruitAuthError(
                f"Failed to refresh Zoho Recruit access token: {payload}"
            )

        self._access_token = payload["access_token"]
        expires_in = payload.get("expires_in", 3600)
        self._expires_at = time.monotonic() + expires_in - _TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS
        return self._access_token
