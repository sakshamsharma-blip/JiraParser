# Jira Parser

Parse Jira links from a Google Sheet / CSV / Excel → pull descriptions + **images** → group by category → export a **PDF with screenshots embedded** (Markdown/CSV also available). Optional AI rewrite later.

**Repo:** https://github.com/sakshamsharma-blip/JiraParser

---

## Choose how to run

| | **Option A — Use deployed app** | **Option B — Run locally** |
|---|--------------------------------|------------------------------|
| Best for | Most of the team (no setup) | Devs / offline / custom changes |
| Link | https://jiraparser.streamlit.app/ | http://localhost:8501 after setup |
| Install | None | Python + `pip install` |

---

## Option A — Use the deployed app (recommended)

**Open:** https://jiraparser.streamlit.app/

1. Enter **your own** Jira email, API token, and Jira URL  
2. Paste a **Google Sheet link** (Anyone with link → Viewer) **or** upload CSV/Excel  
3. Click **Fetch & categorize**  
4. **Download PDF** (screenshots embedded) — Markdown/CSV also available  
5. *(Optional)* Add an AI key at the top → **Get AI rewrite** after fetch  

**Notes**
- Credentials stay in your browser session only — not stored on the server  
- First load after idle can take ~30 seconds (free Streamlit tier)  
- Each person uses **their own** Jira API token  

---

## Option B — Run locally

### 1. Clone and install

```bash
git clone git@github.com:sakshamsharma-blip/JiraParser.git
cd JiraParser

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start the app

```bash
streamlit run app.py
```

Opens at **http://localhost:8501**

### 3. Use the app

Same steps as Option A: fill credentials → sheet/file → **Fetch & categorize** → **Download PDF**.

### Optional — prefill fields from `.env`

```bash
cp .env.example .env
# edit .env with your values (never commit this file)
```

The UI reads `.env` if present. Useful so you don’t retype Jira URL or sheet link every time.

---

## What you need (both options)

| # | What | Where to get it |
|---|------|-----------------|
| 1 | Jira email | Your Atlassian login |
| 2 | Jira API token | [Create token](https://id.atlassian.com/manage-profile/security/api-tokens) |
| 3 | Jira URL | e.g. `https://yourcompany.atlassian.net` |
| 4 | Sheet or file | Google Sheet (**Anyone with link → Viewer**) or CSV/Excel upload |
| 5 | *(Optional)* AI key | [OpenAI](https://platform.openai.com/api-keys) or [Gemini](https://aistudio.google.com/apikey) — only for **Get AI rewrite** |

---

## What you get

```text
Sheet / CSV
   → Jira tickets (summary, description, category)
   → Image attachments saved under output/images/{TICKET}/
   → changes-from-jira.pdf  (images embedded in the document)
   → changes-from-jira.md / .csv also available
   → [optional] Get AI rewrite → changes-structured.md
```

- **PDF** — actual screenshots in the document, not just filenames  
- **Categories** — from Jira components → labels → keywords (`category_map.json`)  
- **AI rewrite** — optional; fetch + PDF work without it  

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Deployed app slow / blank on first open | Wait ~30s and refresh (free tier wake-up) |
| Sheet download fails | Share sheet as **Anyone with the link → Viewer** |
| Jira 401 / auth error | Check email + API token + Jira URL |
| No images in PDF | Ticket may have no image attachments |
| AI rewrite fails | Check API key / quota; try `gemini-2.0-flash-lite` for Gemini free tier |
| Local: `localhost` connection error | Run `streamlit run app.py` again in the project folder |

---

## For admins (redeploy / update hosted app)

- **Manage app:** https://share.streamlit.io/  
- **Repo:** `sakshamsharma-blip/JiraParser` · branch `main` · entry file `streamlit_app.py` or `app.py`  
- Push to `main` on GitHub → Streamlit redeploys automatically  
