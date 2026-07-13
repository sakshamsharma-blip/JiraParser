# Jira Parser

Parse Jira links from a Google Sheet / CSV / Excel → pull descriptions + **images** → group by category → optional **AI structured summary**.

**Repo:** https://github.com/sakshamsharma-blip/JiraParser

---

## What each person needs

| # | What | Where |
|---|------|--------|
| 1 | Jira email | App: **Email** |
| 2 | Jira API token | [Create token](https://id.atlassian.com/manage-profile/security/api-tokens) → **API token** |
| 3 | Jira URL | e.g. `https://yourcompany.atlassian.net` |
| 4 | Sheet or CSV/Excel | Google Sheet (**Anyone with link → Viewer**) or upload |
| 5 | *(Optional)* OpenAI API key | Enter at the **top** of the app — used later for **Get AI rewrite** |

---

## Team setup

```bash
git clone git@github.com:sakshamsharma-blip/JiraParser.git
cd JiraParser
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

1. Fill Jira credentials  
2. *(Optional)* Paste OpenAI API key at the top  
3. Add sheet/file → **Fetch & categorize** → review parsed results  
4. *(Optional)* Click **Get AI rewrite** → structured bullet Markdown  

---

## Pipeline (how it works)

```text
Sheet / CSV
   → Jira tickets (summary, description, category)
   → Image attachments downloaded to output/images/{TICKET}/
   → changes-from-jira.md  (raw, with ![…](images/…))
   → [optional] Get AI rewrite → changes-structured.md
```

### Images
- Downloads **image** attachments from each Jira ticket
- Embeds them in the Markdown as local relative links
- Shows them in the UI under each ticket

### AI rewrite
- Optional OpenAI key is entered **at the start** (with credentials)
- After parsed results, click **Get AI rewrite** to call the API
- Output: clear bullet points per category/ticket, image links kept
- Without a key, fetch/results still work; the AI button stays disabled

---

## Optional `.env`

```bash
cp .env.example .env
```

```
JIRA_EMAIL=
JIRA_API_TOKEN=
JIRA_BASE_URL=
GOOGLE_SHEET_URL=
OPENAI_API_KEY=          # optional
OPENAI_MODEL=gpt-4o-mini # optional
OPENAI_API_BASE=https://api.openai.com/v1
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No images | Ticket may have no image attachments (inline-only embeds are limited) |
| AI rewrite fails | Check OpenAI key / billing |
| Sheet fails | Share as Anyone with the link → Viewer |
| Jira 401 | Check email + token + URL |
