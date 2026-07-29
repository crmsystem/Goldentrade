import os
from dataclasses import dataclass


class ZohoRecruitConfigError(Exception):
    pass


@dataclass
class ZohoRecruitConfig:
    client_id: str
    client_secret: str
    refresh_token: str
    dc: str = "com"

    @property
    def accounts_url(self) -> str:
        return f"https://accounts.zoho.{self.dc}/oauth/v2/token"

    @property
    def api_base_url(self) -> str:
        return f"https://recruit.zoho.{self.dc}/recruit/v2"

    @classmethod
    def from_env(cls) -> "ZohoRecruitConfig":
        client_id = os.environ.get("ZOHO_RECRUIT_CLIENT_ID")
        client_secret = os.environ.get("ZOHO_RECRUIT_CLIENT_SECRET")
        refresh_token = os.environ.get("ZOHO_RECRUIT_REFRESH_TOKEN")
        dc = os.environ.get("ZOHO_RECRUIT_DC", "com")

        missing = [
            name
            for name, value in (
                ("ZOHO_RECRUIT_CLIENT_ID", client_id),
                ("ZOHO_RECRUIT_CLIENT_SECRET", client_secret),
                ("ZOHO_RECRUIT_REFRESH_TOKEN", refresh_token),
            )
            if not value
        ]
        if missing:
            raise ZohoRecruitConfigError(
                f"Missing required environment variable(s): {', '.join(missing)}"
            )

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            dc=dc,
        )
