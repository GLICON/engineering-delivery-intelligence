-- 03_pr_analysis.sql
-- Which pull requests are slow, and which ones get reverted?
-- We group PRs by size and by how much review discussion they had.

SET search_path TO delivery;

-- Each PR with its size group and review group --------------------------------
CREATE OR REPLACE VIEW v_pr_features AS
SELECT
    p.repo,
    p.pull_number,
    t.merged_year,
    p.additions + p.deletions AS lines_changed,
    p.changed_files,
    p.commits,
    p.review_comments,
    p.linked_issues,
    t.cycle_days,
    t.lead_time_days,
    p.was_reverted,
    -- The numbers in front ("1.", "2.") make the groups sort in the right order
    CASE
        WHEN p.additions + p.deletions < 10   THEN '1. XS (<10)'
        WHEN p.additions + p.deletions < 100  THEN '2. S (10-99)'
        WHEN p.additions + p.deletions < 500  THEN '3. M (100-499)'
        WHEN p.additions + p.deletions < 1000 THEN '4. L (500-999)'
        ELSE                                       '5. XL (1000+)'
    END AS size_group,
    CASE
        WHEN p.review_comments = 0   THEN '1. None'
        WHEN p.review_comments <= 3  THEN '2. 1-3'
        WHEN p.review_comments <= 10 THEN '3. 4-10'
        ELSE                              '4. More than 10'
    END AS review_group
FROM pull_requests p
JOIN v_pr_timeline t USING (repo, pull_number);

-- Speed and revert rate by PR size ------------------------------------------
CREATE OR REPLACE VIEW v_size_summary AS
SELECT
    size_group,
    COUNT(*) AS prs,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cycle_days)::numeric, 1) AS median_cycle_days,
    -- AVG of true/false (as 1/0) = the share that were reverted
    ROUND(100 * AVG(was_reverted::int), 2) AS revert_rate_pct
FROM v_pr_features
GROUP BY size_group;

-- Speed and revert rate by amount of review discussion -----------------------
CREATE OR REPLACE VIEW v_review_summary AS
SELECT
    review_group,
    COUNT(*) AS prs,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cycle_days)::numeric, 1) AS median_cycle_days,
    ROUND(100 * AVG(was_reverted::int), 2) AS revert_rate_pct
FROM v_pr_features
GROUP BY review_group;
