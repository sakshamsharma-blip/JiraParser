#!/usr/bin/env python3
"""
Jira → categorized change doc (standalone tool).

1. Reads Jira ticket links/keys from a Google Sheet (CSV export).
2. Fetches each ticket from Jira Cloud.
3. Groups into KB stages via category_map.json.
4. Writes output/changes-from-jira.md and .json

Setup: copy .env.example → .env, then: python3 jira_changelog.py
"""

from __future__ import annotations

import base64
import csv
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
CATEGORY_MAP_PATH = ROOT / "category_map.json"
OUT_DIR = ROOT / "output"
OUT_MD = OUT_DIR / "changes-from-jira.md"
OUT_JSON = OUT_DIR / "changes-from-jira.json"

JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        print(f"Missing {path}")
        print("Copy .env.example → .env and fill in your values.")
        sys.exit(1)
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    required = ["JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_BASE_URL", "GOOGLE_SHEET_URL"]
    missing = [
        k
        for k in required
        if not env.get(k) or "REPLACE" in env.get(k, "") or "paste_token" in env.get(k, "")
    ]
    if missing:
        print(f"Please set these in .env: {', '.join(missing)}")
        sys.exit(1)
    env["JIRA_BASE_URL"] = env["JIRA_BASE_URL"].rstrip("/")
    return env


def sheet_csv_url(sheet_url: str) -> str:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not m:
        print("GOOGLE_SHEET_URL does not look like a Google Sheets link.")
        sys.exit(1)
    sheet_id = m.group(1)
    gid_match = re.search(r"[#&?]gid=(\d+)", sheet_url)
    gid = gid_match.group(1) if gid_match else "0"
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&gid={gid}"
    )


def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {e.code} for {url}\n{body}") from e


def fetch_sheet_rows(sheet_url: str) -> list[dict[str, str]]:
    csv_url = sheet_csv_url(sheet_url)
    print("Downloading sheet CSV…")
    raw = http_get(csv_url)
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(r) for r in reader]
    if not rows:
        print("Sheet downloaded but has no data rows.")
        sys.exit(1)
    print(f"  {len(rows)} row(s), columns: {list(rows[0].keys())}")
    return rows


def extract_keys_from_rows(rows: list[dict[str, str]]) -> list[str]:
    seen: set[str] = set()
    keys: list[str] = []
    for row in rows:
        blob = " ".join(str(v or "") for v in row.values())
        for key in JIRA_KEY_RE.findall(blob):
            if key not in seen:
                seen.add(key)
                keys.append(key)
    if not keys:
        print("No Jira keys found in the sheet (expected like PROJ-123 or /browse/PROJ-123).")
        sys.exit(1)
    print(f"Found {len(keys)} unique Jira key(s).")
    return keys


def jira_auth_header(email: str, token: str) -> str:
    raw = f"{email}:{token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def adf_to_text(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return " ".join(adf_to_text(n) for n in node)
    if not isinstance(node, dict):
        return str(node)
    parts: list[str] = []
    if node.get("type") == "text":
        parts.append(node.get("text") or "")
    if "content" in node:
        parts.append(adf_to_text(node["content"]))
    if node.get("type") in {"paragraph", "heading", "bulletList", "orderedList", "listItem"}:
        parts.append("\n")
    return re.sub(r"[ \t]+\n", "\n", "".join(parts)).strip()


def fetch_issue(base_url: str, auth: str, key: str) -> dict:
    fields = ",".join(
        [
            "summary",
            "description",
            "issuetype",
            "status",
            "components",
            "labels",
            "priority",
            "created",
            "updated",
            "resolutiondate",
            "parent",
            "fixVersions",
        ]
    )
    url = f"{base_url}/rest/api/3/issue/{urllib.parse.quote(key)}?fields={fields}"
    raw = http_get(url, headers={"Authorization": auth, "Accept": "application/json"})
    return json.loads(raw.decode("utf-8"))


def load_category_map() -> dict:
    return json.loads(CATEGORY_MAP_PATH.read_text(encoding="utf-8"))


def categorize(issue: dict, cmap: dict) -> tuple[str, str]:
    fields = issue.get("fields") or {}
    summary = (fields.get("summary") or "").lower()
    description = adf_to_text(fields.get("description")).lower()
    blob = f"{summary} {description}"

    components = [c.get("name", "") for c in (fields.get("components") or [])]
    for comp in components:
        mapped = cmap.get("component_map", {}).get(comp.lower().strip())
        if mapped:
            return mapped, f"component:{comp}"
        for needle, stage in cmap.get("component_map", {}).items():
            if needle in comp.lower():
                return stage, f"component:{comp}"

    labels = [lab.lower() for lab in (fields.get("labels") or [])]
    for lab in labels:
        mapped = cmap.get("label_map", {}).get(lab)
        if mapped:
            return mapped, f"label:{lab}"

    for stage, keywords in cmap.get("keyword_map", {}).items():
        for kw in keywords:
            if kw.lower() in blob:
                return stage, f"keyword:{kw}"

    return "Needs review", "no-match"


def normalize_issue(issue: dict, cmap: dict, base_url: str) -> dict:
    fields = issue.get("fields") or {}
    key = issue.get("key")
    stage, reason = categorize(issue, cmap)
    parent = fields.get("parent") or {}
    return {
        "key": key,
        "url": f"{base_url}/browse/{key}",
        "summary": fields.get("summary") or "",
        "description": adf_to_text(fields.get("description")),
        "type": ((fields.get("issuetype") or {}).get("name")) or "",
        "status": ((fields.get("status") or {}).get("name")) or "",
        "priority": ((fields.get("priority") or {}).get("name")) or "",
        "components": [c.get("name") for c in (fields.get("components") or [])],
        "labels": fields.get("labels") or [],
        "fixVersions": [v.get("name") for v in (fields.get("fixVersions") or [])],
        "parent_key": parent.get("key"),
        "parent_summary": (parent.get("fields") or {}).get("summary"),
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "resolved": fields.get("resolutiondate"),
        "category": stage,
        "category_reason": reason,
    }


def write_markdown(tickets: list[dict], cmap: dict) -> None:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for t in tickets:
        by_cat[t["category"]].append(t)

    stage_order = list(cmap.get("stages") or [])
    extras = sorted(c for c in by_cat if c not in stage_order)
    ordered = [c for c in stage_order if c in by_cat] + extras

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "# Product changes from Jira",
        "",
        f"_Generated {now} by `jira_changelog.py`._",
        "",
        f"**Total tickets:** {len(tickets)}",
        "",
        "## How to use this file",
        "",
        "1. Skim each category. Move anything in **Needs review** to the right stage.",
        "2. Open the Knowledge Base project (`workflow-config-pages`) in Cursor.",
        "3. Point Cursor at this file and ask it to update support docs module by module,",
        "   in clear support-facing language.",
        "4. Review the KB diffs, then commit/push in the KB project.",
        "",
        "## Category counts",
        "",
    ]
    for cat in ordered:
        lines.append(f"- **{cat}:** {len(by_cat[cat])}")
    lines.append("")

    for cat in ordered:
        lines.append(f"## {cat}")
        lines.append("")
        for t in by_cat[cat]:
            lines.append(f"### [{t['key']}]({t['url']}) — {t['summary']}")
            lines.append("")
            meta = [
                f"**Type:** {t['type'] or '—'}",
                f"**Status:** {t['status'] or '—'}",
                f"**Categorized by:** `{t['category_reason']}`",
            ]
            if t["components"]:
                meta.append(f"**Components:** {', '.join(t['components'])}")
            if t["labels"]:
                meta.append(f"**Labels:** {', '.join(t['labels'])}")
            if t["fixVersions"]:
                meta.append(f"**Fix versions:** {', '.join(t['fixVersions'])}")
            if t.get("parent_key"):
                meta.append(f"**Parent:** {t['parent_key']} — {t.get('parent_summary') or ''}")
            lines.append(" · ".join(meta))
            lines.append("")
            desc = (t.get("description") or "").strip()
            if desc:
                if len(desc) > 1200:
                    desc = desc[:1200].rstrip() + "…"
                lines.append("**Description (from Jira):**")
                lines.append("")
                lines.append(desc)
                lines.append("")
            lines.append(
                "**Support note (fill / refine in KB):** What changed for the user, "
                "where to find it, and any caveats."
            )
            lines.append("")
            lines.append("---")
            lines.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}")


def main() -> None:
    env = load_env(ENV_PATH)
    cmap = load_category_map()
    rows = fetch_sheet_rows(env["GOOGLE_SHEET_URL"])
    keys = extract_keys_from_rows(rows)
    auth = jira_auth_header(env["JIRA_EMAIL"], env["JIRA_API_TOKEN"])

    tickets: list[dict] = []
    failures: list[str] = []
    for i, key in enumerate(keys, 1):
        print(f"[{i}/{len(keys)}] {key}")
        try:
            issue = fetch_issue(env["JIRA_BASE_URL"], auth, key)
            tickets.append(normalize_issue(issue, cmap, env["JIRA_BASE_URL"]))
        except Exception as e:  # noqa: BLE001
            failures.append(f"{key}: {e}")
            print(f"  FAILED: {e}")
        time.sleep(0.15)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "ticket_count": len(tickets),
                "failures": failures,
                "tickets": tickets,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT_JSON}")

    write_markdown(tickets, cmap)

    needs = sum(1 for t in tickets if t["category"] == "Needs review")
    print("")
    print("Done.")
    print(f"  Fetched: {len(tickets)}")
    print(f"  Failed:  {len(failures)}")
    print(f"  Needs review (no category match): {needs}")
    if needs:
        print("  Tip: open output/changes-from-jira.md and/or tweak category_map.json")


if __name__ == "__main__":
    main()
