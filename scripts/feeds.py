#!/usr/bin/env python3
"""Compare the data with public deadline feeds and add editions that the official site confirms.

    python3 scripts/feeds.py                    report what the feeds know that the data does not
    python3 scripts/feeds.py --apply            also add new editions whose dates the official page confirms
    python3 scripts/feeds.py --hints out.json   write the rest as hints for the weekly update

Feeds: ccfddl/ccf-deadlines (MIT) and sec-deadlines. They are hints only: an edition is added only when
every deadline it carries appears on the official page (see sourcecheck.py). The feed's own data is not
copied into this repository; the official page is what gets cited.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import DATA, Report, validate  # noqa: E402
import sourcecheck as sc  # noqa: E402

CCFDDL = "https://codeload.github.com/ccfddl/ccf-deadlines/tar.gz/refs/heads/main"
SECDL = "https://raw.githubusercontent.com/sec-deadlines/sec-deadlines.github.io/master/_data/conferences.yml"
DBLP_RE = re.compile(r"dblp\.org/(?:db|streams)/conf/([^/#?]+)")
MONTH = {m: i + 1 for i, m in enumerate(sc.MONTHS)} | {m: i + 1 for i, m in enumerate(sc.ABBR)} | {"sept": 9}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": sc.UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def tz_of(zone: str | None) -> str | None:
    z = (zone or "").strip()
    if z in ("AoE", "UTC-12", "Etc/GMT+12"):
        return "AoE"
    if z in ("UTC", "UTC+0", "UTC-0", "GMT", "Etc/UTC", "Etc/GMT"):
        return "UTC"
    m = re.fullmatch(r"UTC([+-]\d{1,2})", z)
    return f"UTC{m.group(1)}" if m else None  # PT and the like are ambiguous; leave the zone out


def parse_when(text: str | None, year: int) -> tuple[str | None, str | None]:
    """Start and end from strings such as 'December 8-10, 2026', 'Nov 30 - Dec 4, 2026', '8-10 December 2026'."""
    t = re.sub(r"\s+", " ", str(text or "").lower().replace("\u2013", "-").replace("\u2014", "-")).strip()
    y = re.search(r"(20\d\d)", t)
    yy = int(y.group(1)) if y else year
    mon = r"(" + "|".join(sorted(MONTH, key=len, reverse=True)) + r")\.?"
    pats = [
        (rf"{mon} (\d{{1,2}}) ?- ?{mon} (\d{{1,2}})", lambda g: ((g[0], g[1]), (g[2], g[3]))),
        (rf"{mon} (\d{{1,2}}) ?- ?(\d{{1,2}})", lambda g: ((g[0], g[1]), (g[0], g[2]))),
        (rf"(\d{{1,2}}) ?- ?(\d{{1,2}}),? {mon}", lambda g: ((g[2], g[0]), (g[2], g[1]))),
        (rf"(\d{{1,2}}) {mon} ?- ?(\d{{1,2}}) {mon}", lambda g: ((g[1], g[0]), (g[3], g[2]))),
        (rf"{mon} (\d{{1,2}})\b", lambda g: ((g[0], g[1]), (g[0], g[1]))),
    ]
    for pat, pick in pats:
        m = re.search(pat, t)
        if m:
            (m1, d1), (m2, d2) = pick(m.groups())
            try:
                start = dt.date(yy, MONTH[m1], int(d1))
                end = dt.date(yy + (MONTH[m2] < MONTH[m1]), MONTH[m2], int(d2))
                return start.isoformat(), end.isoformat()
            except ValueError:
                return None, None
    return None, None


def deadline(kind: str, raw, tz: str | None, label: str | None) -> dict | None:
    m = re.match(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?", str(raw or ""))
    if not m:
        return None  # TBD
    out = {"kind": kind, "date": m.group(1)}
    if m.group(2) and tz:
        out |= {"time": m.group(2), "tz": tz}
    if label:
        out["label"] = str(label).strip()[:80]
    return out


def load_ccfddl() -> list[dict]:
    items = []
    with tarfile.open(fileobj=io.BytesIO(get(CCFDDL))) as tar:
        for mem in tar.getmembers():
            if "/conference/" not in mem.name or not mem.name.endswith(".yml") or mem.name.endswith("types.yml"):
                continue
            for conf in yaml.safe_load(tar.extractfile(mem).read()) or []:
                for ed in conf.get("confs") or []:
                    tz = tz_of(ed.get("timezone"))
                    dls = []
                    for t in ed.get("timeline") or []:
                        label = t.get("comment")
                        dls += [d for d in (deadline("abstract", t.get("abstract_deadline"), tz, label),
                                            deadline("submission", t.get("deadline"), tz, label)) if d]
                    start, end = parse_when(ed.get("date"), ed.get("year") or 0)
                    items.append({"feed": "ccfddl", "dblp": str(conf.get("dblp") or ""), "name": conf.get("title"),
                                  "full_name": conf.get("description"), "year": ed.get("year"), "url": ed.get("link"),
                                  "location": ed.get("place"), "start": start, "end": end, "deadlines": dls})
    return items


def load_secdl() -> list[dict]:
    items = []
    for ed in yaml.safe_load(get(SECDL)) or []:
        key = DBLP_RE.search(str(ed.get("dblp") or ""))
        raw = ed.get("deadline") or []
        raw = raw if isinstance(raw, list) else [raw]
        start, end = parse_when(f"{ed.get('date') or ''} {ed.get('year') or ''}", ed.get("year") or 0)
        items.append({"feed": "sec-deadlines", "dblp": key.group(1) if key else "", "name": ed.get("name"),
                      "full_name": ed.get("description"), "year": ed.get("year"), "url": ed.get("link"),
                      "location": ed.get("place"), "start": start, "end": end,
                      "deadlines": [d for d in (deadline("submission", r, None, None) for r in raw) if d]})
    return items


def our_docs() -> dict[str, tuple[Path, dict]]:
    out = {}
    for path in sorted(DATA.glob("*.yml")):
        try:
            out[path.stem] = (path, yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        except yaml.YAMLError:
            pass
    return out


def match(items: list[dict], docs: dict) -> list[tuple[str, dict]]:
    by_dblp, by_name = {}, {}
    for vid, (_, d) in docs.items():
        m = DBLP_RE.search(str((d.get("links") or {}).get("dblp") or ""))
        if m:
            by_dblp.setdefault(m.group(1), []).append(vid)
        by_name.setdefault((sc.norm(d.get("name")), sc.norm(d.get("full_name"))), []).append(vid)
    out = []
    for it in items:
        ids = by_dblp.get(it["dblp"]) if it["dblp"] else None
        if not ids:
            ids = by_name.get((sc.norm(it["name"]), sc.norm(it["full_name"])))
        if ids and len(ids) == 1:
            out.append((ids[0], it))
    return out


def q(v) -> str:
    """One YAML scalar on one line, quoted only when needed."""
    if isinstance(v, int):
        return str(v)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v)):
        return str(v)
    return yaml.safe_dump(str(v), width=10**6, allow_unicode=True).split("\n")[0]


def edition_block(ed: dict, ind: int, sub: int) -> list[str]:
    p, k = " " * ind, " " * (ind + 2)
    lines = [f"{p}- year: {ed['year']}"]
    for key in ("start", "end", "location", "url", "status"):
        if ed.get(key):
            lines.append(f"{k}{key}: {q(ed[key])}")
    lines.append(f"{k}deadlines:")
    dp, dk = " " * (ind + 2 + sub), " " * (ind + 4 + sub)
    for d in ed["deadlines"]:
        lines.append(f"{dp}- kind: {d['kind']}")
        lines.append(f"{dk}date: {d['date']}")
        if d.get("time"):
            lines += [f"{dk}time: '{d['time']}'", f"{dk}tz: {q(d['tz'])}"]
        if d.get("label"):
            lines.append(f"{dk}label: {q(d['label'])}")
    return lines


def block_end(lines: list[str], i: int) -> int:
    j = i + 1
    while j < len(lines) and (not lines[j].strip() or lines[j][0] in " -#"):
        j += 1
    return j


STALE = re.compile(r"not (yet )?(been )?(announced|available|published|online|out|listed)|no .*(yet|announced)|40[34]")


def drop_stale_unverified(lines: list[str], year: int) -> None:
    """Remove `unverified` items saying the given edition is not announced yet (it now is)."""
    u = next((n for n, line in enumerate(lines) if line == "unverified:"), None)
    if u is None:
        return
    e = block_end(lines, u)
    keep, item = [], []
    for line in lines[u + 1:e] + ["- "]:
        if re.match(r" *- ", line) and item:
            text = " ".join(x.strip() for x in item).lower()
            if not (str(year) in text and STALE.search(text)):
                keep += item
            item = []
        item.append(line)
    lines[u + 1:e] = keep
    if not keep:
        del lines[u]


def add_edition(text: str, ed: dict, source: str | None) -> str | None:
    """The file text with `ed` appended to editions (and `source` to sources), or None if the layout is unusual."""
    lines = text.rstrip("\n").split("\n")
    i = next((n for n, line in enumerate(lines) if re.fullmatch(r"editions:\s*(\[\])?\s*", line)), None)
    if i is None:
        return None
    j = block_end(lines, i)
    items = [re.match(r"( *)- ", line) for line in lines[i + 1:j]]
    ind = next((len(m.group(1)) for m in items if m), 0)
    sub = 0
    for n in range(i + 1, j - 1):
        m = re.fullmatch(r"( *)deadlines:", lines[n])
        if m and (m2 := re.match(r"( *)- ", lines[n + 1])):
            sub = len(m2.group(1)) - len(m.group(1))
            break
    lines[i] = "editions:"
    lines[j:j] = edition_block(ed, ind, sub)
    drop_stale_unverified(lines, ed["year"])
    if source:
        s = next((n for n, line in enumerate(lines) if re.fullmatch(r"sources:\s*(\[\])?\s*", line)), None)
        if s is None:
            lines += ["sources:", f"- {source}"]
        elif source not in text:
            e = block_end(lines, s)
            m = next((re.match(r"( *)- ", line) for line in lines[s + 1:e] if re.match(r"( *)- ", line)), None)
            lines[s] = "sources:"
            lines.insert(e, f"{m.group(1) if m else ''}- {source}")
    return "\n".join(lines) + "\n"


def compare(today: dt.date) -> tuple[list[dict], dict[str, list[str]]]:
    docs = our_docs()
    items = []
    for loader in (load_ccfddl, load_secdl):
        try:
            items += loader()
        except Exception as exc:
            print(f"feed unavailable ({loader.__name__}): {exc}", file=sys.stderr)
    new, hints = {}, {}
    for vid, it in match(items, docs):
        d = docs[vid][1]
        if not it.get("year") or not it["deadlines"]:
            continue
        recent = [x for x in it["deadlines"] if dt.date.fromisoformat(x["date"]) >= today - dt.timedelta(days=3)]
        if not recent:
            continue
        years = {e.get("year"): e for e in d.get("editions") or [] if isinstance(e, dict)}
        if it["year"] not in years:
            new.setdefault((vid, it["year"]), it)  # first feed wins (ccfddl has time zones)
            continue
        have = {str(x.get("date")) for x in years[it["year"]].get("deadlines") or [] if isinstance(x, dict)}
        for x in recent:
            if x["date"] not in have:
                hints.setdefault(vid, []).append(
                    f"{it['feed']} lists a {it['year']} {x['kind']} deadline {x['date']}"
                    + (f" ({x['label']})" if x.get("label") else "") + f" not in the file; check {it['url']}")
    cands = [{"id": vid, **it} for (vid, _), it in sorted(new.items(), key=lambda kv: kv[0])]
    return cands, hints


def confirm_and_apply(c: dict, apply: bool) -> tuple[bool, str]:
    path = DATA / f"{c['id']}.yml"
    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text) or {}
    pages = [u for u in [c.get("url"), (doc.get("links") or {}).get("website")] if u]
    texts = [t for t in (sc.fetch(u) for u in pages) if t]
    found = lambda iso: any(sc.page_has(t, dt.date.fromisoformat(iso)) for t in texts)  # noqa: E731
    missing = [x["date"] for x in c["deadlines"] if not found(x["date"])]
    if missing:
        return False, f"not on the official page: {', '.join(missing)}"
    ed = {k: c.get(k) for k in ("year", "location", "url")} | {"deadlines": c["deadlines"]}
    if any("tentative" in (x.get("label") or "").lower() for x in c["deadlines"]):
        ed["status"] = "tentative"
    if c.get("start") and found(c["start"]):
        ed |= {"start": c["start"], "end": c.get("end") or c["start"]}
    if not apply:
        return True, "confirmed"
    out = add_edition(text, ed, c.get("url"))
    if out is None:
        return False, "file layout not recognised"
    rep = Report()
    try:
        validate(path, yaml.safe_load(out), rep)
    except Exception as exc:
        return False, f"validation crashed: {exc}"
    if rep.errors:
        return False, f"validation: {rep.errors[0]}"
    path.write_text(out, encoding="utf-8")
    dls = ", ".join(f"{x['kind']} {x['date']}" for x in c["deadlines"])
    return True, f"added {c['year']} edition from the official page ({dls})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--hints", help="write unconfirmed findings as JSON {id: [hint, ...]}")
    ap.add_argument("--log", help="append one JSON line per applied or rejected edition")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today)")
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    cands, hints = compare(today)
    print(f"{len(cands)} new editions in the feeds, {len(hints)} venues with deadlines not in the file")
    log = open(args.log, "a", encoding="utf-8") if args.log else None
    for c in cands:
        ok, msg = confirm_and_apply(c, args.apply)
        print(f"{'ok ' if ok else 'no '} {c['id']} {c['year']}: {msg}")
        if not ok:
            hints.setdefault(c["id"], []).append(
                f"{c['feed']} lists a {c['year']} edition ({', '.join(x['kind'] + ' ' + x['date'] for x in c['deadlines'])})"
                f" at {c['url']}; {msg}")
        if log:
            log.write(json.dumps({"phase": "feeds", "id": c["id"], "applied": ok and args.apply, "note": msg}) + "\n")
    for vid, hs in sorted(hints.items()):
        for h in hs:
            print(f"hint {vid}: {h}")
    if args.hints:
        Path(args.hints).write_text(json.dumps(hints, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
