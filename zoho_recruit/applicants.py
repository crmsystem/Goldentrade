"""Search helpers for the Zoho Recruit Candidates ("applicants") module."""

from __future__ import annotations

from .client import ZohoRecruitClient

_MODULE = "Candidates"


def _criterion(field: str, operator: str, value: str) -> str:
    return f"({field}:{operator}:{value})"


def build_applicant_search_criteria(
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    skill: str | None = None,
    status: str | None = None,
    job_opening: str | None = None,
) -> str:
    """Build a Zoho Recruit search-criteria string from applicant filters.

    Filters are ANDed together; at least one must be supplied. `job_opening`
    assumes the org's Candidates layout has a field mapping applicants to a
    job opening (API name `Job_Opening_Name`) — adjust the field name below
    if your org uses a different one, e.g. via the Applications module.
    """
    criteria = []
    if first_name:
        criteria.append(_criterion("First_Name", "starts_with", first_name))
    if last_name:
        criteria.append(_criterion("Last_Name", "starts_with", last_name))
    if email:
        criteria.append(_criterion("Email", "equals", email))
    if skill:
        criteria.append(_criterion("Skill_Set", "starts_with", skill))
    if status:
        criteria.append(_criterion("Candidate_Status", "equals", status))
    if job_opening:
        criteria.append(_criterion("Job_Opening_Name", "equals", job_opening))

    if not criteria:
        raise ValueError("At least one search filter must be provided")

    combined = criteria[0]
    for extra in criteria[1:]:
        combined = f"({combined}and{extra})"
    return combined


def search_applicants(
    client: ZohoRecruitClient,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    skill: str | None = None,
    status: str | None = None,
    job_opening: str | None = None,
    per_page: int = 200,
) -> list[dict]:
    """Search Zoho Recruit applicants (Candidates) by any combination of filters.

    Returns the list of matching candidate records (empty list if none found).
    """
    criteria = build_applicant_search_criteria(
        first_name=first_name,
        last_name=last_name,
        email=email,
        skill=skill,
        status=status,
        job_opening=job_opening,
    )
    result = client.search_records(_MODULE, criteria, params={"per_page": per_page})
    return result.get("data", [])
