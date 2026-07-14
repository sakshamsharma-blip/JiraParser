# Jira Parser

Parse Jira links from a Google Sheet / CSV / Excel → pull descriptions + **images** → group by category → export a **PDF with screenshots embedded** (Markdown/CSV also available). Optional AI rewrite later.

**Repo:** https://github.com/sakshamsharma-blip/JiraParser

---

## Deploy for the team (recommended)

Hosted on **Streamlit Community Cloud** so people only need a link — no local install.

1. Open [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub  
2. **Create app** → select repo `sakshamsharma-blip/JiraParser`  
3. Branch: `main` · Main file: `app.py` · Deploy  
4. Share the public URL (e.g. `https://jiraparser-….streamlit.app`)

**How teammates use it**
1. Open the link  
2. Enter **their own** Jira email, API token, Jira URL  
3. Paste sheet link (Anyone with link → Viewer) or upload CSV/Excel  
4. **Fetch & categorize** → **Download PDF**  

Do **not** put everyone’s Jira tokens in Streamlit Secrets. Each person types their own credentials in the form (session-only). Secrets are only needed if you want optional shared defaults.

**Notes**
- Free Streamlit Cloud apps can sleep when idle; first open may take ~30s  
- Google Sheet must stay shareable via link so the server can download it  
- For private company-only hosting later: Docker / internal VM also works  

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
4. **Download PDF** (screenshots embedded) — Markdown/CSV also available  
5. *(Optional)* Click **Get AI rewrite** → structured bullet Markdown  

**Gemini key:** [Google AI Studio](https://aistudio.google.com/apikey)  
**OpenAI key:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

---

## Pipeline (how it works)

```text
Sheet / CSV
   → Jira tickets (summary, description, category)
   → Image attachments downloaded to output/images/{TICKET}/
   → changes-from-jira.pdf  (images embedded in the document)
   → changes-from-jira.md / .csv also available
   → [optional] Get AI rewrite → changes-structured.md
```

### Images
- Downloads **image** attachments from each Jira ticket
- **Embeds them in the PDF** (actual pictures, not just names)
- Also shows them in the UI under each ticket
- Raw image files remain under `output/images/`
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
