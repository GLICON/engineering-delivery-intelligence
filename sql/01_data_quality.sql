-- 01_data_quality.sql
-- Checks that the loaded data makes sense.
--
-- Each row of the report is one check:
--   problem_rows  how many rows break the rule
--   status        PASS  - no rows break it
--                 FAIL  - a rule that must never break did (stop and investigate)
--                 WARN  - a known gap we can live with (explained in data/README.md)
--                 INFO  - just a row count

SET search_path TO delivery;

CREATE OR REPLACE VIEW data_quality_report AS
WITH checks AS (
    -- How much data do we have?
    SELECT 'Row count: pull_requests' AS check_name, COUNT(*) AS problem_rows, 'INFO' AS if_found
    FROM pull_requests
    UNION ALL SELECT 'Row count: releases', COUNT(*), 'INFO' FROM releases
    UNION ALL SELECT 'Row count: reverts',  COUNT(*), 'INFO' FROM reverts

    -- Rules that must never break
    UNION ALL SELECT 'PR merged before it was opened', COUNT(*), 'FAIL'
    FROM pull_requests WHERE merged_at < created_at

    UNION ALL SELECT 'PR released before it was merged', COUNT(*), 'FAIL'
    FROM pull_requests WHERE first_release_at < merged_at

    UNION ALL SELECT 'PR reverted before it was merged', COUNT(*), 'FAIL'
    FROM pull_requests WHERE reverted_at < merged_at

    UNION ALL SELECT 'Negative line or commit counts', COUNT(*), 'FAIL'
    FROM pull_requests WHERE additions < 0 OR deletions < 0 OR commits < 1

    -- Known gaps
    UNION ALL SELECT 'PR not found in git history', COUNT(*), 'WARN'
    FROM pull_requests WHERE merge_sha IS NULL

    UNION ALL SELECT 'PR never reached a stable release', COUNT(*), 'WARN'
    FROM pull_requests WHERE first_release_at IS NULL

    UNION ALL SELECT 'PR open for more than 2 years', COUNT(*), 'WARN'
    FROM pull_requests WHERE merged_at - created_at > INTERVAL '2 years'
)
SELECT
    check_name,
    problem_rows,
    CASE
        WHEN if_found = 'INFO' THEN 'INFO'
        WHEN problem_rows = 0  THEN 'PASS'
        ELSE if_found
    END AS status
FROM checks;

