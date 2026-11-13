-- 05_incident_analysis.sql
-- How often do changes fail, and how quickly are they fixed?
--
-- These projects have no public incident log, so we use two signs of failure:
--   Hotfix  - a release followed by a quick patch (same X.Y line, within 7 days).
--             The first release "failed"; the gap is the time to restore.
--   Revert  - a merged pull request that was later undone.
-- Both miss some real failures, so they are best for comparing projects.

SET search_path TO delivery;

-- Did each release need a hotfix? ------------------------------------------
CREATE OR REPLACE VIEW v_release_failures AS
SELECT
    repo,
    tag,
    released_at,
    release_year,
    COALESCE(next_patch_at - released_at <= INTERVAL '7 days', FALSE) AS needed_hotfix,
    CASE WHEN next_patch_at - released_at <= INTERVAL '7 days'
         THEN EXTRACT(EPOCH FROM next_patch_at - released_at) / 86400 END AS days_to_restore
FROM v_releases;

-- Reliability per project ----------------------------------------------------
CREATE OR REPLACE VIEW v_reliability_by_repo AS
WITH release_stats AS (
    SELECT
        repo,
        COUNT(*) AS releases,
        ROUND(100 * AVG(needed_hotfix::int), 1) AS change_failure_rate_pct,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_to_restore)::numeric, 1) AS median_days_to_restore
    FROM v_release_failures
    GROUP BY repo
),
pr_stats AS (
    SELECT repo, ROUND(100 * AVG(was_reverted::int), 2) AS revert_rate_pct
    FROM v_pr_timeline
    GROUP BY repo
)
SELECT *
FROM pr_stats
LEFT JOIN release_stats USING (repo);

-- Year by year: is it getting faster, and is it breaking more? ----------------
CREATE OR REPLACE VIEW v_speed_vs_reliability_yearly AS
WITH speed AS (
    SELECT
        merged_year AS year,
        COUNT(*) AS prs_merged,
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cycle_days)::numeric, 1) AS median_cycle_days,
        ROUND(100 * AVG(was_reverted::int), 2) AS revert_rate_pct
    FROM v_pr_timeline
    WHERE merged_year BETWEEN 2015 AND 2020
    GROUP BY merged_year
),
reliability AS (
    SELECT
        release_year AS year,
        COUNT(*) AS releases,
        ROUND(100 * AVG(needed_hotfix::int), 1) AS change_failure_rate_pct
    FROM v_release_failures
    GROUP BY release_year
)
SELECT *
FROM speed
JOIN reliability USING (year)
ORDER BY year;

-- The four DORA measures side by side, one row per project -------------------
CREATE OR REPLACE VIEW v_dora_summary AS
SELECT
    d.repo,
    f.releases_per_month,          -- 1. deployment frequency
    d.median_lead_time_days,       -- 2. lead time for changes
    r.change_failure_rate_pct,     -- 3. change failure rate
    r.median_days_to_restore,      -- 4. time to restore
    r.revert_rate_pct,
    d.median_cycle_days,
    d.prs_merged
FROM v_delivery_by_repo d
LEFT JOIN v_deployment_frequency f USING (repo)
LEFT JOIN v_reliability_by_repo  r USING (repo);
