"""Manual smoke test: python -m zoho_recruit.example

Requires ZOHO_RECRUIT_CLIENT_ID, ZOHO_RECRUIT_CLIENT_SECRET, and
ZOHO_RECRUIT_REFRESH_TOKEN to be set in the environment.
"""

from zoho_recruit import ZohoRecruitClient

if __name__ == "__main__":
    client = ZohoRecruitClient()
    result = client.get_records("Candidates", params={"per_page": 5})
    print(result)
