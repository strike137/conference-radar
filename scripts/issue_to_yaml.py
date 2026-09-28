#!/usr/bin/env python3
"""Turn the body of an "Add a conference" issue form into data/conferences/<id>.yml.

Reads the issue body from $ISSUE_BODY (or a file given as the first argument).
Writes id/name/path to $GITHUB_OUTPUT when it is set. Exits non-zero with a
readable message on bad input; the workflow posts that message on the issue.
"""
from __future__ import annotations

import datetime as dt
import os
import re
import sys
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "conferences"

# Issue form labels (see .github/ISSUE_TEMPLATE/add-conference.yml) -> keys.
LABELS = {
    "Short name": "name", "Full name": "full_name", "Official website": "website", "Areas": "areas",
    "Tier": "tier", "Type": "type", "Where it is usually held": "region", "Organizer": "organizer",
    "Run by (country of the organizing society or institution)": "organizer_country",
    "Proceedings": "proceedings", "CORE rank": "core", "CCF rank": "ccf", "Edition year": "year",
    "Conference dates": "dates", "Location": "location", "Deadlines": "deadlines", "Notes": "notes",
    "Acceptance rate": "acceptance_rate", "Registration fee": "fee", "Sources": "sources",
    "File id (optional)": "slug",
}
MULTILINE = {"deadlines", "notes", "sources"}
EMPTY = {"", "_No response_", "None", "Not sure", "Not listed or not sure"}
DATE = r"\d{4}-\d{2}-\d{2}"
TZ_NAMES = ["AoE", "UTC", "GMT", "JST", "KST", "CET", "CEST", "WET", "WEST", "EET", "EEST", "PST", "PDT",
            "MST", "MDT", "EST", "EDT", "IST", "SGT", "HKT", "AEST", "AEDT", "ICT", "WIB"]  # = TIMEZONES in build.py
TZ_CANON = {t.lower(): t for t in TZ_NAMES}
KIND_WORDS = [  # searched anywhere in the rest of the line, first match wins
    ("camera", "camera_ready"), ("final version", "camera_ready"), ("notification", "notification"),
    ("notify", "notification"), ("acceptance", "notification"), ("abstract", "abstract"),
    ("submission", "submission"), ("paper", "submission"), ("full", "submission"),
]
LEADING_KIND = re.compile(r"(?i)(abstract|submission|paper|notification|camera[_ -]?ready|camera|other)\b[\s:,-]*")
DEADLINE_RE = re.compile(
    rf"^(?P<date>{DATE})"
    r"(?:\s+(?P<time>\d{1,2}:\d{2}))?"
    r"(?:\s+\(?(?P<tz>(?:UTC|GMT)\s*[+-]\s*\d{1,2}(?::?\d{2})?|[A-Za-z]{2,4})\)?(?=\s|$))?"
    r"\s*(?P<rest>.*)$", re.IGNORECASE)


class FormError(Exception):
    pass


def parse_form(body: str) -> dict[str, str]:
    """Find each "### <label>" heading once, in form order, so text typed inside a textarea
    (even a copy of a heading) stays in its field."""
    body = body.replace("\r\n", "\n")
    found = []
    pos = 0
    for label in LABELS:  # dict order = form order
        m = re.compile(rf"^### {re.escape(label)}[ \t]*$", re.M).search(body, pos)
        if m:
            found.append((LABELS[label], m.start(), m.end()))
            pos = m.end()
    out: dict[str, str] = {}
    for i, (key, _, end) in enumerate(found):
        stop = found[i + 1][1] if i + 1 < len(found) else len(body)
        value = body[end:stop].strip()
        out[key] = "" if value in EMPTY else value
    return out


def lines(value: str) -> list[str]:
    """One item per line; strip a leading list marker ("- ", "* ", "+ ") and keep everything else."""
    out = [re.sub(r"^\s*[-*+]\s+", "", ln).strip() for ln in value.splitlines()]
    return [ln for ln in out if ln]


def slugify(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def valid_date(text: str) -> str:
    try:
        return dt.date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise FormError(f"'{text}' is not a valid date (use YYYY-MM-DD)") from exc


def parse_deadline(line: str) -> dict:
    m = DEADLINE_RE.match(line)
    if not m:
        raise FormError(f"cannot read the deadline line '{line}' (start it with YYYY-MM-DD)")
    rest = m["rest"].strip()
    tz = m["tz"]
    if tz and not re.match(r"(?i)(utc|gmt)\s*[+-]", tz) and tz.lower() not in TZ_CANON:
        rest = f"{tz} {rest}".strip()  # a word such as "Paper", not a time zone
        tz = None
    kind = "submission"
    for word, k in KIND_WORDS:
        if re.search(rf"\b{word}", rest.lower()):
            kind = k
            break
    lead = LEADING_KIND.match(rest)
    if lead:  # a leading kind keyword is not part of the label
        if lead.group(1).lower() == "other":
            kind = "other"
        rest = rest[lead.end():]
    d: dict = {"kind": kind, "date": valid_date(m["date"])}
    if m["time"]:
        hh, mm = (int(x) for x in m["time"].split(":"))
        if hh > 23 or mm > 59:
            raise FormError(f"'{m['time']}' in '{line}' is not a valid time (00:00 to 23:59)")
        d["time"] = f"{hh:02d}:{mm:02d}"
    if tz:
        tz = re.sub(r"\s+", "", tz)
        d["tz"] = TZ_CANON.get(tz.lower(), tz.upper())
    if rest.strip():
        d["label"] = rest.strip()
    return d


def build_record(form: dict[str, str], author: str | None) -> dict:
    for key in ("name", "full_name", "website"):
        if not form.get(key):
            raise FormError(f"'{key}' is required")
    for key, value in form.items():
        if key not in MULTILINE and "\n" in value:
            raise FormError(f"'{key}' must be a single line")
    if not re.match(r"^https?://[^\s/]+\S*$", form["website"]):
        raise FormError("'Official website' must be a web address starting with http:// or https://")
    cid = slugify(form.get("slug") or form["name"])
    if not cid:
        raise FormError("could not derive a file id from the short name; fill in 'File id' (letters, digits, '-')")
    rec: dict = {
        "id": cid, "name": form["name"], "full_name": form["full_name"],
        "type": form.get("type") or "conference", "tier": form.get("tier") or "minor",
        "areas": [a.strip() for a in (form.get("areas") or "").split(",") if a.strip()],
        "region": form.get("region") or "",
    }
    for key in ("organizer", "proceedings"):
        if form.get(key):
            rec[key] = form[key]
    if form.get("organizer_country"):
        rec["organizer_country"] = [x.strip() for x in form["organizer_country"].split(",") if x.strip()]
    rank = {}
    if form.get("core"):
        rank["core"] = form["core"]
    if form.get("ccf"):
        rank["ccf"] = form["ccf"]
    if rank:
        rec["rank"] = rank
    for key in ("acceptance_rate", "fee"):
        if form.get(key):
            rec[key] = form[key]
    rec["links"] = {"website": form["website"]}
    if form.get("notes"):
        rec["notes"] = lines(form["notes"])

    deadlines = [parse_deadline(ln) for ln in lines(form.get("deadlines") or "")]
    dates = re.findall(DATE, form.get("dates") or "")
    if form.get("dates") and len(dates) not in (1, 2):
        raise FormError("'Conference dates' must be one date, or two like 2027-02-03 to 2027-02-05")
    year = (form.get("year") or "").strip()
    if year or dates or deadlines or form.get("location"):
        if not year and dates:
            year = dates[0][:4]
        if not year.isdigit():
            raise FormError("'Edition year' must be a year like 2027")
        ed: dict = {"year": int(year)}
        if dates:
            ed["start"] = valid_date(dates[0])
            ed["end"] = valid_date(dates[-1])
            if ed["end"] < ed["start"]:
                raise FormError("the conference end date is before the start date")
        if form.get("location"):
            ed["location"] = form["location"]
        ed["deadlines"] = deadlines
        rec["editions"] = [ed]
    sources = [s for s in lines(form.get("sources") or "") if re.match(r"^https?://[^\s/]+", s)]
    rec["sources"] = sources or [form["website"]]
    rec["last_verified"] = dt.date.today().isoformat()
    if author:
        rec["added_by"] = author
    return rec


def write_outputs(values: dict[str, str]) -> None:
    """Write step outputs with random heredoc delimiters so no value can inject another output."""
    target = os.environ.get("GITHUB_OUTPUT")
    if not target:
        return
    with open(target, "a", encoding="utf-8") as fh:
        for key, value in values.items():
            delim = f"EOF_{uuid.uuid4().hex}"
            fh.write(f"{key}<<{delim}\n{value}\n{delim}\n")


def main() -> int:
    body = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else os.environ.get("ISSUE_BODY", "")
    try:
        rec = build_record(parse_form(body), os.environ.get("ISSUE_AUTHOR"))
        path = DATA / f"{rec['id']}.yml"
        if path.exists():
            raise FormError(f"`data/conferences/{rec['id']}.yml` already exists. "
                            "Use **Edit on GitHub** on the site, or put a different id in 'File id'.")
    except FormError as exc:
        print(f"error: {exc}", file=sys.stderr)
        write_outputs({"error": str(exc)})
        return 1
    text = yaml.safe_dump(rec, sort_keys=False, allow_unicode=True, width=120)
    path.write_text(text, encoding="utf-8")
    print(text)
    write_outputs({"id": rec["id"], "name": rec["name"], "path": str(path.relative_to(ROOT))})
    return 0


if __name__ == "__main__":
    sys.exit(main())
