"""
crm/zoho_client.py

Final step of the pipeline: log the finished call into Zoho CRM as a Call
activity, linked to the matching Contact/Lead when the caller's phone number
is on file.

Auth: standard Zoho CRM OAuth2 self-client (client credentials + a
long-lived refresh token). Generate the refresh token once via the
Zoho API Console (Self Client) with scope:
  ZohoCRM.modules.calls.CREATE,ZohoCRM.modules.leads.READ,
  ZohoCRM.modules.contacts.READ,ZohoCRM.coql.READ
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import httpx

from config import settings


@dataclass
class CrmMatch:
    module: str  # "Leads" or "Contacts"
    record_id: str
    name: str


class ZohoCRMClient:
    def __init__(self):
        self._access_token: str | None = None
        self._access_token_expires_at: float = 0.0

    # -- auth -----------------------------------------------------------

    def _refresh_access_token(self) -> str:
        z = settings.zoho
        if not (z.client_id and z.client_secret and z.refresh_token):
            raise RuntimeError("ZOHO_CLIENT_ID / ZOHO_CLIENT_SECRET / ZOHO_REFRESH_TOKEN must be set")

        resp = httpx.post(
            f"{z.accounts_url}/oauth/v2/token",
            params={
                "refresh_token": z.refresh_token,
                "client_id": z.client_id,
                "client_secret": z.client_secret,
                "grant_type": "refresh_token",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()

        self._access_token = data["access_token"]
        # Refresh a little early to avoid using a token that expires mid-request.
        self._access_token_expires_at = time.time() + data.get("expires_in", 3600) - 60
        return self._access_token

    def _headers(self) -> dict[str, str]:
        if not self._access_token or time.time() >= self._access_token_expires_at:
            self._refresh_access_token()
        return {"Authorization": f"Zoho-oauthtoken {self._access_token}"}

    # -- lookups ----------------------------------------------------------

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        return re.sub(r"[^\d+]", "", phone)

    def find_by_phone(self, phone: str) -> CrmMatch | None:
        """Look up a Contact first, then a Lead, by phone number (E.164 or local)."""
        digits = self._normalize_phone(phone)
        if not digits:
            return None

        for module in ("Contacts", "Leads"):
            url = f"{settings.zoho.api_domain}/crm/v6/{module}/search"
            resp = httpx.get(
                url,
                params={"phone": digits},
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code == 204:
                continue
            resp.raise_for_status()
            records = resp.json().get("data", [])
            if records:
                rec = records[0]
                name = rec.get("Full_Name") or f"{rec.get('First_Name', '')} {rec.get('Last_Name', '')}".strip()
                return CrmMatch(module=module, record_id=rec["id"], name=name or phone)
        return None

    # -- call logging -------------------------------------------------------

    def log_call(
        self,
        *,
        caller_phone: str,
        call_start_iso: str,
        duration_seconds: int,
        transcript: str,
        summary: str,
        call_type: str = "Inbound",
        call_result: str = "Completed",
    ) -> str:
        """Create a Call record in Zoho CRM for the finished conversation.

        Returns the new Call record's id. If the caller can't be matched to an
        existing Contact/Lead, the call is still logged, just without Who_Id.
        """
        match = self.find_by_phone(caller_phone)

        call_record: dict[str, object] = {
            "Subject": f"AI voice agent call - {match.name if match else caller_phone}",
            "Call_Type": call_type,
            "Call_Start_Time": call_start_iso,
            "Call_Duration_in_seconds": str(duration_seconds),
            "Call_Result": call_result,
            "Description": f"Summary:\n{summary}\n\nTranscript:\n{transcript}",
        }
        if match is not None:
            call_record["Who_Id"] = {"id": match.record_id}

        url = f"{settings.zoho.api_domain}/crm/v6/Calls"
        resp = httpx.post(url, headers=self._headers(), json={"data": [call_record]}, timeout=15.0)
        resp.raise_for_status()
        result = resp.json()["data"][0]
        if result.get("status") != "success":
            raise RuntimeError(f"Zoho CRM rejected the Call record: {result}")
        return result["details"]["id"]
