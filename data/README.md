# Data sources

Nothing in `data/raw/` or `data/processed/` is committed. Run
`python src/acquire.py` and then `python src/git_history.py` to rebuild it.

## 1. GHPR — pull requests (development activity)

- **What:** 14,384 rows, each a merged pull request linked to the issue it
  fixed, from 13 CNCF graduated projects (Kubernetes, Envoy, Helm,
  Prometheus, …). Columns include issue/PR timestamps, commit count,
  comments, review comments, additions, deletions and changed files.
  
- **Source:** <https://github.com/soroushj/ghpr-dataset> (collected by the
  author via the GitHub REST API in October 2020; covers PRs merged
  April 2013 – October 2020).

- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0).

- **Accessed:** November 2026.

## 2. Git history of the same 12 projects — releases and reverts (reliability)

- **What:** treeless clones (commits and tags, no file contents) of the 12
  software projects in GHPR (the 13th, `theupdateframework/specification`,
  is a spec document with no releases and is excluded).

- **Derived by `src/git_history.py`:**
  - `releases.csv` — stable release tags `vX.Y.Z` with publish time
  - `pr_commits.csv` — the commit that merged each PR, and the first stable
    release containing it
  - `reverts.csv` — PRs that were later reverted

- **Source:** `git clone https://github.com/<owner>/<repo>`.

- **Accessed:** November 2026.

## Why these two sources work together

Both come from the same projects, so a pull request in GHPR can be followed
through git to the release that shipped it, and to a revert if it was rolled
back. About 99% of GHPR pull requests are matched to their merge commit,
and the merge time in git equals GHPR's `pull_merged_at` to the second.

## Known limitations

- **GHPR only contains PRs that fixed a linked issue.** It is a sample of
  issue-driven work (mostly bug fixes and requested features), not every PR.
- **Open-source projects are not companies.** There are no sprints, and
  contributors are often volunteers, so absolute times run longer than in a
  typical product team. Comparisons *between* projects and over time are
  more meaningful than the absolute values.

- **"Deployment" means a stable release.** These projects ship software that
  users install; they do not deploy a service. A stable tag (`vX.Y.Z`) is
  the nearest equivalent.

- **Failures are proxies.** There is no incident tracker. Two signals stand
  in for "a change that failed": the PR was later **reverted**, and a release
  was followed by a **hotfix** (patch release in the same line within 7
  days). Both under-count real failures.

- **Review timing is not available.** GHPR has review *comment counts* but no
  review timestamps, so "time to first review" cannot be measured.