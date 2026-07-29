"""
tests/test_zoho_client.py

Verifies ZohoCRMClient's token refresh, phone-based caller lookup, and Call
record construction against fake HTTP responses (via monkeypatching
httpx.get/httpx.post), so the OAuth + REST logic is checked without ever
calling the real Zoho API.
"""

from __future__ import annotations

import httpx
import pytest

from crm.zoho_client import ZohoCRMClient
from config import settings


def _response(status_code: int, url: str = "https://example.test", **kwargs) -> httpx.Response:
    """httpx.Response.raise_for_status() requires a bound request - real calls get one
    automatically, but responses built by hand for tests need it attached explicitly."""
    return httpx.Response(status_code, request=httpx.Request("GET", url), **kwargs)


@pytest.fixture(autouse=True)
def zoho_settings(monkeypatch):
    monkeypatch.setattr(settings.zoho, "client_id", "test-client-id")
    monkeypatch.setattr(settings.zoho, "client_secret", "test-client-secret")
    monkeypatch.setattr(settings.zoho, "refresh_token", "test-refresh-token")
    monkeypatch.setattr(settings.zoho, "accounts_url", "https://accounts.zoho.test")
    monkeypatch.setattr(settings.zoho, "api_domain", "https://crm.zoho.test")


def test_normalize_phone_strips_formatting():
    assert ZohoCRMClient._normalize_phone("+1 (555) 123-4567") == "+15551234567"


def test_refresh_access_token_calls_correct_endpoint(monkeypatch):
    captured = {}

    def fake_post(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return _response(200, json={"access_token": "abc123", "expires_in": 3600})

    monkeypatch.setattr(httpx, "post", fake_post)

    client = ZohoCRMClient()
    token = client._refresh_access_token()

    assert token == "abc123"
    assert captured["url"] == "https://accounts.zoho.test/oauth/v2/token"
    assert captured["params"]["grant_type"] == "refresh_token"
    assert captured["params"]["refresh_token"] == "test-refresh-token"


def test_find_by_phone_returns_first_matching_contact(monkeypatch):
    def fake_post(url, params=None, timeout=None):
        return _response(200, json={"access_token": "tok", "expires_in": 3600})

    def fake_get(url, params=None, headers=None, timeout=None):
        assert "Contacts/search" in url
        return _response(
            200,
            json={"data": [{"id": "contact-1", "Full_Name": "Jane Doe"}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    client = ZohoCRMClient()
    match = client.find_by_phone("+1 555 123 4567")

    assert match is not None
    assert match.module == "Contacts"
    assert match.record_id == "contact-1"
    assert match.name == "Jane Doe"


def test_find_by_phone_falls_back_to_leads_when_no_contact(monkeypatch):
    def fake_post(url, params=None, timeout=None):
        return _response(200, json={"access_token": "tok", "expires_in": 3600})

    def fake_get(url, params=None, headers=None, timeout=None):
        if "Contacts/search" in url:
            return _response(204)
        assert "Leads/search" in url
        return _response(200, json={"data": [{"id": "lead-1", "First_Name": "John", "Last_Name": "Smith"}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    client = ZohoCRMClient()
    match = client.find_by_phone("+15550001111")

    assert match is not None
    assert match.module == "Leads"
    assert match.record_id == "lead-1"
    assert match.name == "John Smith"


def test_find_by_phone_returns_none_when_no_match(monkeypatch):
    def fake_post(url, params=None, timeout=None):
        return _response(200, json={"access_token": "tok", "expires_in": 3600})

    def fake_get(url, params=None, headers=None, timeout=None):
        return _response(204)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    client = ZohoCRMClient()
    assert client.find_by_phone("+15559998888") is None


def test_log_call_includes_who_id_when_caller_matched(monkeypatch):
    captured = {}

    def fake_post(url, params=None, timeout=None, headers=None, json=None):
        if "oauth/v2/token" in url:
            return _response(200, json={"access_token": "tok", "expires_in": 3600})
        captured["url"] = url
        captured["json"] = json
        return _response(
            200,
            json={"data": [{"status": "success", "details": {"id": "call-99"}}]},
        )

    def fake_get(url, params=None, headers=None, timeout=None):
        return _response(200, json={"data": [{"id": "contact-1", "Full_Name": "Jane Doe"}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    client = ZohoCRMClient()
    call_id = client.log_call(
        caller_phone="+15551234567",
        call_start_iso="2026-07-29T10:00:00",
        duration_seconds=42,
        transcript="user: hi\nassistant: hello",
        summary="Caller said hi.",
    )

    assert call_id == "call-99"
    assert captured["url"] == "https://crm.zoho.test/crm/v6/Calls"
    record = captured["json"]["data"][0]
    assert record["Who_Id"] == {"id": "contact-1"}
    assert "Caller said hi." in record["Description"]


def test_log_call_raises_when_zoho_rejects_the_record(monkeypatch):
    def fake_post(url, params=None, timeout=None, headers=None, json=None):
        if "oauth/v2/token" in url:
            return _response(200, json={"access_token": "tok", "expires_in": 3600})
        return _response(200, json={"data": [{"status": "error", "message": "invalid data"}]})

    def fake_get(url, params=None, headers=None, timeout=None):
        return _response(204)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    client = ZohoCRMClient()
    with pytest.raises(RuntimeError, match="Zoho CRM rejected"):
        client.log_call(
            caller_phone="+15551234567",
            call_start_iso="2026-07-29T10:00:00",
            duration_seconds=10,
            transcript="t",
            summary="s",
        )
