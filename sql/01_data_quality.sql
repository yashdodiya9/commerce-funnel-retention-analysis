-- 1. Volume and date range
SELECT COUNT(*) AS events, COUNT(DISTINCT user_id) AS users, COUNT(DISTINCT user_session) AS sessions,
       MIN(event_date) AS first_day, MAX(event_date) AS last_day
FROM events;

-- 2. Events by type (view should be largest, purchase smallest)
SELECT event_type, COUNT(*) AS n, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM events GROUP BY 1 ORDER BY n DESC;

-- 3. Null / bad value checks
SELECT SUM(CASE WHEN category_code = 'unknown' THEN 1 ELSE 0 END) AS unknown_category,
       SUM(CASE WHEN brand = 'unknown' THEN 1 ELSE 0 END) AS unknown_brand,
       SUM(CASE WHEN price IS NULL OR price <= 0 THEN 1 ELSE 0 END) AS bad_price
FROM events;

-- 4. Exact duplicate rows
SELECT COUNT(*) AS duplicate_groups FROM (
  SELECT event_ts, event_type, product_id, user_id, user_session, COUNT(*) c
  FROM events GROUP BY ALL HAVING COUNT(*) > 1
);

-- 5. Purchase sessions with no view event (tracking gaps affect funnel logic)
WITH s AS (
  SELECT user_session,
         MAX(CASE WHEN event_type='view' THEN 1 ELSE 0 END)     AS has_view,
         MAX(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS has_purchase
  FROM events GROUP BY 1)
SELECT COUNT(*) FILTER (WHERE has_purchase = 1) AS purchase_sessions,
       COUNT(*) FILTER (WHERE has_purchase = 1 AND has_view = 0) AS purchase_without_view
FROM s;

-- 6. Daily volume, first 10 days (look for gaps or spikes)
SELECT event_date, COUNT(*) AS events, COUNT(DISTINCT user_id) AS dau
FROM events GROUP BY 1 ORDER BY 1 LIMIT 10;

-- 7. One-day vs returning users (preview of retention)
WITH u AS (SELECT user_id, COUNT(DISTINCT event_date) AS active_days FROM events GROUP BY 1)
SELECT CASE WHEN active_days = 1 THEN '1 day' WHEN active_days <= 3 THEN '2-3 days' ELSE '4+ days' END AS bucket,
       COUNT(*) AS users, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM u GROUP BY 1 ORDER BY 1
