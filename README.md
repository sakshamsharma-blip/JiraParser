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
| 5 | *(Optional)* AI provider + API key | **OpenAI** or **Gemini** at the top — used for **Get AI rewrite** |

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
2. *(Optional)* Choose **OpenAI** or **Google Gemini** and paste that API key  
3. Add sheet/file → **Fetch & categorize** → review parsed results  
4. *(Optional)* Click **Get AI rewrite** → structured bullet Markdown  

**Gemini key:** [Google AI Studio](https://aistudio.google.com/apikey)  
**OpenAI key:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

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
- Choose provider at the top: **OpenAI** or **Google Gemini** (optional key)
- After parsed results, click **Get AI rewrite** to call that provider’s API
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
AI_PROVIDER=openai          # or gemini
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No images | Ticket may have no image attachments (inline-only embeds are limited) |
| AI rewrite fails | Check OpenAI key / billing |
| Sheet fails | Share as Anyone with the link → Viewer |
| Jira 401 | Check email + token + URL |
