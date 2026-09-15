-- BUILD C. user_first: each user's first active date and cohort week
CREATE OR REPLACE TABLE user_first AS
SELECT user_id,
       MIN(event_date)                        AS first_date,
       DATE_TRUNC('week', MIN(event_date))    AS cohort_week
FROM events
GROUP BY user_id;

-- BUILD D. user_retention: one row per user who had at least 7 days to come back (eligible users only)
CREATE OR REPLACE TABLE user_retention AS
WITH mx AS (SELECT MAX(event_date) AS max_d FROM events),
first_session AS (
    SELECT user_id, has_cart, has_purchase,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY start_ts) AS rn
    FROM session_funnel
),
elig AS (
    SELECT f.user_id, f.first_date, f.cohort_week
    FROM user_first f, mx
    WHERE f.first_date <= mx.max_d - 7
)
SELECT e.user_id, e.first_date, e.cohort_week,
       CASE WHEN fs.has_purchase = 1 THEN '1_purchased'
            WHEN fs.has_cart = 1     THEN '2_carted_no_purchase'
            ELSE '3_viewed_only' END                                              AS first_session_outcome,
       MAX(CASE WHEN d.event_date = e.first_date + 1 THEN 1 ELSE 0 END)           AS d1,
       MAX(CASE WHEN d.event_date = e.first_date + 7 THEN 1 ELSE 0 END)           AS d7,
       MAX(CASE WHEN d.event_date BETWEEN e.first_date + 1 AND e.first_date + 7
                THEN 1 ELSE 0 END)                                                AS back_within_7d
FROM elig e
JOIN first_session fs ON fs.user_id = e.user_id AND fs.rn = 1
LEFT JOIN (SELECT DISTINCT user_id, event_date FROM events) d ON d.user_id = e.user_id
GROUP BY e.user_id, e.first_date, e.cohort_week, fs.has_purchase, fs.has_cart;

-- 1. Overall retention (eligible users only)
SELECT COUNT(*)                                   AS users,
       ROUND(100.0 * AVG(d1), 2)                  AS d1_pct,
       ROUND(100.0 * AVG(d7), 2)                  AS d7_pct,
       ROUND(100.0 * AVG(back_within_7d), 2)      AS back_within_7d_pct
FROM user_retention;

-- 2. Retention by weekly cohort (is it improving or worsening?)
SELECT cohort_week, COUNT(*) AS users,
       ROUND(100.0 * AVG(d1), 2)               AS d1_pct,
       ROUND(100.0 * AVG(d7), 2)               AS d7_pct,
       ROUND(100.0 * AVG(back_within_7d), 2)   AS back_within_7d_pct
FROM user_retention
GROUP BY 1 ORDER BY 1;

-- 3. Does a purchase in the first session drive coming back?
SELECT first_session_outcome, COUNT(*) AS users,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_of_users_pct,
       ROUND(100.0 * AVG(d1), 2)               AS d1_pct,
       ROUND(100.0 * AVG(back_within_7d), 2)   AS back_within_7d_pct
FROM user_retention
GROUP BY 1 ORDER BY 1;

-- 4. Weekly cohort retention triangle (percent of cohort active N calendar weeks later)
WITH act AS (SELECT DISTINCT user_id, DATE_TRUNC('week', event_date) AS act_week FROM events),
cohort AS (SELECT cohort_week, COUNT(*) AS cohort_size FROM user_first GROUP BY 1),
x AS (
    SELECT f.cohort_week,
           CAST(date_diff('week', f.cohort_week, a.act_week) AS INTEGER) AS wk,
           COUNT(DISTINCT a.user_id) AS active
    FROM user_first f JOIN act a ON a.user_id = f.user_id
    GROUP BY 1, 2
)
SELECT x.cohort_week, c.cohort_size,
       ROUND(100.0 * SUM(CASE WHEN wk = 1 THEN active END) / c.cohort_size, 2) AS week_1_pct,
       ROUND(100.0 * SUM(CASE WHEN wk = 2 THEN active END) / c.cohort_size, 2) AS week_2_pct,
       ROUND(100.0 * SUM(CASE WHEN wk = 3 THEN active END) / c.cohort_size, 2) AS week_3_pct,
       ROUND(100.0 * SUM(CASE WHEN wk = 4 THEN active END) / c.cohort_size, 2) AS week_4_pct
FROM x JOIN cohort c ON c.cohort_week = x.cohort_week
GROUP BY x.cohort_week, c.cohort_size
ORDER BY 1;

-- 5. Repeat purchase rate (purchasers who bought on 2+ different days)
WITH p AS (
    SELECT user_id, COUNT(DISTINCT event_date) AS purchase_days
    FROM events WHERE event_type = 'purchase' GROUP BY user_id
)
SELECT COUNT(*)                                                         AS purchasers,
       SUM(CASE WHEN purchase_days >= 2 THEN 1 ELSE 0 END)              AS repeat_purchasers,
       ROUND(100.0 * SUM(CASE WHEN purchase_days >= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_purchase_pct
FROM p;

-- 6. Days between first and second purchase day (repeat purchasers only)
WITH pd AS (SELECT DISTINCT user_id, event_date FROM events WHERE event_type = 'purchase'),
r AS (SELECT user_id, event_date, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_date) AS rn FROM pd)
SELECT COUNT(*)                                                  AS repeat_purchasers,
       MEDIAN(date_diff('day', a.event_date, b.event_date))      AS median_days_to_2nd_purchase,
       ROUND(AVG(date_diff('day', a.event_date, b.event_date)), 1) AS avg_days_to_2nd_purchase
FROM r a JOIN r b ON a.user_id = b.user_id AND a.rn = 1 AND b.rn = 2