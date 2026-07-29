from typing import Any

import requests

from .auth import ZohoRecruitTokenManager
from .config import ZohoRecruitConfig


class ZohoRecruitAPIError(Exception):
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Zoho Recruit API error ({status_code}): {payload}")


class ZohoRecruitClient:
    """Thin REST client for the Zoho Recruit API v2.

    Docs: https://www.zoho.com/recruit/developer-guide/apiv2/modules-api.html
    """

    def __init__(self, config: ZohoRecruitConfig | None = None):
        self._config = config or ZohoRecruitConfig.from_env()
        self._tokens = ZohoRecruitTokenManager(self._config)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Zoho-oauthtoken {self._tokens.get_access_token()}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._config.api_base_url}/{path.lstrip('/')}"
        response = requests.request(method, url, headers=self._headers(), timeout=30, **kwargs)
        if response.status_code >= 400:
            raise ZohoRecruitAPIError(response.status_code, _safe_json(response))
        return _safe_json(response)

    def get_records(self, module: str, params: dict | None = None) -> dict:
        """List records in a module (e.g. Candidates, Job_Openings, Clients)."""
        return self._request("GET", module, params=params or {})

    def get_record(self, module: str, record_id: str) -> dict:
        return self._request("GET", f"{module}/{record_id}")

    def search_records(self, module: str, criteria: str, params: dict | None = None) -> dict:
        """criteria example: (Email:equals:jane@example.com)

        Extra query params (e.g. per_page, page, fields) can be supplied via `params`.
        """
        query = {"criteria": criteria}
        if params:
            query.update(params)
        return self._request("GET", f"{module}/search", params=query)

    def create_records(self, module: str, records: list[dict]) -> dict:
        return self._request("POST", module, json={"data": records})

    def update_records(self, module: str, records: list[dict]) -> dict:
        """Each record dict must include its 'id'."""
        return self._request("PUT", module, json={"data": records})

    def delete_record(self, module: str, record_id: str) -> dict:
        return self._request("DELETE", f"{module}/{record_id}")


def _safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text}
