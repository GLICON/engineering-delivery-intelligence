"""
Tests for cleaning.py.

Each test builds a tiny made-up table, runs one cleaning function on it,
and checks the result is what we expect.
"""

import pandas as pd

from cleaning import make_pull_requests, remove_impossible_rows


def ghpr_row(**changes):
    """One fake GHPR row. Pass keyword arguments to change any value."""
    row = {
        "repo": "a/b", "pull_number": 1, "issue_number": 10,
        "issue_created_at": 1_600_000_000,
        "pull_created_at": 1_600_000_100,
        "pull_merged_at": 1_600_086_500,   # exactly one day after created
        "pull_comments": 2, "pull_review_comments": 3, "pull_commits": 1,
        "pull_additions": 10, "pull_deletions": 5, "pull_changed_files": 2,
    }
    row.update(changes)
    return row


def test_pr_that_fixed_two_issues_becomes_one_row():
    ghpr = pd.DataFrame([ghpr_row(issue_number=10), ghpr_row(issue_number=11)])
    prs = make_pull_requests(ghpr)
    assert len(prs) == 1
    assert prs.loc[0, "linked_issues"] == 2


def test_dates_are_converted():
    prs = make_pull_requests(pd.DataFrame([ghpr_row()]))
    time_to_merge = prs.loc[0, "merged_at"] - prs.loc[0, "created_at"]
    assert time_to_merge == pd.Timedelta(days=1)


def test_impossible_pull_requests_are_removed():
    ghpr = pd.DataFrame([
        ghpr_row(pull_number=1),                                # fine
        ghpr_row(pull_number=2, pull_merged_at=1_500_000_000),  # merged before created
        ghpr_row(pull_number=3, pull_commits=0),                # no commits
    ])
    prs = remove_impossible_rows(make_pull_requests(ghpr))
    assert prs["pull_number"].tolist() == [1]
