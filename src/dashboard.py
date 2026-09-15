"""Streamlit dashboard. Run from the project root:  streamlit run src/dashboard.py
Needs data/events.duckdb plus the tables built by sql/02_funnel.sql and sql/03_retention.sql."""
import duckdb, pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(page_title="Funnel & Retention", layout="wide")

@st.cache_resource
def con():
    return duckdb.connect("data/events.duckdb", read_only=True)

@st.cache_data
def q(sql: str) -> pd.DataFrame:
    return con().execute(sql).fetchdf()

st.title("E-commerce funnel, cohort & retention (REES46, Oct 2019)")
st.caption("5% random sample of users (by hashed user_id), all of their events. Hours are UTC.")

# ---------- KPI row ----------
f = q("""SELECT COUNT(*) AS sessions, SUM(has_view) AS viewed, SUM(has_cart) AS carted,
                SUM(has_purchase) AS purchased,
                SUM(CASE WHEN has_cart=1 AND has_purchase=0 THEN 1 ELSE 0 END) AS abandoned,
                SUM(CASE WHEN has_purchase=1 AND has_cart=0 THEN 1 ELSE 0 END) AS buy_no_cart
         FROM session_funnel""").iloc[0]
r = q("SELECT COUNT(*) AS users, AVG(back_within_7d) AS back7 FROM user_retention").iloc[0]
rp = q("""WITH p AS (SELECT user_id, COUNT(DISTINCT event_date) AS d FROM events
                     WHERE event_type='purchase' GROUP BY 1)
          SELECT AVG(CASE WHEN d >= 2 THEN 1.0 ELSE 0 END) AS rate FROM p""").iloc[0]

c = st.columns(5)
c[0].metric("Sessions", f"{int(f.sessions):,}")
c[1].metric("View → purchase", f"{100*f.purchased/f.viewed:.2f}%")
c[2].metric("Cart abandonment", f"{100*f.abandoned/f.carted:.1f}%")
c[3].metric("Back within 7 days", f"{100*r.back7:.1f}%")
c[4].metric("Repeat purchasers", f"{100*rp.rate:.1f}%")

tab1, tab2, tab3 = st.tabs(["Funnel", "Retention", "Data notes"])

# ---------- Funnel ----------
with tab1:
    left, right = st.columns(2)
    stages = pd.DataFrame({"stage": ["Viewed", "Carted", "Purchased"],
                           "sessions": [f.viewed, f.carted, f.purchased]})
    left.plotly_chart(px.bar(stages, x="stage", y="sessions", text="sessions",
                             title="Sessions reaching each stage"))
    left.caption(f"{100*f.buy_no_cart/f.purchased:.1f}% of purchase sessions have no cart event, "
                 "so purchased can exceed carted. Use view→purchase as the primary conversion metric.")

    h = q("""SELECT start_hour, SUM(has_view) AS sessions,
                    100.0*SUM(has_purchase)/NULLIF(SUM(has_view),0) AS conv
             FROM session_funnel GROUP BY 1 ORDER BY 1""")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=h.start_hour, y=h.sessions, name="Sessions", secondary_y=False)
    fig.add_scatter(x=h.start_hour, y=h.conv, name="View→purchase %", secondary_y=True, mode="lines+markers")
    fig.update_layout(title="Traffic vs conversion by hour (UTC)")
    right.plotly_chart(fig)

    min_n = st.number_input("Min viewing sessions per category", 100, 50000, 5000, step=500)
    cat = q(f"""SELECT category_l1, SUM(has_view) AS viewed,
                       100.0*SUM(has_cart)/NULLIF(SUM(has_view),0)     AS view_to_cart_pct,
                       100.0*SUM(has_purchase)/NULLIF(SUM(has_view),0) AS view_to_purchase_pct
                FROM session_category GROUP BY 1 HAVING SUM(has_view) >= {int(min_n)}
                ORDER BY viewed DESC""")
    st.plotly_chart(px.bar(cat, x="category_l1", y=["view_to_cart_pct", "view_to_purchase_pct"],
                           barmode="group", title="Conversion by category"))

# ---------- Retention ----------
with tab2:
    st.info("Data starts Oct 1, so users first seen in the first week include existing customers. "
            "Do not read the cohort-to-cohort decline as a real trend. The last calendar week is partial "
            "and is blanked out in the heatmap.")
    tri = q("""SELECT f.cohort_week, CAST(date_diff('week', f.cohort_week, a.act_week) AS INTEGER) AS wk,
                      COUNT(DISTINCT a.user_id) AS active
               FROM user_first f
               JOIN (SELECT DISTINCT user_id, DATE_TRUNC('week', event_date) AS act_week FROM events) a USING (user_id)
               GROUP BY 1, 2""")
    sizes = q("SELECT cohort_week, COUNT(*) AS size FROM user_first GROUP BY 1")
    last_week = pd.to_datetime(q("SELECT DATE_TRUNC('week', MAX(event_date)) AS w FROM events").iloc[0, 0])
    tri = tri.merge(sizes, on="cohort_week")
    tri["cohort_week"] = pd.to_datetime(tri["cohort_week"])
    tri["pct"] = 100.0 * tri.active / tri["size"]
    tri.loc[tri.cohort_week + pd.to_timedelta(tri.wk * 7, unit="D") >= last_week, "pct"] = None
    pivot = (tri[tri.wk.between(1, 4)].pivot(index="cohort_week", columns="wk", values="pct")
             .sort_index())
    pivot.index = pivot.index.strftime("%Y-%m-%d")
    pivot.columns = [f"Week +{c}" for c in pivot.columns]
    st.plotly_chart(px.imshow(pivot, text_auto=".1f", color_continuous_scale="Blues", aspect="auto",
                              title="% of cohort active N calendar weeks later"))

    o = q("""SELECT first_session_outcome, COUNT(*) AS users,
                    100.0*AVG(back_within_7d) AS back_within_7d_pct, 100.0*AVG(d1) AS d1_pct
             FROM user_retention GROUP BY 1 ORDER BY 1""")
    st.plotly_chart(px.bar(o, x="first_session_outcome", y="back_within_7d_pct",
                           text=o.users.map("n={:,}".format),
                           title="Back within 7 days, by what happened in the first session"))

# ---------- Data notes ----------
with tab3:
    unk = q("""SELECT 100.0*SUM(CASE WHEN category_l1='unknown' THEN has_view ELSE 0 END)/SUM(has_view) AS pct
               FROM session_category""").iloc[0, 0]
    st.markdown(f"""
- **Cart events are incomplete:** {100*f.buy_no_cart/f.purchased:.1f}% of purchase sessions have no cart event.
- **Missing category:** {unk:.1f}% of category-level views have no category code.
- **Sampling:** users are sampled by hashed user_id so every kept user has their full month of events.
- **Cohorts:** first seen is not the same as new user, because the data starts on Oct 1.
- **Retention windows:** only users with 7+ days of follow-up are counted in 7-day retention.
""")