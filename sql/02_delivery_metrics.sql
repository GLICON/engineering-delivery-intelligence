-- 02_delivery_metrics.sql
-- How long does a change take, and where does the time go?
--
-- Every change goes through three stages:
--   1. Waiting to be picked up   issue reported -> PR opened
--   2. Review and merge          PR opened      -> PR merged    (= "cycle time")
--   3. Waiting to ship           PR merged      -> first release
-- "Lead time" = PR opened -> released (stages 2 + 3).
--
-- We use the MEDIAN (the middle value) instead of the average, because a few
-- PRs stay open for years and would drag an average up.
-- PERCENTILE_CONT(0.5) is how PostgreSQL calculates a median.

SET search_path TO delivery;

-- One row per pull request with each stage measured in days -----------------
CREATE OR REPLACE VIEW v_pr_timeline AS
SELECT
    repo,
    pull_number,
    merged_at,
    DATE_TRUNC('month', merged_at)::date AS merged_month,
    EXTRACT(YEAR FROM merged_at)::int    AS merged_year,
    was_reverted,
    -- EXTRACT(EPOCH ...) gives seconds; dividing by 86400 turns that into days.
    -- GREATEST(..., 0): sometimes the PR came before the issue was written up.
    GREATEST(EXTRACT(EPOCH FROM created_at - first_issue_created_at), 0) / 86400 AS pickup_days,
    EXTRACT(EPOCH FROM merged_at - created_at) / 86400         AS cycle_days,
    EXTRACT(EPOCH FROM first_release_at - merged_at) / 86400   AS release_wait_days,
    EXTRACT(EPOCH FROM first_release_at - created_at) / 86400  AS lead_time_days
FROM pull_requests
WHERE repo <> 'theupdateframework/specification';   -- a document, not software

-- Median days in each stage, per project ---------------------------------
CREATE OR REPLACE VIEW v_stage_breakdown AS
SELECT repo, '1. Waiting to be picked up' AS stage,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pickup_days)::numeric, 1) AS median_days
FROM v_pr_timeline GROUP BY repo
UNION ALL
SELECT repo, '2. Review and merge',
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cycle_days)::numeric, 1)
FROM v_pr_timeline GROUP BY repo
UNION ALL
SELECT repo, '3. Waiting to ship',
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY release_wait_days)::numeric, 1)
FROM v_pr_timeline GROUP BY repo;

-- Headline speed numbers per project ---------------------------------------
CREATE OR REPLACE VIEW v_delivery_by_repo AS
SELECT
    repo,
    COUNT(*) AS prs_merged,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cycle_days)::numeric, 1)     AS median_cycle_days,
    ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY cycle_days)::numeric, 1)     AS p90_cycle_days,  -- 90% of PRs are faster than this
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lead_time_days)::numeric, 1) AS median_lead_time_days
FROM v_pr_timeline
GROUP BY repo;

-- Month by month, for trend charts -----------------------------------------
CREATE OR REPLACE VIEW v_delivery_monthly AS
SELECT
    repo,
    merged_month,
    COUNT(*) AS prs_merged,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cycle_days)::numeric, 1) AS median_cycle_days
FROM v_pr_timeline
GROUP BY repo, merged_month;
