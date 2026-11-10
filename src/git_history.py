"""
git_history.py

Read each project's git history and save three tables to data/raw/.

    python src/git_history.py

releases.csv    every stable release (e.g. v1.19.0) and the date it came out
pr_commits.csv  for every pull request: the commit that merged it, and the
                first release that included it
reverts.csv     pull requests that were later undone ("reverted")

GHPR tells us how long review took. These tables add what happened next:
when the change was released, and whether it had to be undone.
"""

import re
import subprocess

import pandas as pd

from config import RAW_DIR, REPOS, SPEC_REPO

# ---------------------------------------------------------------------------
# Patterns used to read git messages
# ---------------------------------------------------------------------------
# A stable release tag looks like "v1.19.0" or "1.19.0".
# Test versions such as "v1.19.0-rc.1" or "v2.0.0-beta" do not match.
STABLE_TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

# How a merged pull request appears in git:
MERGE_COMMIT = re.compile(r"^Merge pull request #(\d+)")  # "Merge pull request #123 from ..."
SQUASH_COMMIT = re.compile(r"\(#(\d+)\)\s*$")             # "Fix the bug (#123)"

# How a revert appears in git:
REVERT_TITLE = re.compile(r'^[Rr]evert:?\s*"(.*)"')                     # 'Revert "Fix the bug (#123)"'
REVERT_BRANCH = re.compile(r"^Merge pull request #\d+ from \S+/revert-(\d+)")  # GitHub's Revert button
REVERTS_COMMIT = re.compile(r"This reverts commit ([0-9a-f]{7,40})")   # line git adds to a revert


def git(repo_folder, *args):
    """Run a git command on one project's history and return its text output."""
    result = subprocess.run(
        ["git", "-C", str(repo_folder), *args],
        capture_output=True, text=True, errors="replace", check=True,
    )
    return result.stdout


# ---------------------------------------------------------------------------
# 1. Releases
# ---------------------------------------------------------------------------
def read_releases(repo_folder, repo):
    """List the project's stable releases, oldest first."""
    # One line per tag: name | commit it points to | date (Unix seconds)
    output = git(repo_folder, "for-each-ref", "refs/tags",
                 "--format=%(refname:short)|%(*objectname)|%(objectname)|%(creatordate:unix)")
    rows = []
    for line in output.splitlines():
        tag, tagged_commit, object_id, timestamp = line.split("|")
        match = STABLE_TAG.match(tag)
        if not match:
            continue  # skip test releases and other tags
        major, minor, patch = (int(x) for x in match.groups())
        rows.append({
            "repo": repo,
            "tag": tag,
            # annotated tags point at a tag object; tagged_commit is the commit behind it
            "commit_sha": tagged_commit or object_id,
            "major": major, "minor": minor, "patch": patch,
            "released_at": pd.to_datetime(int(timestamp), unit="s", utc=True),
        })

    releases = pd.DataFrame(rows).sort_values("released_at")
    # Some projects put two tags on the same commit (Prometheus tags both
    # v3.16.0 and v0.316.0). That is one release, so keep only the first tag.
    releases = releases.drop_duplicates("commit_sha", keep="first")
    return releases.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Commits
# ---------------------------------------------------------------------------
def read_commits(repo_folder):
    """Every commit in the history: id, time, title and message body."""
    # \x1f and \x1e are invisible separator characters that never appear in
    # commit messages, so they are safe to split on.
    output = git(repo_folder, "log", "--all", "--format=%H\x1f%ct\x1f%s\x1f%b\x1e")
    rows = []
    for record in output.split("\x1e"):
        fields = record.strip("\n").split("\x1f")
        if len(fields) == 4:
            sha, timestamp, title, body = fields
            rows.append({"sha": sha, "committed_at": int(timestamp), "title": title, "body": body})
    return pd.DataFrame(rows)


def pr_number_from_title(title):
    """Return the pull request number a commit merged, or None."""
    match = MERGE_COMMIT.match(title) or SQUASH_COMMIT.search(title)
    return int(match.group(1)) if match else None


def reverted_pr_from_commit(title, body, pr_by_sha):
    """Return the pull request number this commit undoes, or None.

    pr_by_sha maps a commit id to the pull request it merged, so that
    'This reverts commit abc123' can be traced back to a pull request.
    """
    # Rule 1: GitHub's Revert button makes a branch called "revert-<number>-..."
    match = REVERT_BRANCH.match(title)
    if match:
        return int(match.group(1))

    if not title.lower().startswith("revert"):
        return None  # not a revert at all

    # Rule 2: the reverted PR's number is inside the quoted title
    match = REVERT_TITLE.match(title)
    if match:
        numbers = re.findall(r"#(\d+)", match.group(1))
        if numbers:
            return int(numbers[-1])

    # Rule 3: follow "This reverts commit <id>" back to its pull request
    for short_sha in REVERTS_COMMIT.findall(body):
        for sha, pr_number in pr_by_sha.items():
            if sha.startswith(short_sha):
                return pr_number
    return None


# ---------------------------------------------------------------------------
# 3. Which release first shipped each commit?
# ---------------------------------------------------------------------------
def first_release_of_each_commit(repo_folder, releases):
    """Map each commit id to the first release that included it.

    Go through releases from oldest to newest. For each one, ask git for the
    commits it contains that no earlier release contained. Those commits
    were shipped for the first time in that release.
    """
    first_release = {}
    earlier_tags = []
    for tag in releases["tag"]:
        new_commits = git(repo_folder, "rev-list", tag, "--not", *earlier_tags)
        for sha in new_commits.split():
            first_release.setdefault(sha, tag)
        earlier_tags.append(tag)
    return first_release


# ---------------------------------------------------------------------------
# Put it together for one project
# ---------------------------------------------------------------------------
def process_project(repo_folder, repo):
    releases = read_releases(repo_folder, repo)
    commits = read_commits(repo_folder)

    # Pull request merge commits. If a PR number shows up more than once
    # (it was copied to a release branch), keep the earliest commit.
    commits["pull_number"] = commits["title"].map(pr_number_from_title)
    pr_commits = (commits.dropna(subset=["pull_number"])
                  .sort_values("committed_at")
                  .drop_duplicates("pull_number"))
    pr_by_sha = dict(zip(pr_commits["sha"], pr_commits["pull_number"].astype(int)))

    # Reverts: keep the first time each pull request was undone.
    commits["reverted_pull_number"] = [
        reverted_pr_from_commit(t, b, pr_by_sha) for t, b in zip(commits["title"], commits["body"])
    ]
    reverts = (commits.dropna(subset=["reverted_pull_number"])
               .sort_values("committed_at")
               .drop_duplicates("reverted_pull_number"))
    reverts = pd.DataFrame({
        "repo": repo,
        "reverted_pull_number": reverts["reverted_pull_number"].astype(int),
        "revert_sha": reverts["sha"],
        "reverted_at": pd.to_datetime(reverts["committed_at"], unit="s", utc=True),
    })

    # First release for each pull request's merge commit
    first_release = first_release_of_each_commit(repo_folder, releases)
    release_dates = dict(zip(releases["tag"], releases["released_at"]))
    pr_commits = pd.DataFrame({
        "repo": repo,
        "pull_number": pr_commits["pull_number"].astype(int),
        "merge_sha": pr_commits["sha"],
        "first_release_tag": pr_commits["sha"].map(first_release),
    })
    pr_commits["first_release_at"] = pr_commits["first_release_tag"].map(release_dates)

    return releases, pr_commits, reverts


if __name__ == "__main__":
    all_releases, all_pr_commits, all_reverts = [], [], []

    for repo in REPOS.values():
        if repo == SPEC_REPO:
            continue
        repo_folder = RAW_DIR / "git" / (repo.replace("/", "_") + ".git")
        releases, pr_commits, reverts = process_project(repo_folder, repo)
        print(f"{repo:32} releases={len(releases):4}  merged PRs found={len(pr_commits):6}  reverts={len(reverts):4}")
        all_releases.append(releases)
        all_pr_commits.append(pr_commits)
        all_reverts.append(reverts)

    pd.concat(all_releases).to_csv(RAW_DIR / "releases.csv", index=False)
    pd.concat(all_pr_commits).to_csv(RAW_DIR / "pr_commits.csv", index=False)
    pd.concat(all_reverts).to_csv(RAW_DIR / "reverts.csv", index=False)
    print("Saved releases.csv, pr_commits.csv and reverts.csv in data/raw/")
