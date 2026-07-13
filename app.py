"""
Minimal local UI — only required fields.

Clone → install → run → fill 4 fields → Fetch.
"""

from __future__ import annotations

import json

import streamlit as st

import jira_lib as lib

st.set_page_config(page_title="Jira Parser", layout="centered")

_env = lib.read_dotenv()


def main() -> None:
    st.title("Jira Parser")

    st.markdown("**1. Jira credentials** *(your own — not shared)*")
    email = st.text_input("Email", value=_env.get("JIRA_EMAIL", ""), placeholder="you@company.com")
    token = st.text_input(
        "API token",
        value=_env.get("JIRA_API_TOKEN", ""),
        type="password",
        placeholder="Create at id.atlassian.com → Security → API tokens",
    )
    base_url = st.text_input(
        "Jira URL",
        value=_env.get("JIRA_BASE_URL", ""),
        placeholder="https://yourcompany.atlassian.net",
    )

    st.markdown("**2. Ticket list**")
    source_mode = st.radio(
        "Source",
        ["Google Sheet link", "Upload CSV / Excel"],
        horizontal=True,
        label_visibility="collapsed",
    )
    sheet_url = ""
    uploaded = None
    if source_mode == "Google Sheet link":
        sheet_url = st.text_input(
            "Sheet link",
            value=_env.get("GOOGLE_SHEET_URL", ""),
            placeholder="https://docs.google.com/spreadsheets/d/…  (Anyone with link → Viewer)",
        )
    else:
        uploaded = st.file_uploader("CSV or Excel", type=["csv", "xlsx"])

    run = st.button("Fetch & categorize", type="primary")

    if run:
        _run(email.strip(), token.strip(), base_url.strip().rstrip("/"), sheet_url.strip(), uploaded)
    elif "result" in st.session_state:
        _render_results(st.session_state["result"])


def _run(email: str, token: str, base_url: str, sheet_url: str, uploaded) -> None:
    if not email or not token or not base_url:
        st.error("Fill Email, API token, and Jira URL.")
        return
    if "atlassian.net" not in base_url and "jira" not in base_url.lower():
        st.warning("Jira URL should look like https://yourcompany.atlassian.net")
    if not sheet_url and uploaded is None:
        st.error("Paste a Google Sheet link or upload a file.")
        return

    status = st.status("Working…", expanded=True)
    try:
        if uploaded is not None:
            status.write(f"Reading {uploaded.name}…")
            data = uploaded.getvalue()
            name = uploaded.name.lower()
            rows = (
                lib.rows_from_csv_bytes(data)
                if name.endswith(".csv")
                else lib.rows_from_xlsx_bytes(data)
            )
        else:
            status.write("Downloading sheet…")
            rows = lib.rows_from_google_sheet(sheet_url)

        keys = lib.extract_keys_from_rows(rows)
        status.write(f"{len(keys)} ticket(s) found. Fetching…")
        progress = st.progress(0.0)

        def on_progress(msg: str) -> None:
            status.write(msg)
            try:
                cur, total = msg.split(":", 1)[0].replace("Fetching", "").strip().split("/")
                progress.progress(min(int(cur) / max(int(total), 1), 1.0), text=msg)
            except Exception:  # noqa: BLE001
                pass

        tickets, failures = lib.fetch_and_categorize(
            keys,
            email=email,
            token=token,
            base_url=base_url,
            progress=on_progress,
        )
        progress.progress(1.0, text="Done")
        lib.save_outputs(tickets, failures)
        st.session_state["result"] = {
            "tickets": tickets,
            "failures": failures,
            "markdown": lib.build_markdown(tickets),
            "csv": lib.build_csv(tickets),
        }
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

    st.markdown("---")
    st.markdown("**Results**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tickets", len(tickets))
    c2.metric("Needs review", sum(1 for t in tickets if t["category"] == "Needs review"))
    c3.metric("Failed", len(failures))

    if failures:
        with st.expander(f"Failed ({len(failures)})"):
            for f in failures:
                st.text(f)

    d1, d2 = st.columns(2)
    d1.download_button("Download Markdown", result["markdown"], "changes-from-jira.md", "text/markdown", key="dl_md")
    d2.download_button("Download CSV", result["csv"], "changes-from-jira.csv", "text/csv", key="dl_csv")

    chosen = st.selectbox("Category", ["All"] + list(by_cat.keys()))
    show = tickets if chosen == "All" else by_cat.get(chosen, [])
    st.dataframe(
        [
            {
                "Key": t["key"],
                "Category": t["category"],
                "Summary": t["summary"],
                "Change": t.get("change_summary") or "",
                "Status": t["status"],
            }
            for t in show
        ],
        use_container_width=True,
        hide_index=True,
    )

    for t in show:
        with st.expander(f"{t['key']} — {t['summary']}"):
            st.markdown(f"[{t['key']}]({t['url']}) · **{t['category']}**")
            st.write(t.get("change_summary") or "—")
            desc = (t.get("description") or "").strip()
            if desc and desc != t.get("change_summary"):
                st.caption("Full description")
                st.write(desc)


if __name__ == "__main__":
    main()
