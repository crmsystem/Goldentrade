"""CLI: search Zoho Recruit applicants (Candidates).

Examples:
    python -m zoho_recruit.search_applicants_cli --email jane@example.com
    python -m zoho_recruit.search_applicants_cli --last-name Doe --status "In Progress"

Requires ZOHO_RECRUIT_CLIENT_ID, ZOHO_RECRUIT_CLIENT_SECRET, and
ZOHO_RECRUIT_REFRESH_TOKEN to be set in the environment.
"""

import argparse
import json

from zoho_recruit import ZohoRecruitClient
from zoho_recruit.applicants import search_applicants


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Zoho Recruit applicants (Candidates)")
    parser.add_argument("--first-name")
    parser.add_argument("--last-name")
    parser.add_argument("--email")
    parser.add_argument("--skill")
    parser.add_argument("--status")
    parser.add_argument("--job-opening")
    parser.add_argument("--per-page", type=int, default=200)
    args = parser.parse_args()

    client = ZohoRecruitClient()
    applicants = search_applicants(
        client,
        first_name=args.first_name,
        last_name=args.last_name,
        email=args.email,
        skill=args.skill,
        status=args.status,
        job_opening=args.job_opening,
        per_page=args.per_page,
    )
    print(json.dumps(applicants, indent=2))


if __name__ == "__main__":
    main()
