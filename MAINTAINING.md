# Maintaining the data

How the data is kept current. A scheduled Claude agent runs this procedure on the 1st of every month and
publishes the result without manual review, so every rule below matters. Anyone doing a bulk update by hand
should follow it too. Field definitions are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Scope

- Conferences only: `type` is `conference`, `workshop` (co-located academic workshop) or `industry`
  (hacker/practitioner conference). Do not add recurring society meetings (IEICE/IPSJ kenkyukai),
  network operators' group meetings (JANOG, SANOG, ...), trade shows, or chapter paper meetings.
- Focus: security, AI, networking, communications and general EECS, with emphasis on venues held or run in
  Asia and on smaller venues students can realistically attend. Major venues are listed for reference.
- Skip venues with no edition since 2023 (discontinued or dormant).

## Rules for every change

- Source every date from the official site or CFP page and list that page under `sources`. WikiCFP and
  aggregator sites are hints only. Never guess a date; leave it out and, if useful, write what is missing
  under `unverified`.
- Dates `YYYY-MM-DD`. Add `time` (quoted, `"23:59"`) and `tz` only when the page states them. For domestic
  Japanese/Korean/Chinese/Taiwanese events that state a time without a zone, use the local zone (JST, KST,
  UTC+8). When no zone is given the site already assumes local time for domestic events and AoE otherwise.
- Keep old editions that are needed for estimates (at least the latest one that took place); add the next
  edition as soon as anything is announced. Mark announced-as-tentative editions `status: tentative`.
- Set `last_verified` to the date you checked.
- Ranks: `rank.core` from the CORE portal, ICORE2026 edition
  (<https://portal.core.edu.au/conf-ranks/?search=ACRONYM&by=all&source=ICORE2026>), using the exact label
  shown there (`A*`, `A`, `B`, `C`, `National: Japan`, `Australasian B`, `Multiconference`, `Unranked`, ...).
  `rank.ccf` from the CCF 2026 recommended list (<https://www.ccf.org.cn/Academic_Evaluation/By_category/>);
  leave it out when the venue is not listed. Match on the full name, not only the acronym (the CCF "WISA" is a
  Chinese web conference, not the Korean WISA; the CCF "SAC" is Selected Areas in Cryptography, not ACM SAC).
- `organizer_country`: the country of the society or institution that runs the venue, not where it is held
  (ICAIIC is held in Japan but run by the Korean KICS -> `[korea]`). Global society flagships with a worldwide
  steering committee -> `[international]`. Several values for joint organizers.
- `region`: where the venue is usually held, from the last six editions: a country or region that hosts at least
  five of them, else `asia-pacific` (rotates within Asia/Oceania) or `worldwide`. One edition abroad does not change it.
- `tier`: `top` flagship of its field (usually CORE A*), `major` established and competitive (CORE A/B or
  CCF A/B), `minor` smaller or regional (CORE C, national rank or unranked), `domestic` national conference in
  a local language.
- `proceedings`: where papers are published (`IEEE Xplore`, `Springer LNCS`, `J-STAGE`, `ANLP website`, ...).
  Use `None` only when nothing is published, `None (participants only)` when only attendees get it. Set
  Post-proceedings count: when the (revised) papers appear in a formal series or digital library after the event
  (Springer LNCS/LNAI/CCIS/IFIP AICT, PMLR, IEEE Xplore, ACM DL, ...), even as "revised selected papers", name
  that series first and set `archival: true` (JSAI-isAI -> Springer LNAI, WISA -> Springer LNCS). Set
  `archival: false` only when papers stay in participant-only or informal proceedings, when there is no peer
  review (most domestic conferences), or when only journal special issues pick up selected papers; the site
  then shows "non-archival".
- Notes: short factual bullets like a lab seminar slide (organizer, proceedings, where it is held,
  reputation, acceptance rate, cost, anything unusual). Plain English. Never use em dashes or en dashes;
  write arrows as `->`. Quote a note that contains `: ` or ` #`.
- No internal information about any lab, project or budget.
- Do not reformat files you did not otherwise change.
- `python3 scripts/build.py --check` must report 0 errors before you open a pull request.

## Monthly update procedure

1. `pip install pyyaml` and run `python3 scripts/stale.py --limit 60` for the work queue: venues whose next
   call for papers is due or overdue but not recorded, venues with a deadline in the next 30 days, and venues
   not verified for a long time.
2. Work through the queue (most urgent first): open the official site, add the new edition and its
   deadlines, fix anything that changed, update `sources` and `last_verified`.
3. Handle open GitHub issues labeled `update` (reports from the site): apply what the official source
   confirms, then close the issue with a short comment. Review open pull requests from the issue bot
   (branches `add/issue-*`): check the file against the official site, fix it on that branch if needed, run
   the validator, then merge it (`gh pr merge N --squash --delete-branch`). Close submissions that are out of
   scope or cannot be verified, with a comment saying why.
4. Add up to 10 missing venues that fit the scope (search for Asian and regional security, AI, networking
   and communications conferences not yet in `data/conferences/`). Each new file needs every field you can
   source: tier, areas, region, organizer, organizer_country, proceedings, rank, typical months, notes,
   editions, sources.
5. Run `python3 scripts/build.py --check` until it reports 0 errors.
6. Commit to `main` and push; the site redeploys by itself. Use one commit titled `Monthly update YYYY-MM`
   whose message lists venues updated (what changed), venues added, issues and pull requests handled, and
   anything you could not verify. If pushing to `main` is not allowed, push the branch `update/YYYY-MM` and
   open a pull request with the same title and text instead: the "Auto-merge data updates" workflow merges it
   once the data validates and redeploys the site.
