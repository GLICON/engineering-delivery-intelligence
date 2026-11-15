"""
cleaning.py

Step 2: turn the raw files into tidy tables in data/processed/.

    python src/cleaning.py

Problems this fixes:
- GHPR has one row per *issue*. A pull request that fixed three issues
  appears three times, so we split it into two tables:
      pull_requests.csv  one row per pull request
      pr_issues.csv      one row per (pull request, issue) pair
- Dates arrive as Unix seconds (e.g. 1600000000). We turn them into real
  dates in UTC.
- Rows that cannot be true (merged before they were created, no commits)
  are removed.
- Release and revert information from git is added to each pull request.
"""

import pandas as pd

from config import AUTHOR_ROLES, PROCESSED_DIR, RAW_DIR, REPOS

# Columns in GHPR that describe the pull request itself (not the issue).
# GHPR prefixes them with "pull_"; we drop the prefix to keep names short.
PR_COLUMNS = {
    "pull_created_at": "created_at",
    "pull_merged_at": "merged_at",
    "pull_comments": "comments",
    "pull_review_comments": "review_comments",
    "pull_commits": "commits",
    "pull_additions": "additions",
    "pull_deletions": "deletions",
    "pull_changed_files": "changed_files",
}


def to_date(unix_seconds):
    """Unix seconds -> UTC date and time."""
    return pd.to_datetime(unix_seconds, unit="s", utc=True)


def make_pull_requests(ghpr):
    """One row per pull request, with how many issues it fixed."""
    prs = (
        ghpr.groupby(["repo", "pull_number"])
        .agg(
            # PR columns are identical on every row of the same PR, so take the first
            **{new: (old, "first") for old, new in PR_COLUMNS.items()},
            linked_issues=("issue_number", "nunique"),
            first_issue_created_at=("issue_created_at", "min"),
        )
        .reset_index()
    )
    for col in ["created_at", "merged_at", "first_issue_created_at"]:
        prs[col] = to_date(prs[col])
    return prs


def make_pr_issues(ghpr):
    """One row per (pull request, issue it fixed)."""
    issues = ghpr[["repo", "pull_number", "issue_number", "issue_created_at",
                   "issue_author_association", "issue_title"]].copy()
    issues["issue_created_at"] = to_date(issues["issue_created_at"])
    # A few titles contain hidden line-break characters, which would split
    # the row in two when saved as CSV. Replace them with a space.
    issues["issue_title"] = issues["issue_title"].str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    issues["issue_author_role"] = issues.pop("issue_author_association").map(AUTHOR_ROLES)
    return issues.drop_duplicates(["repo", "pull_number", "issue_number"])


def remove_impossible_rows(prs):
    """Drop pull requests whose numbers cannot be right."""
    merged_before_created = prs["merged_at"] < prs["created_at"]
    no_commits = prs["commits"] == 0
    bad = merged_before_created | no_commits
    print(f"Removed {bad.sum()} impossible pull requests "
          f"({merged_before_created.sum()} merged before created, {no_commits.sum()} with no commits)")
    return prs[~bad].reset_index(drop=True)


def add_git_information(prs, pr_commits, reverts):
    """Add the merge commit, first release and revert date to each pull request."""
    # Merge commit and first release (left join keeps PRs with no match)
    pr_commits = pr_commits.copy()
    pr_commits["first_release_at"] = pd.to_datetime(pr_commits["first_release_at"], utc=True)
    prs = prs.merge(pr_commits, on=["repo", "pull_number"], how="left")

    # A release dated *before* the merge means a tag was moved later on.
    # We cannot trust that link, so we blank it out.
    bad_release = prs["first_release_at"] < prs["merged_at"]
    prs.loc[bad_release, ["first_release_tag", "first_release_at"]] = None
    print(f"Blanked {bad_release.sum()} release links dated before the merge")

    # Revert date (blank if the PR was never reverted)
    reverts = reverts.rename(columns={"reverted_pull_number": "pull_number"})
    reverts["reverted_at"] = pd.to_datetime(reverts["reverted_at"], utc=True)
    prs = prs.merge(reverts[["repo", "pull_number", "reverted_at"]],
                    on=["repo", "pull_number"], how="left")

    # A "revert" before the merge is a number mix-up, not a real revert.
    prs.loc[prs["reverted_at"] < prs["merged_at"], "reverted_at"] = pd.NaT
    prs["was_reverted"] = prs["reverted_at"].notna()
    return prs


if __name__ == "__main__":
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Read GHPR and give each project its name
    ghpr = pd.read_csv(RAW_DIR / "ghpr.csv")
    ghpr["repo"] = ghpr["repo_id"].map(REPOS)

    # 2. Split into pull requests and issues, and remove bad rows
    prs = remove_impossible_rows(make_pull_requests(ghpr))
    issues = make_pr_issues(ghpr)
    issues = issues.merge(prs[["repo", "pull_number"]])  # only issues of kept PRs

    # 3. Add what happened after the merge (release, revert)
    releases = pd.read_csv(RAW_DIR / "releases.csv")
    reverts = pd.read_csv(RAW_DIR / "reverts.csv")
    prs = add_git_information(prs, pd.read_csv(RAW_DIR / "pr_commits.csv"), reverts)

    # 4. Save
    prs.to_csv(PROCESSED_DIR / "pull_requests.csv", index=False)
    issues.to_csv(PROCESSED_DIR / "pr_issues.csv", index=False)
    releases.to_csv(PROCESSED_DIR / "releases.csv", index=False)
    reverts.to_csv(PROCESSED_DIR / "reverts.csv", index=False)
    print(f"Saved {len(prs)} pull requests, {len(issues)} issue links, "
          f"{len(releases)} releases and {len(reverts)} reverts to data/processed/")