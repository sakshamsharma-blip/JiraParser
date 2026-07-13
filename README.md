# Jira Change Log

Local team tool: parse Jira links from a Google Sheet / CSV / Excel file, pull ticket details, and group them by category. Use it as a **change summary** or a **task log**.

Credentials stay on each person's machine (sidebar or local `.env`). Nothing is shared by this app.

## Quick start (for the team)

```bash
git clone <this-repo-url>
cd jira-kb-changelog

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

Browser opens → enter your Jira email, API token, and base URL in the **sidebar** → paste a sheet link or upload CSV/Excel → **Fetch & categorize**.

### Get a Jira API token

1. Open [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create token → paste into the sidebar (or `.env`)

### Google Sheet

Share as **Anyone with the link → Viewer**. Links or keys like `PROJ-123` / `…/browse/PROJ-123` anywhere in the sheet are picked up.

### Optional: prefill credentials

```bash
cp .env.example .env
# edit .env with your values
```

The UI reads `.env` if present. `.env` is gitignored.

## What you get

- Tickets grouped by category (Ordering, Accession, Billing, …)
- Short **change** text from the Jira description/summary
- Downloads: **Markdown**, **CSV** (task log), **JSON**
- Files also saved under `output/` on disk

## Categories

No category column needed in the sheet. Match order:

1. Jira Component  
2. Jira Label  
3. Keywords in summary/description (`category_map.json`)  
4. Else → **Needs review**

Edit `category_map.json` anytime to improve matching for your product language.

## Folder layout

```text
jira-kb-changelog/
  app.py                 # minimal UI (Streamlit)
  jira_lib.py            # shared logic
  jira_changelog.py      # optional CLI
  category_map.json
  requirements.txt
  .env.example
  output/                # generated locally (gitignored)
```

## CLI (optional)

```bash
cp .env.example .env   # fill all fields including GOOGLE_SHEET_URL
python3 jira_changelog.py
```

## Tips

- Each teammate uses **their own** API token
- Re-run whenever the sheet grows
- If many tickets land in Needs review, add keywords/components to `category_map.json`
- Sheet download fails → check link sharing is “Anyone with the link can view”
- Jira 401 → check email + token + base URL
