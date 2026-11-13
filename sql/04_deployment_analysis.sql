-- 04_deployment_analysis.sql
-- How often does each project ship?
--
-- These projects make software that people download and install, so a stable
-- release (e.g. v1.19.0) is the closest thing to a "deployment".
-- We only count releases from Jan 2015 to Oct 2020, the same period as the
-- pull request data.

SET search_path TO delivery;

-- Releases in the study period, with a link to the next patch ---------------
CREATE OR REPLACE VIEW v_releases AS
SELECT
    repo,
    tag,
    major,
    minor,
    patch,
    released_at,
    EXTRACT(YEAR FROM released_at)::int  AS release_year,
    DATE_TRUNC('month', released_at)::date AS release_month,
    -- LEAD looks at the next row. Here: the next release in the same X.Y line
    -- (e.g. after v1.19.0 comes v1.19.1). Used in 05 to spot hotfixes.
    LEAD(released_at) OVER (PARTITION BY repo, major, minor ORDER BY released_at) AS next_patch_at
FROM releases
WHERE released_at >= '2015-01-01' AND released_at < '2020-11-01';

-- Releases per month for each project --------------------------------------
CREATE OR REPLACE VIEW v_deployment_frequency AS
SELECT
    repo,
    COUNT(*) AS releases,
    -- releases divided by the number of months between first and last release
    ROUND(COUNT(*) / (EXTRACT(EPOCH FROM MAX(released_at) - MIN(released_at)) / (86400 * 30.4))::numeric, 1)
        AS releases_per_month
FROM v_releases
GROUP BY repo;

-- Monthly release counts, for a trend chart ---------------------------------
CREATE OR REPLACE VIEW v_deployment_frequency_monthly AS
SELECT repo, release_month, COUNT(*) AS releases
FROM v_releases
GROUP BY repo, release_month;
