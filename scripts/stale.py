#!/usr/bin/env python3
"""List conferences that need attention, most urgent first.

    python3 scripts/stale.py               table of the top 40
    python3 scripts/stale.py --limit 100
    python3 scripts/stale.py --json        machine-readable

Reasons:
  cfp-due     the next call for papers is expected (from the previous edition) within 45 days, or is
              already overdue, but no upcoming deadline is recorded
  deadline    an announced submission deadline falls within the next 30 days (re-check for extensions)
  unverified  last_verified is older than 120 days (or missing)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import Report, load_all  # noqa: E402

SUB = ("abstract", "submission")


def shift_years(iso: str, years: int) -> dt.date:
    d = dt.date.fromisoformat(iso)
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + years, day=28)


def assess(rec: dict, today: dt.date) -> list[dict]:
    items = []
    subs = [(dt.date.fromisoformat(d["date"]), d, e) for e in rec["editions"] for d in e["deadlines"] if d["kind"] in SUB]
    upcoming = sorted((x for x in subs if x[0] >= today - dt.timedelta(days=1)), key=lambda x: x[0])
    for day, d, e in upcoming:
        if day <= today + dt.timedelta(days=30):
            items.append({"reason": "deadline", "when": day.isoformat(), "score": (day - today).days,
                          "detail": f"{e['year']} {d['kind']} {d.get('label') or ''}".strip()})
            break
    if not upcoming and subs:
        step = 2 if rec.get("frequency") == "biennial" else 1
        last_ed = max((x[2] for x in subs), key=lambda e: e["year"] or 0)
        first = min(dt.date.fromisoformat(d["date"]) for d in last_ed["deadlines"] if d["kind"] in SUB)
        expected = shift_years(first.isoformat(), step)
        while expected < today - dt.timedelta(days=330):
            expected = shift_years(expected.isoformat(), step)
        if expected <= today + dt.timedelta(days=45):
            items.append({"reason": "cfp-due", "when": expected.isoformat(), "score": (expected - today).days - 60,
                          "detail": f"expected from the {last_ed['year']} edition; no upcoming deadline recorded"})
    elif not subs and rec["typical"]["deadline_months"]:
        months = rec["typical"]["deadline_months"]
        near = [m for m in months if 0 <= (m - today.month) % 12 <= 1]
        if near:
            items.append({"reason": "cfp-due", "when": f"~month {near[0]}", "score": -20,
                          "detail": "usual deadline month is now or next month; no editions recorded"})
    lv = rec.get("last_verified")
    age = (today - dt.date.fromisoformat(lv)).days if lv else 9999
    if age > 120:
        items.append({"reason": "unverified", "when": lv or "never", "score": 1000 - min(age, 999),
                      "detail": f"last verified {age} days ago" if lv else "never verified"})
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today)")
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    rep = Report()
    records = load_all(rep)
    if rep.errors:
        print("fix validation errors first (python3 scripts/build.py --check)", file=sys.stderr)
        return 1
    rows = []
    for rec in records:
        for it in assess(rec, today):
            rows.append({"id": rec["id"], "name": rec["name"], "file": f"data/conferences/{rec['id']}.yml",
                         "website": rec["links"].get("website"), **it})
    rows.sort(key=lambda r: (r["score"], r["id"]))
    rows = rows[: args.limit]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    print(f"{len(rows)} items (today {today})")
    for r in rows:
        print(f"{r['reason']:10}  {r['when']:<11}  {r['id']:<20} {r['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
