-- BUILD A. session_funnel: one row per session with 0/1 flags per stage
CREATE OR REPLACE TABLE session_funnel AS
SELECT
    user_session,
    ANY_VALUE(user_id) AS user_id,
    MIN(event_ts) AS start_ts,
    CAST(MIN(event_ts) AS DATE) AS start_date,
    EXTRACT(hour FROM MIN(event_ts)) AS start_hour,
    dayname(MIN(event_ts)) AS start_dow,
    MAX(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS has_view,
    MAX(CASE WHEN event_type = 'cart' THEN 1 ELSE 0 END) AS has_cart,
    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS has_purchase
FROM events
GROUP BY user_session;

-- BUILD B. session_category: one row per (session, top-level category), so category funnels are fair
CREATE OR REPLACE TABLE session_category AS
SELECT
    user_session,
    category_l1,
    MAX(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS has_view,
    MAX(CASE WHEN event_type = 'cart' THEN 1 ELSE 0 END) AS has_cart,
    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS has_purchase
FROM events
GROUP BY user_session, category_l1;


-- 1. Overall session funnel
SELECT
    COUNT(*) AS sessions,
    SUM(has_view) AS viewed,
    SUM(has_cart) AS carted,
    SUM(has_purchase) AS purchased,
    ROUND(100.0 * SUM(has_cart)     / SUM(has_view), 2) AS view_to_cart_pct,
    ROUND(100.0 * SUM(has_purchase) / SUM(has_cart), 2) AS cart_to_purchase_pct_raw,
    ROUND(100.0 * SUM(has_purchase) / SUM(has_view), 2) AS view_to_purchase_pct
FROM session_funnel;

-- 2. Strict vs loose funnel (purchases without a cart event are a tracking quirk, not a bug in the SQL)
SELECT
    SUM(CASE WHEN has_view=1 AND has_cart=1 AND has_purchase=1 THEN 1 ELSE 0 END) AS strict_view_cart_purchase,
    SUM(CASE WHEN has_purchase=1 AND has_cart=0 THEN 1 ELSE 0 END) AS purchase_without_cart,
    ROUND(100.0 * SUM(CASE WHEN has_purchase=1 AND has_cart=0 THEN 1 ELSE 0 END)
          / NULLIF(SUM(has_purchase),0), 1) AS pct_purchases_without_cart,
    ROUND(100.0 * SUM(CASE WHEN has_view=1 AND has_cart=1 AND has_purchase=1 THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN has_cart=1 THEN 1 ELSE 0 END),0), 2) AS strict_cart_to_purchase_pct
FROM session_funnel;

-- 3. Cart abandonment (sessions with a cart but no purchase)
SELECT
    SUM(has_cart) AS cart_sessions,
    SUM(CASE WHEN has_cart=1 AND has_purchase=0 THEN 1 ELSE 0 END) AS abandoned_sessions,
    ROUND(100.0 * SUM(CASE WHEN has_cart=1 AND has_purchase=0 THEN 1 ELSE 0 END)
          / SUM(has_cart), 2) AS cart_abandonment_pct
FROM session_funnel;

-- 4. Funnel by hour of day (UTC)
SELECT start_hour,
       SUM(has_view) AS viewed, SUM(has_cart) AS carted, SUM(has_purchase) AS purchased,
       ROUND(100.0 * SUM(has_cart)     / NULLIF(SUM(has_view),0), 2) AS view_to_cart_pct,
       ROUND(100.0 * SUM(has_purchase) / NULLIF(SUM(has_view),0), 2) AS view_to_purchase_pct
FROM session_funnel
GROUP BY 1 ORDER BY 1;

-- 5. Funnel by day of week
SELECT start_dow,
       SUM(has_view) AS viewed,
       ROUND(100.0 * SUM(has_cart)     / NULLIF(SUM(has_view),0), 2) AS view_to_cart_pct,
       ROUND(100.0 * SUM(has_purchase) / NULLIF(SUM(has_view),0), 2) AS view_to_purchase_pct
FROM session_funnel
GROUP BY 1 ORDER BY view_to_purchase_pct DESC;

-- 6. Funnel by top-level category (min 5000 viewing sessions, so rates are stable)
SELECT category_l1,
       SUM(has_view) AS viewed,
       ROUND(100.0 * SUM(has_cart)     / NULLIF(SUM(has_view),0), 2) AS view_to_cart_pct,
       ROUND(100.0 * SUM(has_purchase) / NULLIF(SUM(has_cart),0), 2) AS cart_to_purchase_pct_raw,
       ROUND(100.0 * SUM(has_purchase) / NULLIF(SUM(has_view),0), 2) AS view_to_purchase_pct
FROM session_category
GROUP BY 1
HAVING SUM(has_view) >= 5000
ORDER BY viewed DESC;

-- 7. Abandoned carts: did the same user buy anything within 7 days after the abandoned session?
WITH abandoned AS (
    SELECT user_session, user_id, start_ts FROM session_funnel
    WHERE has_cart = 1 AND has_purchase = 0
),
later_purchase AS (
    SELECT a.user_session,
           MAX(CASE WHEN p.start_ts > a.start_ts AND p.start_ts <= a.start_ts + INTERVAL 7 DAY THEN 1 ELSE 0 END) AS bought_within_7d
    FROM abandoned a
    LEFT JOIN session_funnel p ON p.user_id = a.user_id AND p.has_purchase = 1
    GROUP BY a.user_session
)
SELECT COUNT(*)                                                AS abandoned_sessions,
       SUM(bought_within_7d)                                   AS recovered_within_7d,
       ROUND(100.0 * SUM(bought_within_7d) / COUNT(*), 2)      AS recovery_rate_pct
FROM later_purchase