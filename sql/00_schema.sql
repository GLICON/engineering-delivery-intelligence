-- 00_schema.sql
-- Creates the tables that hold the cleaned data.
-- Everything lives in its own schema called "delivery". Running this file
-- again wipes and rebuilds it, so it is safe to re-run.

DROP SCHEMA IF EXISTS delivery CASCADE;
CREATE SCHEMA delivery;
SET search_path TO delivery;

-- Stable releases of each project (one row per release)
CREATE TABLE releases (
    repo         TEXT        NOT NULL,
    tag          TEXT        NOT NULL,   -- e.g. v1.19.0
    commit_sha   TEXT        NOT NULL,
    major        INT         NOT NULL,   -- 1 in v1.19.0
    minor        INT         NOT NULL,   -- 19 in v1.19.0
    patch        INT         NOT NULL,   -- 0 in v1.19.0
    released_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (repo, tag)
);

-- Merged pull requests (one row per pull request)
CREATE TABLE pull_requests (
    repo                    TEXT        NOT NULL,
    pull_number             INT         NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL,   -- PR opened
    merged_at               TIMESTAMPTZ NOT NULL,   -- PR merged
    comments                INT         NOT NULL,
    review_comments         INT         NOT NULL,
    commits                 INT         NOT NULL,
    additions               INT         NOT NULL,   -- lines added
    deletions               INT         NOT NULL,   -- lines removed
    changed_files           INT         NOT NULL,
    linked_issues           INT         NOT NULL,   -- issues this PR fixed
    first_issue_created_at  TIMESTAMPTZ NOT NULL,   -- when the problem was first reported
    merge_sha               TEXT,                   -- blank if not found in git
    first_release_tag       TEXT,                   -- blank if never released
    first_release_at        TIMESTAMPTZ,
    reverted_at             TIMESTAMPTZ,            -- blank if never reverted
    was_reverted            BOOLEAN     NOT NULL,
    PRIMARY KEY (repo, pull_number),
    FOREIGN KEY (repo, first_release_tag) REFERENCES releases (repo, tag)
);

-- The issues each pull request fixed
CREATE TABLE pr_issues (
    repo               TEXT        NOT NULL,
    pull_number        INT         NOT NULL,
    issue_number       INT         NOT NULL,
    issue_created_at   TIMESTAMPTZ NOT NULL,
    issue_title        TEXT,
    issue_author_role  TEXT,       -- e.g. MEMBER, CONTRIBUTOR
    PRIMARY KEY (repo, pull_number, issue_number),
    FOREIGN KEY (repo, pull_number) REFERENCES pull_requests (repo, pull_number)
);

-- Every revert found in the git history
CREATE TABLE reverts (
    repo                  TEXT        NOT NULL,
    reverted_pull_number  INT         NOT NULL,
    revert_sha            TEXT        NOT NULL,
    reverted_at           TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (repo, reverted_pull_number)
);
