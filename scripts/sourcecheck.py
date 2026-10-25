#!/usr/bin/env python3
"""Check that dates written into a conference file appear on the pages it cites.

    python3 scripts/sourcecheck.py data/conferences/acsac.yml           every date in the file
    python3 scripts/sourcecheck.py --base origin/main                    only dates added or changed since a git revision
    python3 scripts/sourcecheck.py --base HEAD data/conferences/x.yml    the same, for some files

A date counts as confirmed when it appears, in any common spelling (2026-05-26, May 26 2026, 26 May,
26.05.2026, 2026年5月26日, ...), on one of the pages the file lists: the edition url, links.website or
sources. The weekly update discards a changed file when one of its new dates is not confirmed. With
--core it also checks rank.core against the ICORE2026 export of the CORE portal.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import io
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
CORE_EXPORT = ("https://portal.core.edu.au/conf-ranks/?search=&by=all&source=ICORE2026&sort=arank&page=1"
               "&do=Export")
MAX_PAGES = 12
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
ABBR = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

_pages: dict[str, str | None] = {}


def fetch(url: str, timeout: int = 25) -> str | None:
    """Page text with tags removed (scripts kept, since some sites carry their dates in JSON), or None."""
    if url in _pages:
        return _pages[url]
    text = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,ja;q=0.8,ko;q=0.6"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(4_000_000)
            ctype = resp.headers.get("Content-Type", "")
        if "pdf" in ctype or raw[:5] == b"%PDF-":
            if shutil.which("pdftotext"):
                out = subprocess.run(["pdftotext", "-layout", "-", "-"], input=raw, capture_output=True, timeout=60)
                text = out.stdout.decode("utf-8", "replace")
        else:
            m = re.search(r"charset=([\w-]+)", ctype) or re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', raw[:4000])
            enc = m.group(1) if m else "utf-8"
            enc = enc.decode() if isinstance(enc, bytes) else enc
            try:
                page = raw.decode(enc, "replace")
            except LookupError:
                page = raw.decode("utf-8", "replace")
            text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    except Exception:  # unreachable, TLS problem, timeout: the date simply stays unconfirmed
        text = None
    if text is not None:
        text = re.sub(r"\s+", " ", text.replace(" ", " ")).lower()
    _pages[url] = text
    return text


def date_patterns(d: dt.date) -> tuple[list[re.Pattern], list[re.Pattern]]:
    """Patterns that contain the year, and patterns without it (accepted only if the page mentions the year)."""
    y, m, day = d.year, d.month, d.day
    dd, mm = f"{day:02d}", f"{m:02d}"
    num = [f"{y}-{mm}-{dd}", f"{y}/{mm}/{dd}", f"{y}/{m}/{day}", f"{y}.{mm}.{dd}", f"{y}.{m}.{day}",
           f"{dd}.{mm}.{y}", f"{day}.{m}.{y}", f"{dd}/{mm}/{y}", f"{day}/{m}/{y}", f"{mm}/{dd}/{y}", f"{m}/{day}/{y}",
           f"{dd}-{mm}-{y}", f"{y}-{m}-{day}", f"{y}年{m}月{day}日", f"{y}年{mm}月{dd}日", f"{y}년 {m}월 {day}일",
           f"{y}. {m}. {day}"]
    with_year = [re.compile(r"(?<![\d])" + re.escape(s) + r"(?![\d])") for s in num]
    names = [MONTHS[m - 1], ABBR[m - 1]] + (["sept"] if m == 9 else [])
    mon = "(?:" + "|".join(names) + r")\.?"
    day_re = rf"0?{day}(?:st|nd|rd|th)?"
    to = r"\s*(?:-|~|\u2013|\u2014|to)\s*"
    without = [
        re.compile(rf"\b{mon}\s+{day_re}(?![\d])"),                                  # May 26, May 26th, May 26-28
        re.compile(rf"(?<![\d]){day_re}[\s-]+(?:of\s+)?{mon}\b"),                   # 26 May, 26th of May, 26-May
        re.compile(rf"(?<![\d]){day_re}{to}\d{{1,2}}(?:st|nd|rd|th)?,?\s+{mon}\b"),  # 26-28 May, 15-17, December
        re.compile(rf"(?<![\d]){m}月\s*{day}日"), re.compile(rf"(?<![\d]){m}월\s*{day}일"),
    ]
    return with_year, without


def page_has(text: str, d: dt.date) -> bool:
    with_year, without = date_patterns(d)
    if any(p.search(text) for p in with_year):
        return True
    return str(d.year) in text and any(p.search(text) for p in without)


def as_date(v) -> dt.date | None:
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v))
    except ValueError:
        return None


def dated_items(doc: dict) -> list[tuple[str, dt.date, str | None]]:
    """(what, date, edition url) for every deadline and edition start in a file."""
    out = []
    for ed in doc.get("editions") or []:
        if not isinstance(ed, dict):
            continue
        year, url = ed.get("year"), ed.get("url")
        start = as_date(ed.get("start"))
        if start:
            out.append((f"{year} start", start, url))
        for dl in ed.get("deadlines") or []:
            if isinstance(dl, dict) and as_date(dl.get("date")):
                what = f"{year} {dl.get('kind') or 'submission'}" + (f" ({dl['label']})" if dl.get("label") else "")
                out.append((what, as_date(dl["date"]), url))
    return out


def pages_for(doc: dict, edition_url: str | None) -> list[str]:
    urls = [edition_url, (doc.get("links") or {}).get("website")] + list(doc.get("sources") or [])
    seen, out = set(), []
    for u in urls:
        if isinstance(u, str) and u.startswith("http") and u not in seen:
            seen.add(u)
            out.append(u)
    return out[:MAX_PAGES]


def load_rev(rev: str, rel: str) -> dict | None:
    out = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        return None
    try:
        return yaml.safe_load(out.stdout) or {}
    except yaml.YAMLError:
        return None


def new_items(old: dict | None, new: dict) -> list[tuple[str, dt.date, str | None]]:
    """Items whose date is new for its edition year (added or changed since `old`)."""
    items = dated_items(new)
    if not old:
        return items
    before = {(w.split(" ")[0], d) for w, d, _ in dated_items(old)}
    return [(w, d, u) for w, d, u in items if (w.split(" ")[0], d) not in before]


def check_doc(new: dict, old: dict | None = None) -> dict:
    """{'confirmed': [...], 'missing': [...]} for the dates that are new in `new`."""
    res = {"confirmed": [], "missing": []}
    for what, d, url in new_items(old, new):
        found = None
        for page in pages_for(new, url):
            text = fetch(page)
            if text and page_has(text, d):
                found = page
                break
        (res["confirmed"] if found else res["missing"]).append(f"{what} {d.isoformat()}" + (f" <- {found}" if found else ""))
    return res


_core: list[dict] | None = None


def core_rows() -> list[dict] | None:
    global _core
    if _core is None:
        try:
            req = urllib.request.Request(CORE_EXPORT, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8", "replace")
            # id, title, acronym, source, rank, primary, FoR codes
            _core = [{"title": r[1], "acronym": r[2], "rank": rank_label(r[4])}
                     for r in csv.reader(io.StringIO(body)) if len(r) >= 5]
        except Exception:
            _core = []
    return _core or None


def norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def rank_label(s) -> str:
    return re.sub(r":\s*", ": ", str(s or "").strip())  # the export has both "National:India" and "National: India"


def check_core(doc: dict) -> tuple[str, str] | None:
    """None when rank.core is absent, Unranked or matches ICORE2026. Otherwise ("error", why) when ICORE2026
    lists the venue with another rank, or ("warn", why) when the venue cannot be found by acronym or title."""
    rank = rank_label((doc.get("rank") or {}).get("core"))
    if not rank or rank == "Unranked" or (doc.get("rank") or {}).get("core_source"):
        return None
    rows = core_rows()
    if rows is None:
        return None  # export unreachable: do not block on it
    name = str(doc.get("name") or "")
    names = {norm(name), norm(re.sub(r"^(IEEE|ACM|IFIP|USENIX)\s+", "", name))}
    names |= {norm(p) for p in re.split(r"[/+&()-]", name) if len(norm(p)) >= 3}
    title = norm(doc.get("full_name"))
    hits = [r for r in rows if norm(r["acronym"]) in names or (title and norm(r["title"]) == title)]
    if not hits:
        return ("warn", f"rank.core {rank}, but {name} is not found in the ICORE2026 export")
    if not any(norm(r["rank"]) == norm(rank) for r in hits):
        return ("error", f"rank.core {rank}, but ICORE2026 lists {', '.join(sorted({r['rank'] for r in hits}))}")
    return None


def changed_files(base: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", base, "--", "data/conferences"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    out += subprocess.run(["git", "ls-files", "-o", "--exclude-standard", "data/conferences"], cwd=ROOT,
                          capture_output=True, text=True).stdout.split()
    return sorted({f for f in out if f.endswith(".yml") and (ROOT / f).exists()})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--base", help="only check dates added or changed since this git revision")
    ap.add_argument("--core", action="store_true", help="also check rank.core against ICORE2026")
    args = ap.parse_args()
    files = args.files or (changed_files(args.base) if args.base else [])
    if not files:
        print("nothing to check")
        return 0
    bad = 0
    for f in files:
        rel = str(Path(f).resolve().relative_to(ROOT))
        new = yaml.safe_load((ROOT / rel).read_text(encoding="utf-8")) or {}
        old = load_rev(args.base, rel) if args.base else None
        res = check_doc(new, old)
        core = check_core(new) if args.core else None
        status = "ok" if not res["missing"] and not (core and core[0] == "error") else "FAIL"
        bad += status == "FAIL"
        print(f"{status}  {rel}  ({len(res['confirmed'])} confirmed, {len(res['missing'])} missing)")
        for m in res["missing"]:
            print(f"      missing: {m}")
        if core:
            print(f"      {core[0]}: {core[1]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
