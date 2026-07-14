"""
Minimal local UI:
1) Credentials (+ optional OpenAI key at top)
2) Fetch → show parsed results
3) Optional AI rewrite button → hit API → show structured output
"""

from __future__ import annotations

import streamlit as st

import jira_lib as lib

st.set_page_config(page_title="Jira Parser", layout="centered")

_env = lib.read_dotenv()


def main() -> None:
    st.title("Jira Parser")

    st.markdown("**1. Credentials** *(yours only — not shared)*")
    email = st.text_input("Jira email", value=_env.get("JIRA_EMAIL", ""), placeholder="you@company.com")
    token = st.text_input(
        "Jira API token",
        value=_env.get("JIRA_API_TOKEN", ""),
        type="password",
        placeholder="Create at id.atlassian.com → Security → API tokens",
    )
    base_url = st.text_input(
        "Jira URL",
        value=_env.get("JIRA_BASE_URL", ""),
        placeholder="https://yourcompany.atlassian.net",
    )
    st.markdown("**AI provider** *(optional — for rewrite after fetch)*")
    provider_labels = {k: v["label"] for k, v in lib.AI_PROVIDERS.items()}
    default_provider = (_env.get("AI_PROVIDER") or "openai").strip().lower()
    if default_provider not in lib.AI_PROVIDERS:
        default_provider = "openai"
    provider_label = st.selectbox(
        "AI provider",
        options=list(provider_labels.values()),
        index=list(lib.AI_PROVIDERS.keys()).index(default_provider),
    )
    provider = next(k for k, lab in provider_labels.items() if lab == provider_label)
    meta = lib.AI_PROVIDERS[provider]
    env_key_name = meta["env_key"]
    models = list(meta.get("models") or [meta["default_model"]])
    env_model = _env.get(meta["env_model"], meta["default_model"])
    if env_model not in models:
        models = [env_model] + models
    model = st.selectbox(
        "AI model",
        options=models,
        index=models.index(env_model) if env_model in models else 0,
        key=f"ai_model_select_{provider}",
    )
    key_placeholder = {
        "openai": "sk-…",
        "gemini": "AIza…  (Google AI Studio)",
    }.get(provider, "API key")
    ai_key = st.text_input(
        f"{meta['label']} API key (optional)",
        value=_env.get(env_key_name, ""),
        type="password",
        placeholder=f"{key_placeholder} — only needed for AI rewrite later",
        help="Optional. Enter now; after fetch click Get AI rewrite. If Gemini hits quota, wait or switch model.",
        key=f"ai_key_{provider}",
    )
    st.session_state["ai_provider"] = provider
    st.session_state["ai_key"] = ai_key.strip()
    st.session_state["ai_model"] = model
    st.session_state["ai_base"] = _env.get(meta["env_base"], meta["default_base"])

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
        # Fresh fetch clears previous AI rewrite
        if "result" in st.session_state:
            st.session_state["result"].pop("structured", None)
        _run(email.strip(), token.strip(), base_url.strip().rstrip("/"), sheet_url.strip(), uploaded)
    elif "result" in st.session_state:
        _render_results(st.session_state["result"])


def _run(email: str, token: str, base_url: str, sheet_url: str, uploaded) -> None:
    if not email or not token or not base_url:
        st.error("Fill Jira email, API token, and Jira URL.")
        return
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
        status.write(f"{len(keys)} ticket(s) found. Fetching tickets + images…")
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
            download_images=True,
        )
        progress.progress(1.0, text="Done")
        status.write("Building PDF with images…")
        lib.save_outputs(tickets, failures)
        n_img = lib.count_images(tickets)
        st.session_state["result"] = {
            "tickets": tickets,
            "failures": failures,
            "markdown": lib.build_markdown(tickets),
            "csv": lib.build_csv(tickets),
            "pdf": lib.build_pdf(tickets),
            "structured": None,
        }
        status.update(
            label=f"Done — {len(tickets)} ticket(s), {n_img} image(s)",
            state="complete",
        )
    except Exception as e:  # noqa: BLE001
        status.update(label="Failed", state="error")
        st.error(str(e))
        return

    _render_results(st.session_state["result"])


def _render_results(result: dict) -> None:
    tickets = result["tickets"]
    failures = result["failures"]
    by_cat = lib.group_by_category(tickets)
    n_img = lib.count_images(tickets)
    if not result.get("pdf"):
        try:
            result["pdf"] = lib.build_pdf(tickets)
            st.session_state["result"] = result
        except Exception as e:  # noqa: BLE001
            st.warning(f"PDF not ready yet: {e}")

    st.markdown("---")
    st.markdown("**Parsed results**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tickets", len(tickets))
    c2.metric("Images", n_img)
    c3.metric("Needs review", sum(1 for t in tickets if t["category"] == "Needs review"))
    c4.metric("Failed", len(failures))

    if failures:
        with st.expander(f"Failed ({len(failures)})"):
            for f in failures:
                st.text(f)

    d1, d2, d3 = st.columns(3)
    if result.get("pdf"):
        d1.download_button(
            "Download PDF",
            result["pdf"],
            "changes-from-jira.pdf",
            "application/pdf",
            key="dl_pdf",
            type="primary",
        )
    d2.download_button(
        "Download Markdown",
        result["markdown"],
        "changes-from-jira.md",
        "text/markdown",
        key="dl_md",
    )
    d3.download_button(
        "Download CSV",
        result["csv"],
        "changes-from-jira.csv",
        "text/csv",
        key="dl_csv",
    )
    if n_img:
        st.caption(
            f"{n_img} image(s) embedded in the PDF. Also saved under `output/images/`."
        )

    chosen = st.selectbox("Category", ["All"] + list(by_cat.keys()))
    show = tickets if chosen == "All" else by_cat.get(chosen, [])
    st.dataframe(
        [
            {
                "Key": t["key"],
                "Category": t["category"],
                "Summary": t["summary"],
                "Images": len(t.get("images") or []),
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
            for img in t.get("images") or []:
                img_path = lib.OUT_DIR / img["rel_path"]
                if img_path.exists():
                    st.image(str(img_path), caption=img["filename"], use_container_width=True)

    st.markdown("---")
    st.markdown("**AI rewrite** *(optional)*")
    provider = st.session_state.get("ai_provider") or "openai"
    provider_label = lib.AI_PROVIDERS.get(provider, {}).get("label", provider)
    has_key = bool(st.session_state.get("ai_key"))
    if not has_key:
        st.caption(f"Add a {provider_label} API key in step 1 above to enable this.")
    else:
        st.caption(f"Will use **{provider_label}** with the key from step 1.")
    if st.button("Get AI rewrite", disabled=not has_key, type="primary"):
        with st.spinner(f"Calling {provider_label} and rewriting…"):
            try:
                structured = lib.rewrite_structured_markdown(
                    result["markdown"],
                    api_key=st.session_state["ai_key"],
                    provider=provider,
                    model=st.session_state.get("ai_model"),
                    api_base=st.session_state.get("ai_base"),
                )
                result["structured"] = structured
                st.session_state["result"] = result
                st.success("AI rewrite ready.")
            except Exception as e:  # noqa: BLE001
                st.error(str(e))

    if result.get("structured"):
        st.download_button(
            "Download AI rewrite (Markdown)",
            result["structured"],
            "changes-structured.md",
            "text/markdown",
            key="dl_structured",
        )
        st.markdown("**AI rewrite preview**")
        st.markdown(result["structured"])


if __name__ == "__main__":
    main()
