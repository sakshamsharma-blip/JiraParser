# Jira → KB changelog (standalone)

Separate tool from the Knowledge Base site. Use this repo only to pull Jira tickets from a Google Sheet and produce a categorized change document. Then use that document to update `workflow-config-pages` (or any other docs project).

## Folder layout

```text
jira-kb-changelog/
  .env.example          # copy → .env (secrets stay local)
  category_map.json     # how tickets map to KB stages
  jira_changelog.py     # the script
  README.md             # this file
  output/               # generated (gitignored)
    changes-from-jira.md
    changes-from-jira.json
```

## One-time setup

1. Create a [Jira API token](https://id.atlassian.com/manage-profile/security/api-tokens).
2. Share the Google Sheet as **Anyone with the link → Viewer**.
3. Configure env:

```bash
cd ~/Documents/jira-kb-changelog
cp .env.example .env
# edit .env: JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BASE_URL, GOOGLE_SHEET_URL
```

## Run

```bash
python3 jira_changelog.py
```

## Categories

No category column needed in the sheet. Matching order:

1. Jira Component  
2. Jira Label  
3. Keywords in summary/description (`category_map.json`)  
4. Else → **Needs review**

## After the run

1. Skim `output/changes-from-jira.md`.
2. Open the KB project (`workflow-config-pages`) in Cursor.
3. Ask Cursor to update support docs from that Markdown file, module by module.
4. Review, commit, and push **in the KB project**.

## Team reuse

Anyone with sheet access + a Jira API token can copy `.env.example` → `.env` and run the same command.
