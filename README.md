# Goldentrade

## Zoho Recruit integration

`zoho_recruit/` is a thin Python client for the [Zoho Recruit API v2](https://www.zoho.com/recruit/developer-guide/apiv2/modules-api.html),
covering list/get/search/create/update/delete on any module (`Candidates`, `Job_Openings`, `Clients`, etc.), plus
an `applicants` helper for searching the `Candidates` module.

### 1. Register an API client

In the [Zoho API Console](https://api-console.zoho.com/) (same data center as your Recruit account, `.com` here):

- Create a **Self Client** (simplest for server-to-server use) or a **Server-based** client.
- Note the generated **Client ID** and **Client Secret**.

### 2. Generate a refresh token

Generate a grant token scoped for Recruit, e.g. `ZohoRecruit.modules.ALL,ZohoRecruit.settings.ALL`, then exchange it for
a refresh token:

```bash
curl -X POST https://accounts.zoho.com/oauth/v2/token \
  -d "code=<GRANT_TOKEN>" \
  -d "client_id=<CLIENT_ID>" \
  -d "client_secret=<CLIENT_SECRET>" \
  -d "redirect_uri=<REDIRECT_URI>" \
  -d "grant_type=authorization_code"
```

The response includes a `refresh_token` — save it, it does not expire unless revoked.

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in `ZOHO_RECRUIT_CLIENT_ID`, `ZOHO_RECRUIT_CLIENT_SECRET`,
`ZOHO_RECRUIT_REFRESH_TOKEN` (and `ZOHO_RECRUIT_DC` if not on the `.com` data center).

### 4. Use it

```bash
pip install -r requirements.txt
python -m zoho_recruit.example
```

```python
from zoho_recruit import ZohoRecruitClient

client = ZohoRecruitClient()
candidates = client.get_records("Candidates", params={"per_page": 5})
client.create_records("Candidates", [{"Last_Name": "Doe", "Email": "jane@example.com"}])
```

### Searching applicants

`zoho_recruit.applicants.search_applicants` searches the `Candidates` module by any combination of
first/last name, email, skill, status, and job opening (filters are ANDed together):

```python
from zoho_recruit import ZohoRecruitClient, search_applicants

client = ZohoRecruitClient()
applicants = search_applicants(client, last_name="Doe", status="In Progress")
```

Or from the command line:

```bash
python -m zoho_recruit.search_applicants_cli --last-name Doe --status "In Progress"
python -m zoho_recruit.search_applicants_cli --email jane@example.com
```
