"""
Minimal local UI for the team.

Clone → pip install → streamlit run app.py → enter your own Jira credentials.
"""

from __future__ import annotations

import json

import streamlit as st

import jira_lib as lib

st.set_page_config(
    page_title="Jira Change Log",
    page_icon="📋",
    layout="wide",
)

# Prefill from local .env if present (never committed)
_env = lib.read_dotenv()


def _sidebar_credentials() -> dict[str, str]:
    st.sidebar.header("Your credentials")
    st.sidebar.caption("Stored only in this browser session. Not uploaded anywhere.")
    email = st.sidebar.text_input("Jira email", value=_env.get("JIRA_EMAIL", ""))
    token = st.sidebar.text_input(
        "Jira API token",
        value=_env.get("JIRA_API_TOKEN", ""),
        type="password",
        help="Create at https://id.atlassian.com/manage-profile/security/api-tokens",
    )
    base_url = st.sidebar.text_input(
        "Jira base URL",
        value=_env.get("JIRA_BASE_URL", "https://yourcompany.atlassian.net"),
        help="Example: https://yourcompany.atlassian.net",
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Optional: copy `.env.example` → `.env` to prefill these fields.")
    return {
        "email": email.strip(),
        "token": token.strip(),
        "base_url": base_url.strip().rstrip("/"),
    }


def _load_rows():
    st.subheader("1. Ticket source")
    source = st.radio(
        "Where are the Jira links?",
        ["Google Sheet URL", "Upload CSV / Excel"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if source == "Google Sheet URL":
        sheet_url = st.text_input(
            "Google Sheet link",
            value=_env.get("GOOGLE_SHEET_URL", ""),
            placeholder="https://docs.google.com/spreadsheets/d/…/edit#gid=0",
            help="Share the sheet as Anyone with the link → Viewer.",
        )
        if not sheet_url.strip():
            return None
        return ("sheet", sheet_url.strip())

    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    if not uploaded:
        return None
    return ("file", uploaded)


def main() -> None:
    st.title("Jira Change Log")
    st.write(
        "Parse Jira links from a sheet, pull ticket details, and group them by category. "
        "Use it as a change summary or a personal/team task log."
    )

    creds = _sidebar_credentials()
    source = _load_rows()

    st.subheader("2. Run")
    run = st.button("Fetch & categorize", type="primary", use_container_width=False)

    if not run:
        if "result" in st.session_state:
            _render_results(st.session_state["result"])
        return

    if not creds["email"] or not creds["token"] or not creds["base_url"]:
        st.error("Fill in Jira email, API token, and base URL in the sidebar.")
        return
    if "yourcompany" in creds["base_url"] or "paste_token" in creds["token"]:
        st.error("Replace the placeholder credentials with your own.")
        return
    if source is None:
        st.error("Add a Google Sheet URL or upload a CSV/Excel file.")
        return

    status = st.status("Working…", expanded=True)
    try:
        kind, payload = source
        if kind == "sheet":
            status.write("Downloading Google Sheet…")
            rows = lib.rows_from_google_sheet(payload)
        else:
            status.write(f"Reading {payload.name}…")
            data = payload.getvalue()
            name = payload.name.lower()
            if name.endswith(".csv"):
                rows = lib.rows_from_csv_bytes(data)
            else:
                rows = lib.rows_from_xlsx_bytes(data)

        status.write(f"Found {len(rows)} row(s). Extracting Jira keys…")
        keys = lib.extract_keys_from_rows(rows)
        status.write(f"Found {len(keys)} unique ticket(s). Fetching from Jira…")

        progress = st.progress(0.0, text="Starting…")

        def on_progress(msg: str) -> None:
            # msg like "Fetching 3/10: PROJ-1"
            status.write(msg)
            try:
                part = msg.split(":", 1)[0]  # Fetching 3/10
                cur, total = part.replace("Fetching", "").strip().split("/")
                progress.progress(min(int(cur) / max(int(total), 1), 1.0), text=msg)
            except Exception:  # noqa: BLE001
                progress.progress(0.0, text=msg)

        tickets, failures = lib.fetch_and_categorize(
            keys,
            email=creds["email"],
            token=creds["token"],
            base_url=creds["base_url"],
            progress=on_progress,
        )
        progress.progress(1.0, text="Done")

        md_path, json_path = lib.save_outputs(tickets, failures)
        result = {
            "tickets": tickets,
            "failures": failures,
            "markdown": lib.build_markdown(tickets),
            "csv": lib.build_csv(tickets),
            "md_path": str(md_path),
            "json_path": str(json_path),
        }
        st.session_state["result"] = result
        status.update(label=f"Done — {len(tickets)} ticket(s)", state="complete")
    except Exception as e:  # noqa: BLE001
        status.update(label="Failed", state="error")
        st.error(str(e))
        return

    _render_results(st.session_state["result"])


def _render_results(result: dict) -> None:
    tickets = result["tickets"]
    failures = result["failures"]
    by_cat = lib.group_by_category(tickets)

    st.subheader("3. Results")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tickets", len(tickets))
    c2.metric("Categories", len(by_cat))
    c3.metric("Needs review", sum(1 for t in tickets if t["category"] == "Needs review"))
    c4.metric("Failed fetches", len(failures))

    if failures:
        with st.expander(f"Failed fetches ({len(failures)})"):
            for f in failures:
                st.text(f)

    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Download Markdown",
        data=result["markdown"],
        file_name="changes-from-jira.md",
        mime="text/markdown",
        key="dl_md",
    )
    d2.download_button(
        "Download CSV (task log)",
        data=result["csv"],
        file_name="changes-from-jira.csv",
        mime="text/csv",
        key="dl_csv",
    )
    d3.download_button(
        "Download JSON",
        data=json.dumps(
            {"ticket_count": len(tickets), "failures": failures, "tickets": tickets},
            indent=2,
            ensure_ascii=False,
        ),
        file_name="changes-from-jira.json",
        mime="application/json",
        key="dl_json",
    )

    filter_cats = ["All"] + list(by_cat.keys())
    chosen = st.selectbox("Filter by category", filter_cats)

    show = tickets if chosen == "All" else by_cat.get(chosen, [])
    table_rows = [
        {
            "Key": t["key"],
            "Category": t["category"],
            "Summary": t["summary"],
            "Change": t.get("change_summary") or "",
            "Type": t["type"],
            "Status": t["status"],
            "URL": t["url"],
        }
        for t in show
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.markdown("#### Details")
    for t in show:
        with st.expander(f"{t['key']} · {t['category']} — {t['summary']}"):
            st.markdown(f"[Open in Jira]({t['url']})")
            st.markdown(f"**Change:** {t.get('change_summary') or '—'}")
            st.markdown(f"**Categorized by:** `{t['category_reason']}`")
            if t.get("components"):
                st.markdown(f"**Components:** {', '.join(t['components'])}")
            if t.get("labels"):
                st.markdown(f"**Labels:** {', '.join(t['labels'])}")
            desc = (t.get("description") or "").strip()
            if desc:
                st.markdown("**Full description**")
                st.write(desc)


if __name__ == "__main__":
    main()
