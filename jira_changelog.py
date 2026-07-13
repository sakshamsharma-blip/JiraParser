#!/usr/bin/env python3
"""CLI alternative to the Streamlit UI. Prefer: streamlit run app.py"""

from __future__ import annotations

import sys

import jira_lib as lib


def main() -> None:
    env = lib.read_dotenv()
    required = ["JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_BASE_URL", "GOOGLE_SHEET_URL"]
    missing = [
        k
        for k in required
        if not env.get(k) or "REPLACE" in env.get(k, "") or "paste_token" in env.get(k, "")
    ]
    if missing:
        print(f"Missing in .env: {', '.join(missing)}")
        print("Or use the UI: streamlit run app.py")
        sys.exit(1)

    print("Downloading sheet…")
    rows = lib.rows_from_google_sheet(env["GOOGLE_SHEET_URL"])
    print(f"  {len(rows)} row(s)")
    keys = lib.extract_keys_from_rows(rows)
    print(f"Found {len(keys)} key(s)")

    def progress(msg: str) -> None:
        print(msg)

    tickets, failures = lib.fetch_and_categorize(
        keys,
        email=env["JIRA_EMAIL"],
        token=env["JIRA_API_TOKEN"],
        base_url=env["JIRA_BASE_URL"],
        progress=progress,
    )
    md_path, json_path = lib.save_outputs(tickets, failures)
    needs = sum(1 for t in tickets if t["category"] == "Needs review")
    print("")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(f"Fetched: {len(tickets)}  Failed: {len(failures)}  Needs review: {needs}")


if __name__ == "__main__":
    main()
