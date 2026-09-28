#!/usr/bin/env python3
"""Validate data/conferences/*.yml and build the static site into _site/.

    python3 scripts/build.py              validate and build _site/
    python3 scripts/build.py --check      validate only (used on pull requests)
    python3 scripts/build.py --serve      build, then serve on http://localhost:8000

Needs PyYAML (pip install pyyaml).
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import http.server
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "conferences"
SITE = ROOT / "site"

AREAS = ["security", "crypto", "ai", "nlp", "data", "vision", "networking",
         "communications", "systems", "software", "general"]
TIERS = ["top", "major", "minor", "domestic"]
TYPES = ["conference", "workshop", "industry"]
REGIONS = ["japan", "korea", "taiwan", "china", "southeast-asia", "south-asia", "asia-pacific",
           "oceania", "europe", "north-america", "latin-america", "middle-east", "africa",
           "worldwide", "online"]
LANGUAGES = ["english", "japanese", "korean", "chinese", "mixed"]
ORG_COUNTRIES = ["japan", "korea", "taiwan", "china", "singapore", "india", "vietnam", "thailand", "indonesia",
                 "malaysia", "philippines", "australia", "new-zealand", "usa", "canada", "europe", "international",
                 "other"]
FREQUENCIES = ["annual", "biennial", "multiple-per-year", "irregular"]
CORE_RANKS = ["A*", "A", "B", "C", "National", "Regional", "Unranked"]
# Other ICORE2026 values: "National: USA", "National/Regional", "Australasian C", "Journal Published", "Multiconference".
NATIONAL_RE = re.compile(
    r"^((National|Regional)(: [A-Za-z ,]+)?|National/Regional|Australasian [ABC]|Journal Published|Multiconference)$")
CCF_RANKS = ["A", "B", "C"]
DEADLINE_KINDS = ["abstract", "submission", "notification", "camera_ready", "other"]
STATUSES = ["confirmed", "tentative"]
# Must match TZ in site/app.js.
TIMEZONES = ["AoE", "UTC", "GMT", "JST", "KST", "CET", "CEST", "WET", "WEST", "EET", "EEST",
             "PST", "PDT", "MST", "MDT", "EST", "EDT", "IST", "SGT", "HKT",
             "AEST", "AEDT", "ICT", "WIB"]
TZ_OFFSET = re.compile(r"^(UTC|GMT)\s*[+-]\s*\d{1,2}(:?\d{2})?$")

TOP_KEYS = {"id", "name", "full_name", "name_local", "type", "tier", "areas", "region", "organizer_country",
            "language", "frequency", "organizer", "proceedings", "archival", "indexing",
            "rank", "acceptance_rate", "fee", "typical", "links", "notes", "editions",
            "sources", "last_verified", "unverified", "added_by"}
EDITION_KEYS = {"year", "label", "start", "end", "location", "url", "status", "deadlines"}
DEADLINE_KEYS = {"kind", "date", "time", "tz", "label"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate keys instead of silently keeping the last one."""

    def construct_mapping(self, node, deep=False):
        seen: dict = {}
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key '{key}' (first used on line {seen[key] + 1})", key_node.start_mark)
            seen[key] = key_node.start_mark.line
        return super().construct_mapping(node, deep=deep)


def as_date(value, where: str, rep: Report, allow_datetime: bool = True) -> str | None:
    """Accept a YAML date or a YYYY-MM-DD string, return the ISO string."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        if not allow_datetime:
            rep.error(where, "write the date and the time separately, e.g. date: 2026-10-02, "
                             'time: "12:00", tz: UTC+9')
            return None
        rep.warn(where, "has a time of day; only the date is used")
        value = value.date()
    if isinstance(value, dt.date):
        return value.isoformat()
    try:
        return dt.date.fromisoformat(str(value).strip()).isoformat()
    except ValueError:
        rep.error(where, f"'{value}' is not a date (use YYYY-MM-DD)")
        return None


def str_list(value, where: str, rep: Report) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        rep.error(where, "must be a list (start each item with '- ')")
        return []
    out = []
    for i, v in enumerate(value):
        if v is None or not str(v).strip():
            continue
        if isinstance(v, (dict, list)):
            text = ", ".join(f"{k}: {x}" for k, x in v.items()) if isinstance(v, dict) else str(v)
            rep.error(where, f"item {i + 1} is not plain text; put it in quotes: - \"{text}\"")
            continue
        out.append(str(v))
    return out


def url_ok(value) -> bool:
    if not isinstance(value, str) or any(ch.isspace() for ch in value.strip()):
        return False
    parts = urlsplit(value.strip())
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def month_list(value, where: str, rep: Report) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int) and not isinstance(value, bool):
        value = [value]
    if not isinstance(value, list):
        rep.error(where, "must be a list of month numbers, e.g. [7] or [6, 7]")
        return []
    out = []
    for v in value:
        if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 12:
            out.append(v)
        else:
            rep.error(where, f"'{v}' is not a month number 1-12")
    return sorted(set(out))


def check_enum(value, allowed: list[str], where: str, rep: Report, required=False) -> str | None:
    if value is None or value == "":
        if required:
            rep.error(where, f"is required (one of: {', '.join(allowed)})")
        return None
    if not isinstance(value, str):
        hint = " (YAML read it as a boolean; put it in quotes)" if isinstance(value, bool) else ""
        rep.error(where, f"'{value}' is not one of: {', '.join(allowed)}{hint}")
        return None
    if value not in allowed:
        rep.error(where, f"'{value}' is not one of: {', '.join(allowed)}")
        return None
    return value


def mapping(value, where: str, rep: Report, keys: set[str]) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        rep.error(where, f"must be a mapping with: {', '.join(sorted(keys))}")
        return {}
    for key in value:
        if key not in keys:
            rep.warn(where, f"unknown field '{key}' (typo?)")
    return value


def as_list(value, where: str, rep: Report) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        rep.error(where, "must be a list (start each item with '- ')")
        return []
    return value


def validate(path: Path, doc, rep: Report) -> dict | None:
    where = str(path.relative_to(ROOT))
    if not isinstance(doc, dict):
        rep.error(where, "file must contain a YAML mapping")
        return None

    for key in doc:
        if key not in TOP_KEYS:
            rep.warn(where, f"unknown field '{key}' (typo?)")

    cid = str(doc.get("id") or "")
    if not ID_RE.match(cid):
        rep.error(where, "id must be lowercase letters, digits and '-'")
    elif cid != path.stem:
        rep.error(where, f"id '{cid}' must match the file name '{path.name}'")

    for key in ("name", "full_name"):
        if not str(doc.get(key) or "").strip():
            rep.error(where, f"'{key}' is required")

    rec: dict = {
        "id": cid,
        "name": str(doc.get("name") or "").strip(),
        "full_name": str(doc.get("full_name") or "").strip(),
        "name_local": str(doc.get("name_local") or "").strip() or None,
        "type": check_enum(doc.get("type"), TYPES, f"{where} type", rep, required=True),
        "tier": check_enum(doc.get("tier"), TIERS, f"{where} tier", rep, required=True),
        "region": check_enum(doc.get("region"), REGIONS, f"{where} region", rep, required=True),
        "language": check_enum(doc.get("language"), LANGUAGES, f"{where} language", rep),
        "frequency": check_enum(doc.get("frequency"), FREQUENCIES, f"{where} frequency", rep),
        "organizer": str(doc["organizer"]) if doc.get("organizer") else None,
        "proceedings": str(doc["proceedings"]) if doc.get("proceedings") else None,
        "archival": doc.get("archival"),
        "indexing": str_list(doc.get("indexing"), f"{where} indexing", rep),
        "acceptance_rate": str(doc["acceptance_rate"]) if doc.get("acceptance_rate") else None,
        "fee": str(doc["fee"]) if doc.get("fee") else None,
        "notes": str_list(doc.get("notes"), f"{where} notes", rep),
        "sources": str_list(doc.get("sources"), f"{where} sources", rep),
        "unverified": str_list(doc.get("unverified"), f"{where} unverified", rep),
        "last_verified": as_date(doc.get("last_verified"), f"{where} last_verified", rep),
        "added_by": str(doc["added_by"]) if doc.get("added_by") else None,
    }
    if rec["archival"] is not None and not isinstance(rec["archival"], bool):
        rep.error(f"{where} archival", "must be true or false")
        rec["archival"] = None
    for s in rec["sources"]:
        if not url_ok(s.split(" ", 1)[0]):
            rep.error(f"{where} sources", f"'{s}' is not a web address (http:// or https://)")

    areas = str_list(doc.get("areas"), f"{where} areas", rep)
    if not areas:
        rep.error(f"{where} areas", f"at least one of: {', '.join(AREAS)}")
    for a in areas:
        check_enum(a, AREAS, f"{where} areas", rep)
    rec["areas"] = [a for a in areas if a in AREAS]

    org = str_list(doc.get("organizer_country"), f"{where} organizer_country", rep)
    for o in org:
        check_enum(o, ORG_COUNTRIES, f"{where} organizer_country", rep)
    rec["organizer_country"] = [o for o in dict.fromkeys(org) if o in ORG_COUNTRIES]

    rank = mapping(doc.get("rank"), f"{where} rank", rep, {"core", "core_source", "ccf"})
    core = rank.get("core")
    rec["rank"] = {
        "core": core if isinstance(core, str) and NATIONAL_RE.match(core)
        else check_enum(core, CORE_RANKS, f"{where} rank.core", rep),
        "core_source": str(rank["core_source"]) if rank.get("core_source") else None,
        "ccf": check_enum(rank.get("ccf"), CCF_RANKS, f"{where} rank.ccf", rep),
    }

    typical = mapping(doc.get("typical"), f"{where} typical", rep, {"deadline_months", "conference_months"})
    rec["typical"] = {
        "deadline_months": month_list(typical.get("deadline_months"), f"{where} typical.deadline_months", rep),
        "conference_months": month_list(typical.get("conference_months"), f"{where} typical.conference_months", rep),
    }

    links = mapping(doc.get("links"), f"{where} links", rep, {"website", "dblp", "wikicfp"})
    rec["links"] = {k: str(v).strip() for k, v in links.items() if v}
    for k, v in rec["links"].items():
        if not url_ok(v):
            rep.error(f"{where} links.{k}", f"'{v}' is not a web address (http:// or https://)")

    editions = []
    for i, ed in enumerate(as_list(doc.get("editions"), f"{where} editions", rep)):
        ew = f"{where} editions[{i}]"
        if not isinstance(ed, dict):
            rep.error(ew, "must be a mapping")
            continue
        for key in ed:
            if key not in EDITION_KEYS:
                rep.warn(ew, f"unknown field '{key}'")
        year = ed.get("year")
        if not isinstance(year, int) or isinstance(year, bool) or not 1990 <= year <= 2100:
            rep.error(ew, "year must be a number like 2026")
            year = None
        e = {
            "year": year,
            "label": str(ed["label"]) if ed.get("label") else None,
            "start": as_date(ed.get("start"), f"{ew} start", rep),
            "end": as_date(ed.get("end"), f"{ew} end", rep),
            "location": str(ed["location"]) if ed.get("location") else None,
            "url": str(ed["url"]).strip() if ed.get("url") else None,
            "status": check_enum(ed.get("status") or "confirmed", STATUSES, f"{ew} status", rep),
            "deadlines": [],
        }
        if e["url"] and not url_ok(e["url"]):
            rep.error(f"{ew} url", f"'{e['url']}' is not a web address (http:// or https://)")
            e["url"] = None
        if e["start"] and not e["end"]:
            e["end"] = e["start"]
        if e["start"] and e["end"] and e["end"] < e["start"]:
            rep.error(ew, f"end {e['end']} is before start {e['start']}")
        if e["start"] and year and abs(int(e["start"][:4]) - year) > 1:
            rep.warn(ew, f"start {e['start']} does not match year {year}")
        for j, d in enumerate(as_list(ed.get("deadlines"), f"{ew} deadlines", rep)):
            dw = f"{ew} deadlines[{j}]"
            if not isinstance(d, dict):
                rep.error(dw, "must be a mapping with kind and date")
                continue
            for key in d:
                if key not in DEADLINE_KEYS:
                    rep.warn(dw, f"unknown field '{key}'")
            date = as_date(d.get("date"), f"{dw} date", rep, allow_datetime=False)
            if not date:
                if d.get("date") in (None, ""):
                    rep.error(dw, "date is required")
                continue
            time = d.get("time")
            if isinstance(time, int) and not isinstance(time, bool):
                # YAML 1.1 reads an unquoted 23:59 as the number 1439.
                if 0 <= time < 1440:
                    time = f"{time // 60:02d}:{time % 60:02d}"
                else:
                    rep.error(dw, 'time must be quoted, e.g. time: "23:59"')
                    time = None
            if time is not None and not TIME_RE.match(str(time)):
                rep.error(dw, f"time '{time}' must be HH:MM, quoted, e.g. \"23:59\"")
                time = None
            tz = d.get("tz")
            if tz is not None and not isinstance(tz, str):
                rep.error(dw, f"tz '{tz}' must be text; write an offset as \"UTC+9\" (quoted)")
                tz = None
            elif tz is not None and tz not in TIMEZONES and not TZ_OFFSET.match(tz):
                rep.error(dw, f"tz '{tz}' is unknown; use AoE, UTC, UTC+9, JST, ...")
                tz = None
            if time and not tz:
                rep.warn(dw, "time is set without tz; the site assumes AoE, add tz if the CFP states one")
            kind = check_enum(d.get("kind") or "submission", DEADLINE_KINDS, f"{dw} kind", rep)
            e["deadlines"].append({
                "kind": kind,
                "date": date,
                "time": str(time) if time else None,
                "tz": tz or None,
                "label": str(d["label"]) if d.get("label") else None,
            })
            if e["end"] and date > e["end"] and kind in ("abstract", "submission"):
                rep.warn(dw, f"submission deadline {date} is after the event ends")
        e["deadlines"].sort(key=lambda d: d["date"])
        editions.append(e)
    editions.sort(key=lambda e: (e["year"] or 0, e["start"] or ""))
    rec["editions"] = editions
    return rec


def load_config() -> dict:
    cfg = yaml.safe_load((ROOT / "config.yml").read_text(encoding="utf-8")) or {}
    if os.environ.get("GITHUB_REPOSITORY"):
        cfg["repo"] = os.environ["GITHUB_REPOSITORY"]
    return cfg


def load_all(rep: Report) -> list[dict]:
    records = []
    names: dict[str, str] = {}
    ids: dict[str, str] = {}
    for path in sorted(DATA.iterdir()):
        rel = str(path.relative_to(ROOT))
        if path.name.startswith(".") or path.is_dir():
            continue
        if path.suffix != ".yml":
            rep.error(rel, f"only .yml files are read; rename it to {path.stem}.yml")
            continue
        try:
            doc = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
        except (yaml.YAMLError, ValueError, UnicodeDecodeError) as exc:
            # ValueError: an impossible unquoted date such as 2026-09-31.
            hint = " (an impossible date such as 2026-09-31?)" if isinstance(exc, ValueError) and not isinstance(exc, yaml.YAMLError) else ""
            rep.error(rel, f"cannot read the file{hint}: {exc}")
            continue
        try:
            rec = validate(path, doc, rep)
        except Exception as exc:  # keep going and name the file
            rep.error(rel, f"unexpected problem ({type(exc).__name__}: {exc}); check the file's structure")
            continue
        if not rec:
            continue
        if rec["id"] in ids:
            rep.error(rel, f"id '{rec['id']}' is already used by {ids[rec['id']]}")
            continue
        ids[rec["id"]] = path.name
        key = f'{rec["name"]}|{rec["full_name"]}'.lower()
        if rec["name"] and key in names:
            rep.warn(rel, f"same name and full name as {names[key]} (duplicate?)")
        names[key] = path.name
        records.append(rec)
    return records


def build(out: Path, records: list[dict], cfg: dict) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    meta = {
        "title": cfg.get("title", "Conference Radar"),
        "subtitle": cfg.get("subtitle", ""),
        "repo": cfg.get("repo", ""),
        "branch": cfg.get("branch", "main"),
        "core_edition": cfg.get("core_edition", "ICORE2026"),
        "ccf_edition": cfg.get("ccf_edition", "CCF"),
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(records),
    }
    payload = {"meta": meta, "conferences": records}
    (out / "conferences.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate only")
    ap.add_argument("--out", default=str(ROOT / "_site"), help="output directory (default _site/)")
    ap.add_argument("--serve", action="store_true", help="serve the built site")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    rep = Report()
    records = load_all(rep)
    for w in rep.warnings:
        print(f"warning: {w}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning::{w}")
    for e in rep.errors:
        print(f"error: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error::{e}")
    print(f"{len(records)} conferences, {len(rep.errors)} errors, {len(rep.warnings)} warnings")
    if rep.errors:
        return 1
    if args.check:
        return 0

    out = Path(args.out).resolve()
    build(out, records, load_config())
    print(f"built {out}")
    if args.serve:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
        print(f"serving on http://localhost:{args.port}  (Ctrl+C to stop)")
        with http.server.ThreadingHTTPServer(("", args.port), handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
