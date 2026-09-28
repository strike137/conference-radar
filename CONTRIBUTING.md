# Contributing

Thanks for keeping this list useful. Everything lives in `data/conferences/<id>.yml`, one file per venue.
If Git is not your thing, use the [Add a conference](../../issues/new?template=add-conference.yml) form
instead; a bot converts it into a pull request.

## Quick rules

- Dates are `YYYY-MM-DD`. Times are quoted: `time: "23:59"`.
- Copy dates from the official call for papers and put that page under `sources`.
- Set `last_verified` to the day you checked.
- Never guess a date. Leave it out; the site estimates from the previous edition and marks it with `~`.
- Keep notes short and factual. Opinions that are widely shared ("regarded as mid-tier") are fine.
- Quote a note that contains `: ` or ` #`, otherwise YAML reads it as something else:
  `- "Acceptance rate: 24% (2025)"`.
- Run `python3 scripts/build.py --check` (or let the "Check data" action do it).
- `python3 scripts/stale.py` lists venues whose next call for papers is due, so you know what to update first.

## Fields

| Field | Required | Values / example |
|---|---|---|
| `id` | yes | Lowercase letters, digits and `-`; must equal the file name. `icissp`, `css-jp` |
| `name` | yes | Short name as people write it: `ICISSP`, `IEEE S&P` |
| `full_name` | yes | Official full name |
| `name_local` | no | Japanese / Korean / Chinese name for domestic venues |
| `type` | yes | `conference`, `workshop` (co-located), `industry` (hacker or practitioner conference). Recurring society meetings such as IEICE/IPSJ kenkyukai are not listed; the site covers conferences only. |
| `tier` | yes | `top` (flagship of its field, usually CORE A*), `major` (well-established and competitive, CORE A/B or CCF A/B), `minor` (smaller or regional, CORE C or unranked, high acceptance), `domestic` (national conference in a local language) |
| `areas` | yes | Any of `security` (incl. privacy), `crypto`, `ai`, `nlp`, `data` (data mining, databases, web, knowledge graphs), `vision`, `networking` (incl. network management), `communications` (wireless, telecom, EE), `systems`, `software`, `general` (broad CS/EE) |
| `region` | yes | Where it is usually held: `japan`, `korea`, `taiwan`, `china`, `southeast-asia`, `south-asia`, `asia-pacific` (rotates within Asia/Oceania), `oceania`, `europe`, `north-america`, `latin-america`, `middle-east`, `africa`, `worldwide` (rotates globally), `online` |
| `language` | no | `english`, `japanese`, `korean`, `chinese`, `mixed` |
| `frequency` | no | `annual`, `biennial`, `multiple-per-year`, `irregular`. Biennial venues are estimated two years ahead. |
| `organizer` | no | `KIISC`, `IEEE ComSoc`, `INSTICC`, ... |
| `organizer_country` | no | Country of the society or institution that runs it, not where it is held: `japan`, `korea`, `taiwan`, `china`, `singapore`, `india`, `vietnam`, `thailand`, `indonesia`, `malaysia`, `philippines`, `australia`, `new-zealand`, `usa`, `canada`, `europe`, `international` (global society flagships with a worldwide steering committee), `other`. Several are allowed: `[korea, japan]`. ICAIIC is held in Japan but run by KICS, so it is `[korea]`. |
| `proceedings` | no | Where the papers are published: `Springer LNCS`, `IEEE Xplore`, `ACM DL`, `SCITEPRESS`, `J-STAGE`, `IPSJ Digital Library`, ... Write `None` only when nothing is published, or `None (participants only)` when the proceedings are handed to attendees only. |
| `archival` | no | `false` for venues whose papers are not peer-reviewed or do not count as a publication (most domestic conferences); the site then marks the proceedings "not peer-reviewed". |
| `indexing` | no | `[Scopus, DBLP, EI]` |
| `rank.core` | no | `A*`, `A`, `B`, `C`, `National`, `Regional`, `Unranked` from the [CORE portal](https://portal.core.edu.au/conf-ranks/). The edition shown on the site is set in `config.yml`; use `rank.core_source` if you had to take an older edition. |
| `rank.ccf` | no | `A`, `B`, `C`, or leave empty if the CCF list does not include it |
| `acceptance_rate` | no | Free text with year: `24% (2025, 60/250)` |
| `fee` | no | Free text with year and currency: `About 350 USD (2025, regular)` |
| `typical.deadline_months` | no | Months (1-12) of the usual main deadline, used when no dates are known |
| `typical.conference_months` | no | Months of the usual conference dates |
| `links.website` / `links.dblp` / `links.wikicfp` | no | URLs |
| `notes` | no | List of short bullet notes |
| `editions` | no | See below |
| `sources` | no | URLs you used |
| `last_verified` | no | `YYYY-MM-DD` |
| `unverified` | no | Things you could not confirm; the site shows them as a warning |

### Editions

Keep at least the latest edition that has taken place and add the next one as soon as anything is
announced. Older editions can be removed.

```yaml
editions:
  - year: 2027                 # the conference year
    start: 2027-02-03
    end: 2027-02-05
    location: Porto, Portugal
    url: https://example.org/2027/
    status: confirmed          # or tentative
    deadlines:
      - kind: abstract         # abstract | submission | notification | camera_ready | other
        date: 2026-09-25
      - kind: submission
        date: 2026-10-02
        time: "23:59"
        tz: AoE                # AoE, UTC, UTC+9, JST, KST, CET, CEST, PST, PDT, EST, EDT, IST, SGT, ...
        label: Regular papers  # use labels for multiple cycles or tracks
```

Without `tz` the site assumes AoE (and 23:59 when `time` is missing too), the latest possible moment, and
marks the deadline with "AoE?" so readers know the time zone was not stated. Use `status: tentative` for an
edition whose dates are announced as tentative; the site labels its dates "tentative".

## Writing notes

Aim for what the lab seminar slides said about each venue: the organizer, proceedings and indexing, where
it is held, reputation, acceptance rate, cost, and anything unusual (non-archival, biennial, double-blind,
several review cycles, domestic session plus international session, and so on). Plain English, one fact per
bullet.
