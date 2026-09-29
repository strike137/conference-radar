# Conference Radar

Deadlines, rankings and notes for security, AI, networking and general EECS conferences, with a focus on
the Asian and smaller venues that students actually attend. Curated by Claude Opus 5.5 and governed by Jongmin Lee;
the data is refreshed on the 1st of every month (see [Monthly refresh](#monthly-refresh)).

**Site:** https://strike137.github.io/conference-radar/

## What you can do on the site

- **Table**: every venue with its tier, who runs it, areas, CORE and CCF rank, proceedings (where papers are
  published, marked "non-archival" when it does not count as a formal publication, as at most domestic conferences), next deadline (with countdown), next conference dates and location. Click a column header to sort (on phones use the Sort menu), click a row for
  notes, all editions and deadlines, sources and edit links.
- **Search and filters**: free text, area, tier, type, region where it is held (including "Asia (all)"), who runs it
  (Korean, Japanese, Chinese, Taiwanese, ... institutions), CORE, CCF, proceedings
  (has / none / IEEE / Springer / LNCS / ACM / ACL Anthology),
  "deadline between" and "conference held between" date ranges (dates as written in the call for papers), and
  "deadline within the next 30 days / 90 days / 6 months" (counted from now, so a deadline that is still open
  somewhere on Earth is included). Filters are kept in the URL, so you can share a filtered view.
- **Calendar**: month view of deadlines, notifications and conference days.
- **Timeline**: twelve months at a glance, one row per venue.
- **Export .ics**: download the upcoming announced deadlines of the current selection into your calendar
  (estimates are not exported; tentative ones are marked tentative).

When a venue has not announced its next call for papers yet, the site estimates the next dates from the
previous edition and marks them with `~`. Always confirm on the official site.

## Adding or fixing a conference

Each venue is one YAML file in [`data/conferences/`](data/conferences/). Three ways, easiest first:

1. **Fill in a form.** Open an issue with the
   [Add a conference](../../issues/new?template=add-conference.yml) form. A bot turns it into a pull
   request and comments with the link. For wrong or outdated information use
   [Report outdated info](../../issues/new?template=update-conference.yml) (the site prefills it).
2. **Edit on GitHub.** Every venue on the site has an *Edit on GitHub* button that opens its file in the
   GitHub editor. Change it and press "Propose changes".
3. **Locally.**

   ```bash
   cp data/_template.yml data/conferences/myconf.yml   # fill it in
   pip install pyyaml
   python3 scripts/build.py --serve                     # validate, build and open http://localhost:8000
   ```

Field-by-field guidance is in [CONTRIBUTING.md](CONTRIBUTING.md).

## Monthly refresh

On the 1st of every month a scheduled Claude agent follows [MAINTAINING.md](MAINTAINING.md): it checks venues
whose next call for papers is due (`python3 scripts/stale.py`), re-checks deadlines in the next 30 days,
handles "Report outdated info" issues and form submissions, adds a few missing venues, validates everything
and publishes the update directly.

## How it works

```
data/conferences/*.yml     one file per venue (the only thing contributors touch)
data/_template.yml         starting point for a new file
config.yml                 site title, repository name, ranking editions
site/                      static page: index.html, app.js, style.css (no framework, no build step)
scripts/build.py           validates every YAML file and writes _site/ with conferences.json
scripts/issue_to_yaml.py   turns an "Add a conference" issue into a YAML file
scripts/stale.py           lists venues that need an update (used by the monthly refresh)
.github/workflows/         check.yml (validate PRs), deploy.yml (publish to Pages), issue-to-pr.yml,
                           auto-merge.yml (merges update/* pull requests that validate)
```

Pushing to `main` runs `deploy.yml`, which builds `_site/` and publishes it with GitHub Pages. Pull requests
run `check.yml`; a PR with an invalid file fails with a message pointing at the field.

## Maintainer setup (once)

```bash
gh repo create <owner>/conference-radar --public --source . --push
gh api -X POST repos/<owner>/conference-radar/pages -f build_type=workflow
gh api -X PUT repos/<owner>/conference-radar/actions/permissions/workflow \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=true
gh label create new-conference --color 2f5bd3 --description "Created by the Add a conference form" -R <owner>/conference-radar
gh label create update --color c2410c --description "Outdated or wrong information" -R <owner>/conference-radar
```

The first `gh api` call sets Pages to "GitHub Actions"; the second lets the issue bot open pull requests.
If the repository moves (for example to the lab organization), change `repo` in `config.yml`; inside
GitHub Actions the real repository name is used automatically.

## Data sources

Initial data was collected from official conference and CFP pages, the
[CORE portal](https://portal.core.edu.au/conf-ranks/) (ICORE2026), the CCF list, and cross-checked against
[sec-deadlines](https://sec-deadlines.github.io/), [ccf-deadlines](https://github.com/ccfddl/ccf-deadlines),
[Hugging Face AI deadlines](https://huggingface.co/spaces/huggingface/ai-deadlines) and WikiCFP.
Each file lists its sources and the date it was last verified.
