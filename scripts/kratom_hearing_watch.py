
import os
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

from openai import OpenAI

REPORT = Path("reports/kratom-hearing-watch.md")
TRACKER = Path("ban_hearing.html")

STATES = """
Alabama Alaska Arizona Arkansas California Colorado
Connecticut Delaware Florida Georgia Hawaii Idaho Illinois
Indiana Iowa Kansas Kentucky Louisiana Maine Maryland
Massachusetts Michigan Minnesota Mississippi Missouri Montana
Nebraska Nevada New Hampshire New Jersey New Mexico New York
North Carolina North Dakota Ohio Oklahoma Oregon Pennsylvania
Rhode Island South Carolina South Dakota Tennessee Texas Utah
Vermont Virginia Washington West Virginia Wisconsin Wyoming
"""

PRIORITY = """
Idaho Washington Illinois Mississippi New Hampshire
Michigan Florida Pennsylvania New York Missouri
"""

def main():
    if not TRACKER.exists():
        raise RuntimeError("Hearing tracker HTML was not found")

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing")

    client = OpenAI()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""
    Today is {today} UTC.

    Conduct a nationwide research sweep for newly announced
    or changed kratom sales bans, public hearings, votes,
    committee meetings, council agendas, county commission
    agendas, proposed ordinances, and adopted restrictions.

    Cover all 50 US states:
    {STATES}

    Prioritize these states:
    {PRIORITY}

    Search recent government agendas, meeting packets,
    legal notices, local reporting, and publicly indexed
    social media.

    Prioritize developments from the last 24 hours.

    Find official government sources wherever possible.

    For each finding, report:
    - Jurisdiction and state
    - Exact local date and time, or "not confirmed"
    - Meeting location, or "not confirmed"
    - Status: confirmed hearing, official agenda item,
      tentative discussion, reported adoption, adopted
      with official confirmation, or other
    - Whether ordinary botanical kratom is covered
    - Direct evidence URLs
    - Publication date when available
    - What specifically changed

    Distinguish natural botanical leaf from synthetic,
    semisynthetic, concentrated 7-OH, and mitragynine
    pseudoindoxyl restrictions.

    Do not invent meeting dates, times, ordinance numbers,
    legislative actions, or source URLs.

    Never describe an agenda item as an adopted ban.

    Return only findings supported by identifiable sources.
    If nothing material is found, say so.

    This is research for human review, not authority to
    change a published website.
    """

    response = client.responses.create(
        model="gpt-5.1",
        tools=[{"type": "web_search"}],
        input=prompt,
        max_output_tokens=4500,
    )

    findings = response.output_text.strip()

    if not findings:
        print("No research findings returned.")
        return

    # Exclude any accidental credentials or token-like text.
    findings = re.sub(
        r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}",
        "[REDACTED]",
        findings,
    )

    # Save only source-linked candidate findings.
    # No HTML modification or automatic ban-count change.
    if not re.search(r"https?://", findings):
        print("No source-linked findings. No changes made.")
        return

    content = f"""# Kratom Hearing Watch — {today}

**Status: Research candidates requiring human review**

These findings have not been independently adjudicated
against every entry in the published hearing tracker.

Do not treat this report as confirmation of adoption,
or as authorization to increase ban totals.

## Research findings

{findings}

## Editorial verification required

- Confirm the government agenda or signed ordinance.
- Compare with the existing hearing tracker.
- Verify local date, time, and meeting location.
- Determine whether botanical kratom is covered.
- Distinguish proposed, scheduled, and adopted actions.
- Remove duplicates and outdated findings.
- Approve any website changes separately.
"""

    REPORT.parent.mkdir(parents=True, exist_ok=True)

    if REPORT.exists():
        if REPORT.read_text(encoding="utf-8") == content:
            print("No report changes.")
            return

    REPORT.write_text(content, encoding="utf-8")
    print(f"Research report prepared: {REPORT}")


if __name__ == "__main__":
    main()
