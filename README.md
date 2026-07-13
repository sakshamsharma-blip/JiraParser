# Jira Parser

Parse Jira links from a Google Sheet / CSV / Excel → pull descriptions → group by category.

**Repo:** https://github.com/sakshamsharma-blip/JiraParser

---

## What each person needs (once)

| # | What | Where to get it | Where to put it |
|---|------|-----------------|-----------------|
| 1 | **Jira email** | Your Atlassian login email | App field: **Email** |
| 2 | **Jira API token** | [Create token](https://id.atlassian.com/manage-profile/security/api-tokens) | App field: **API token** |
| 3 | **Jira URL** | Your Jira home, e.g. `https://yourcompany.atlassian.net` | App field: **Jira URL** |
| 4 | **Sheet or file** | Google Sheet with Jira links/keys, shared as **Anyone with the link → Viewer**, **or** a CSV/Excel export | App field: **Sheet link** or **Upload** |

Each teammate uses **their own** token. Never commit tokens to GitHub.

---

## Team setup (same for everyone)

```bash
git clone git@github.com:sakshamsharma-blip/JiraParser.git
cd JiraParser

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

Browser opens at `http://localhost:8501`.

1. Fill the 3 credential fields  
2. Paste sheet link **or** upload CSV/Excel  
3. Click **Fetch & categorize**  
4. Filter by category, expand tickets, download Markdown/CSV  

---

## Sheet rules

- Must contain Jira keys or browse links (`PROJ-123` or `…/browse/PROJ-123`)
- Category column **not** required (app assigns categories)
- Google Sheet must be viewable via link

---

## Optional: save credentials locally

```bash
cp .env.example .env
# fill JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BASE_URL, GOOGLE_SHEET_URL
```

`.env` is gitignored. The app prefills from it if present.

---

## Output

- On screen: categorized table + ticket details  
- Downloads: Markdown + CSV  
- Also saved under `output/` locally  

Categories come from Jira components → labels → keywords in `category_map.json`. Unmatched → **Needs review**.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Sheet download fails | Share sheet: Anyone with the link → Viewer |
| Jira 401 / auth error | Check email + API token + Jira URL |
| No tickets found | Sheet must contain keys like `PROJ-123` |
| Too many “Needs review” | Edit `category_map.json` and re-run |
