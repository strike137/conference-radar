#!/usr/bin/env python3
"""The weekly update: public feeds first, then a coding agent in small batches, every change checked.

    python3 scripts/weekly.py update   --agent "opencode run -m opencode/deepseek-v4.1-flash-free --auto"
    python3 scripts/weekly.py discover --agent "..."
    python3 scripts/weekly.py exists "ACRONYM" "Full name" "https://site/"     used by the agent: EXISTS or NEW

update    adds new editions from ccfddl and sec-deadlines when the official page confirms them (feeds.py),
          then hands the stale.py queue to the agent a few venues at a time.
discover  asks the agent for missing venues from a rotating set of angles and has it write each one.

After every agent run, anything outside the files it was given is restored, and each file it changed is
kept only if it validates, every new date appears on a page the file cites (sourcecheck.py) and its CORE
rank matches ICORE2026. Results go to .weekly/log.jsonl; the commit message to .weekly/msg-<phase>.txt.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import DATA, ID_RE, ROOT, Report, UniqueKeyLoader, load_all, validate  # noqa: E402
import feeds  # noqa: E402
import sourcecheck as sc  # noqa: E402
from stale import assess  # noqa: E402

STATE = ROOT / ".weekly"
LOG = STATE / "log.jsonl"
MODEL_NOTE = "OpenCode agent"
ANGLES = [
    "security and privacy conferences held in Europe",
    "security and cryptography conferences held in North or Latin America",
    "AI and machine learning conferences held in Asia or Oceania",
    "AI, NLP and computer vision conferences held in Europe or the Americas",
    "networking and communications conferences (IEEE ComSoc, ACM SIGCOMM, IFIP sponsored)",
    "national computer science or electronics conferences in Japan, Korea, Taiwan or China",
    "computer science and engineering conferences in Southeast Asia or South Asia",
    "conferences in Africa or the Middle East on computing, security or communications",
    "workshops co-located with major security, AI or networking conferences",
    "hacker and practitioner security conferences with a call for papers or talks",
    "systems, software engineering and databases conferences",
    "IEEE Region 10 and IEEE section flagship conferences",
]
DASHES = {"\u2014": "-", "\u2013": "-"}


def log(entry: dict) -> None:
    STATE.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def snapshot() -> dict[str, str]:
    """File name -> text of every data file, taken right before an agent run."""
    return {p.name: p.read_text(encoding="utf-8", errors="replace") for p in DATA.glob("*.yml")
            if p.is_file() and not p.is_symlink()}


def restore_outside() -> list[str]:
    """Undo every change the agent made outside data/conferences/*.yml and .weekly/."""
    out = subprocess.run(["git", "status", "--porcelain", "-z", "--untracked-files=all"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    undone = []
    for entry in filter(None, out.split("\0")):
        code, path = entry[:2], entry[3:]
        if (path.startswith("data/conferences/") and path.endswith(".yml") and "/" not in path[17:]) \
                or path.startswith(".weekly/"):
            continue
        undone.append(path)
        if code == "??":
            p = ROOT / path
            if p.is_symlink() or p.is_file():
                p.unlink()
        else:
            subprocess.run(["git", "checkout", "-q", "HEAD", "--", path], cwd=ROOT)
    # Symlinks or odd files the agent may have left among the data.
    for p in DATA.iterdir():
        if p.is_symlink() or (p.suffix == ".yml" and not p.is_file()):
            p.unlink()
            undone.append(str(p.relative_to(ROOT)))
    return undone


def run_agent(agent: str, prompt: str, tag: str, timeout: int) -> str:
    """Run the agent in its own process group, capture its output, and make sure nothing it started survives."""
    (STATE / "agent").mkdir(parents=True, exist_ok=True)
    out_path = STATE / "agent" / f"{tag}.log"
    with out_path.open("w", encoding="utf-8") as out:
        proc = subprocess.Popen(shlex.split(agent) + [prompt], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True,
                                env={k: v for k, v in os.environ.items() if "TOKEN" not in k and "SECRET" not in k})
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            out.write(f"\n[weekly.py] stopped after {timeout}s\n")
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
    return re.sub(r"\x1b\[[0-9;]*m", "", out_path.read_text(encoding="utf-8", errors="replace"))


def old_text(name: str) -> str | None:
    out = subprocess.run(["git", "show", f"HEAD:data/conferences/{name}"], cwd=ROOT, capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def put_back(name: str, before: str | None) -> None:
    path = DATA / name
    if before is None:
        path.unlink(missing_ok=True)
    else:
        path.write_text(before, encoding="utf-8")


def summarize(old: dict | None, new: dict) -> str:
    if not old:
        eds = ", ".join(str(e.get("year")) for e in new.get("editions") or [] if isinstance(e, dict))
        return f"new venue ({new.get('full_name')}; editions {eds or 'none'})"
    parts = []
    olds = {e.get("year"): e for e in old.get("editions") or [] if isinstance(e, dict)}
    for e in new.get("editions") or []:
        if not isinstance(e, dict):
            continue
        y = e.get("year")
        dl = lambda ed: {(d.get("kind"), str(d.get("date"))) for d in ed.get("deadlines") or [] if isinstance(d, dict)}  # noqa: E731
        if y not in olds:
            subs = ", ".join(f"{k} {d}" for k, d in sorted(dl(e), key=lambda x: x[1]) if k in ("abstract", "submission"))
            parts.append(f"added {y} edition" + (f" ({subs})" if subs else ""))
            continue
        added, removed = dl(e) - dl(olds[y]), dl(olds[y]) - dl(e)
        for k, d in sorted(added):
            was = [od for ok, od in removed if ok == k]
            parts.append(f"{y} {k} {was[0]} -> {d}" if was else f"{y} {k} {d} added")
        for key in ("start", "location", "url", "status"):
            if str(e.get(key)) != str(olds[y].get(key)) and e.get(key):
                parts.append(f"{y} {key} {e.get(key)}")
    skip = {"editions", "last_verified", "sources", "unverified"}
    keys = [k for k in new if k not in skip and new.get(k) != old.get(k)]
    if keys:
        parts.append("changed " + ", ".join(keys))
    return "; ".join(parts) if parts else "checked, no change"


def gate(name: str, before: str | None, allowed: set[str]) -> tuple[bool, str]:
    """Keep the agent's version of data/conferences/<name> only if it passes every check."""
    path = DATA / name
    vid = name[:-4]
    if vid not in allowed:
        return False, "not one of the files this run was given"
    text = path.read_text(encoding="utf-8", errors="replace")
    if any(ch in text for ch in DASHES):
        text = text.translate(str.maketrans(DASHES))
        path.write_text(text, encoding="utf-8")
    try:
        new = yaml.load(text, Loader=UniqueKeyLoader) or {}
    except (yaml.YAMLError, ValueError) as exc:
        return False, f"not valid YAML ({str(exc).splitlines()[0]})"
    if not isinstance(new, dict) or new.get("id") != vid:
        return False, "id does not match the file name"
    rep = Report()
    try:
        validate(path, new, rep)
    except Exception as exc:
        return False, f"validation crashed ({exc})"
    if rep.errors:
        return False, f"validation: {rep.errors[0]}"
    old = yaml.safe_load(before) if before else None
    if before is not None and text == before:
        return True, "no change"
    res = sc.check_doc(new, old)
    if res["missing"]:
        return False, "dates not on the cited pages: " + "; ".join(res["missing"][:4])
    if not old or (old.get("rank") or {}).get("core") != (new.get("rank") or {}).get("core"):
        core = sc.check_core(new)
        if core and core[0] == "error":
            return False, core[1]
    if not old and not new.get("sources"):
        return False, "new venue without sources"
    return True, summarize(old, new)


def apply_gate(snap: dict[str, str], allowed: set[str], phase: str, agent_out: str) -> list[dict]:
    undone = restore_outside()
    results = []
    after = snapshot()
    for name in sorted(set(after) | set(snap)):
        if after.get(name) == snap.get(name):
            continue
        before = snap.get(name)
        ok, note = gate(name, before, allowed) if name in after else (False, "file deleted")
        if not ok:
            put_back(name, before)
        line = next((ln.strip() for ln in agent_out.splitlines() if ln.strip().startswith(name[:-4] + ":")), "")
        entry = {"phase": phase, "id": name[:-4], "kept": ok, "note": note, "agent": line[:300]}
        results.append(entry)
        log(entry)
    if undone:
        log({"phase": phase, "id": "-", "kept": False, "note": "restored files outside the data: " + ", ".join(undone[:10])})
    return results


UPDATE_PROMPT = """You are updating Conference Radar, a dataset of academic conferences. Each venue is one YAML file in data/conferences/. Today is {today}.

Work only on these files:
{items}

For each file:
1. Read it. Open its official website (links.website, or the url of its newest edition) with webfetch, then its call for papers or important dates page.
2. If the next edition is announced, add it under editions with year, start, end, location, url and every deadline: kind (abstract, submission, notification, camera_ready or other), date as YYYY-MM-DD, and time and tz only if the page states them (time: '23:59', tz: AoE).
3. If a deadline of an existing edition was extended or changed, update its date.
4. Add every page you took a date from to sources. A script rejects the whole file if any new date does not appear on the edition url, links.website or a page listed under sources.
5. Set last_verified: {today}. If nothing new is announced, change only last_verified.

Rules: never guess a date. Keep the existing layout and do not rewrite lines you do not change. English only. Never use em dashes or en dashes. Do not edit any other file and do not run git. Field definitions are in CONTRIBUTING.md if you need them.

Finish with one line per venue in the form "<id>: <what you changed, or no change>".
"""

PROPOSE_PROMPT = """You help extend Conference Radar, a dataset of academic conferences (security, AI, networking, communications and general EECS, worldwide). Today is {today}.

Find up to 15 real conferences matching: {angle}.
Each must have an official website and an edition in {year} or later. Skip recurring society meetings, network operator group meetings and trade shows.
For each one, check that it is not already in the dataset by running:
  python3 scripts/weekly.py exists "<acronym>" "<full name>" "<website>"
Keep only the ones that print NEW.

Write the kept ones to .weekly/candidates.json as a JSON list of objects with the keys id (lowercase letters, digits and hyphens, usually the acronym), name, full_name and website. Do not create or edit any other file and do not run git.
"""

CREATE_PROMPT = """Create the file data/conferences/{id}.yml for {name} ({full_name}), official website {website}. Today is {today}.

Use data/_template.yml as the starting point and CONTRIBUTING.md for the allowed values. Fill id ({id}), name, full_name, type, tier, areas, region, language, frequency, organizer, organizer_country, proceedings, archival, rank, typical, links.website, notes, editions, sources and last_verified ({today}).
- rank.core only as listed on the CORE portal ICORE2026 (portal.core.edu.au/conf-ranks), otherwise Unranked. rank.ccf only if the CCF list includes it, otherwise leave it out.
- editions: the latest edition that took place and the next one if announced, each with year, start, end, location, url and deadlines (kind, date YYYY-MM-DD, time and tz only if stated).
- notes: 3 to 6 short factual bullets (organizer, proceedings, where it is held, anything unusual).
- sources: every page you took information from. A script deletes the file if any date does not appear on an edition url, links.website or a page under sources.

Rules: never guess. English only. Never use em dashes or en dashes. Do not edit any other file and do not run git.
If the venue has had no edition since 2023, or is a society meeting, operator group meeting or trade show, do not create the file and reply "skip: <reason>".
"""


def queue(today: dt.date, hints: dict[str, list[str]]) -> list[tuple[str, list[str]]]:
    rep = Report()
    records = load_all(rep)
    rows = []
    for rec in records:
        for it in assess(rec, today):
            rows.append((it["score"], rec["id"], f"{it['reason']}: {it['detail']}"))
    rows.sort()
    order: dict[str, list[str]] = {vid: [f"feed: {h}" for h in hs] for vid, hs in hints.items()
                                   if (DATA / f"{vid}.yml").exists()}
    for _, vid, why in rows:
        order.setdefault(vid, []).append(why)
    return list(order.items())


def cmd_update(args, today: dt.date, deadline: float) -> None:
    hints: dict[str, list[str]] = {}
    if not args.no_feeds:
        cands, hints = feeds.compare(today)
        for c in cands:
            ok, msg = feeds.confirm_and_apply(c, apply=True)
            log({"phase": "feeds", "id": c["id"], "kept": ok, "note": msg})
            if not ok:
                hints.setdefault(c["id"], []).append(
                    f"{c['feed']} lists a {c['year']} edition at {c['url']} "
                    f"({', '.join(x['kind'] + ' ' + x['date'] for x in c['deadlines'])})")
    todo = queue(today, hints)
    log({"phase": "update", "id": "-", "kept": True, "note": f"queue of {len(todo)} venues"})
    done, fails = 0, 0
    for n in range(0, len(todo), args.batch):
        if time.time() > deadline or (args.limit and n // args.batch >= args.limit) or fails >= 3:
            for vid, _ in todo[n:]:
                log({"phase": "update", "id": vid, "kept": False, "note": "not reached", "skipped": True})
            break
        batch = todo[n:n + args.batch]
        items = "\n".join(f"- data/conferences/{vid}.yml ({'; '.join(why)[:400]})" for vid, why in batch)
        before = snapshot()
        out = run_agent(args.agent, UPDATE_PROMPT.format(today=today, items=items), f"update-{n // args.batch:03d}",
                        args.agent_timeout)
        res = apply_gate(before, {vid for vid, _ in batch}, "update", out)
        touched = {r["id"] for r in res}
        for vid, _ in batch:
            if vid not in touched:
                log({"phase": "update", "id": vid, "kept": False, "note": "agent made no change"})
        fails = fails + 1 if not res and ("error" in out.lower() or len(out) < 200) else 0
        done += len(batch)
        print(f"update: {done}/{len(todo)} venues, {sum(r['kept'] for r in res)} files kept in this batch", flush=True)


def exists_index() -> tuple[set[str], set[str], set[str]]:
    ids, names, sites = set(), set(), set()
    for path in DATA.glob("*.yml"):
        try:
            d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        ids.add(path.stem)
        for k in ("name", "full_name"):
            if d.get(k):
                names.add(sc.norm(d[k]))
        site = (d.get("links") or {}).get("website")
        if site:
            sites.add(site_key(site))
    return ids, names, sites


def site_key(url: str) -> str:
    u = urlsplit(str(url).lower())
    return (u.netloc.removeprefix("www.") + u.path).rstrip("/")


def is_new(c: dict, idx) -> bool:
    ids, names, sites = idx
    return not (c.get("id") in ids or sc.norm(c.get("name")) in names or sc.norm(c.get("full_name")) in names
                or (c.get("website") and site_key(c["website"]) in sites))


def cmd_discover(args, today: dt.date, deadline: float) -> None:
    week = today.isocalendar()[1]
    angles = ANGLES[week % len(ANGLES):] + ANGLES[:week % len(ANGLES)]
    dry, made = 0, 0
    for r, angle in enumerate(angles):
        if time.time() > deadline or dry >= 2 or (args.limit and r >= args.limit):
            break
        cand_file = STATE / "candidates.json"
        cand_file.unlink(missing_ok=True)
        before = snapshot()
        run_agent(args.agent, PROPOSE_PROMPT.format(today=today, angle=angle, year=today.year - 1),
                  f"propose-{r:02d}", args.agent_timeout)
        apply_gate(before, set(), "discover", "")  # proposing must not touch the data
        try:
            cands = json.loads(cand_file.read_text(encoding="utf-8"))
            cands = [c for c in cands if isinstance(c, dict)]
        except (OSError, ValueError):
            cands = []
        fresh, seen = [], set()
        idx = exists_index()
        for c in cands:
            c = {k: str(c.get(k) or "").strip() for k in ("id", "name", "full_name", "website")}
            if not ID_RE.match(c["id"]) or not c["website"].startswith("http") or c["id"] in seen or not is_new(c, idx):
                continue
            seen.add(c["id"])
            fresh.append(c)
        log({"phase": "discover", "id": "-", "kept": True,
             "note": f"angle '{angle}': {len(cands)} proposed, {len(fresh)} new"})
        dry = dry + 1 if not fresh else 0
        for c in fresh:
            if time.time() > deadline:
                log({"phase": "discover", "id": c["id"], "kept": False, "note": "not reached", "skipped": True})
                continue
            if not is_new(c, exists_index()):
                continue
            before = snapshot()
            out = run_agent(args.agent, CREATE_PROMPT.format(today=today, **c), f"create-{c['id']}", args.agent_timeout)
            res = apply_gate(before, {c["id"]}, "discover", out)
            if not res:
                skip = next((ln.strip() for ln in out.splitlines() if ln.strip().lower().startswith("skip:")), "")
                log({"phase": "discover", "id": c["id"], "kept": False, "note": skip or "agent wrote no file"})
            made += sum(x["kept"] for x in res)
            print(f"discover: {made} venues added so far", flush=True)


def message(phase: str, today: dt.date) -> str:
    entries = [json.loads(ln) for ln in LOG.read_text(encoding="utf-8").splitlines()] if LOG.exists() else []
    phases = ("feeds", "update") if phase == "update" else ("discover",)
    es = [e for e in entries if e["phase"] in phases and e["id"] != "-"]
    kept = [e for e in es if e["kept"] and e["note"] not in ("no change",)]
    if not kept:
        return ""
    title = f"Weekly update {today}" + (": new venues" if phase == "discover" else "")
    lines = [title, "", f"Automated run: public deadline feeds (ccfddl, sec-deadlines) and an {MODEL_NOTE}.",
             "Every new or changed date was found on a page the file cites; files that failed that check",
             "were left unchanged.", ""]
    feed = [e for e in kept if e["phase"] == "feeds"]
    changed = [e for e in kept if e["phase"] != "feeds" and e["note"] != "checked, no change"]
    same = sorted(e["id"] for e in kept if e["note"] == "checked, no change")
    rejected = [e for e in es if not e["kept"] and not e.get("skipped") and e["note"] not in ("agent made no change",)]
    skipped = [e["id"] for e in es if e.get("skipped")]
    if feed:
        lines += ["Added from the feeds after checking the official page:"] + [f"- {e['id']}: {e['note']}" for e in feed] + [""]
    if changed:
        head = "Venues added:" if phase == "discover" else "Venues updated:"
        lines += [head] + [f"- {e['id']}: {e['note']}" for e in changed] + [""]
    if same:
        lines += ["Checked, no change: " + ", ".join(same), ""]
    if rejected:
        lines += ["Not applied:"] + [f"- {e['id']}: {e['note'][:200]}" for e in rejected[:80]] + [""]
    if skipped:
        lines += [f"Not reached in this run: {len(skipped)} venues", ""]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["update", "discover", "message", "exists"])
    ap.add_argument("words", nargs="*", help="for exists: acronym, full name, website")
    ap.add_argument("--agent", default="opencode run -m opencode/deepseek-v4.1-flash-free --auto")
    ap.add_argument("--minutes", type=float, default=150, help="stop starting new agent runs after this long")
    ap.add_argument("--batch", type=int, default=5, help="venues per agent run (update)")
    ap.add_argument("--limit", type=int, default=0, help="at most this many agent batches or angles (0: no limit)")
    ap.add_argument("--agent-timeout", type=int, default=900, help="seconds per agent run")
    ap.add_argument("--no-feeds", action="store_true")
    ap.add_argument("--part", choices=["update", "discover"], default="update", help="for message")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today)")
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    STATE.mkdir(exist_ok=True)
    if args.phase == "exists":
        w = args.words + ["", "", ""]
        c = {"id": sc.norm(w[0]), "name": w[0], "full_name": w[1], "website": w[2]}
        print("NEW" if is_new(c, exists_index()) else "EXISTS")
        return 0
    if args.phase == "message":
        print(message(args.part, today), end="")
        return 0
    deadline = time.time() + args.minutes * 60
    (cmd_update if args.phase == "update" else cmd_discover)(args, today, deadline)
    rep = Report()
    load_all(rep)
    for err in rep.errors:  # should not happen after the per-file gate, but never publish a broken file
        name = err.split(":")[0].split("/")[-1]
        if (DATA / name).exists():
            put_back(name, old_text(name))
            log({"phase": args.phase, "id": name[:-4], "kept": False, "note": f"reverted: {err[:150]}"})
    msg = message(args.phase, today)
    (STATE / f"msg-{args.phase}.txt").write_text(msg, encoding="utf-8")
    print(msg or "nothing to commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
