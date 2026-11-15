"""
feature_engineering.py

Builds one table with a row per pull request and the "features" we want to
test: things about a PR that might explain why it was slow.

Used by analysis.py and the notebook:

    from feature_engineering import load_features
    df = load_features()
"""

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

from config import database_url

# Pull the PR data from the SQL view built in sql/03_pr_analysis.sql,
# plus a few extra columns from the main table.
QUERY = """
SELECT f.*, p.created_at
FROM delivery.v_pr_features f
JOIN delivery.pull_requests p USING (repo, pull_number)
"""

# Issue raised by a maintainer of the project?
QUERY_ISSUES = """
SELECT repo, pull_number,
       BOOL_OR(issue_author_role NOT IN ('MEMBER', 'OWNER', 'COLLABORATOR')) AS issue_from_outsider
FROM delivery.pr_issues
GROUP BY repo, pull_number
"""


def load_features():
    engine = create_engine(database_url())
    df = pd.read_sql(QUERY, engine)
    df = df.merge(pd.read_sql(QUERY_ISSUES, engine), on=["repo", "pull_number"], how="left")

    # Yes/no features as 1/0 so they can go into a regression
    df["issue_from_outsider"] = df["issue_from_outsider"].fillna(False).astype(int)
    df["opened_on_weekend"] = (pd.to_datetime(df["created_at"], utc=True).dt.dayofweek >= 5).astype(int)
    df["fixes_several_issues"] = (df["linked_issues"] > 1).astype(int)

    # Sizes and times are very uneven (most PRs are small, a few are huge).
    # Taking log2 evens them out: +1 on a log2 scale means "twice as big".
    # We add 1 first because log2(0) is undefined.
    for col in ["lines_changed", "changed_files", "commits", "review_comments"]:
        df[f"log2_{col}"] = np.log2(df[col] + 1)

    # Natural log of time to merge. Adding 1 hour (1/24 day) avoids log(0)
    # for PRs merged within seconds.
    df["log_cycle_days"] = np.log(df["cycle_days"] + 1 / 24)
    return df
