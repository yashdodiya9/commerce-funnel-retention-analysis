# E-commerce Funnel, Cohort & Retention Analysis

**Where do users drop off, which users come back, and what should the product team fix first?**

An end-to-end product analytics project on 2.1M real e-commerce events: SQL funnel and cohort analysis, an interactive dashboard, an insights memo with ranked recommendations, and an A/B test plan.

> Full write-up: [`docs/insights_memo.md`](docs/insights_memo.md)

## Headline findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **Cart tracking is unreliable**, so view→purchase is the trustworthy conversion metric | 54.2% of purchase sessions have no cart event; apparel shows 0.00% view→cart but 1.84% view→purchase |
| 2 | **Conversion drops when traffic peaks** | 13:00-17:59 UTC: 5.4% view→purchase (30.5% of sessions) vs 8.3% for 04:00-11:59 UTC |
| 3 | **Most abandoned carts are not recovered, and early commitment predicts return visits** | 48.9% cart abandonment; 26.8% of abandoned carts followed by a purchase within 7 days; first-session purchasers return within 7 days at 41.1% vs 31.6% for view-only users |

Other numbers: 6.78% overall view→purchase, 10.9% D1 retention, 32.2% back within 7 days, 26.4% repeat-purchase rate with a median of 4 days to the second purchase.

Opportunity sizes in the memo (for example, +1.6% purchases from a cart reminder) are hypothetical estimates, not measured results.

## What this project covers
- **Funnel analysis:** session-level view→cart→purchase, strict vs loose funnel definitions, cart abandonment, and cart recovery
- **Segmentation:** hour of day, day of week, product category
- **Cohort retention:** D1/D7, weekly cohort triangle, retention by first-session outcome
- **Repeat purchase:** share of repeat buyers and days to second purchase
- **Data quality:** duplicates, missing values, tracking gaps, and how each was handled
- **Experimentation:** A/B test design for a cart reminder with sample-size calculation and guardrail metrics
- **Communication:** a dashboard and a memo written for a product manager

## Tech stack
DuckDB (SQL with CTEs, window functions, conditional aggregation) · Python · pandas · Plotly · Streamlit · statsmodels

## Project structure
```
.
├── README.md
├── requirements.txt
├── data/                      # not committed (CSV and DuckDB file)
├── docs/
│   └── insights_memo.md       # findings, recommendations, A/B test plan
├── sql/
│   ├── 01_data_quality.sql    # volume, nulls, duplicates, tracking gaps
│   ├── 02_funnel.sql          # session funnel, segments, cart recovery
│   └── 03_retention.sql       # cohorts, retention, repeat purchase
└── src/
    ├── setup_db.py            # loads CSV into DuckDB (samples by user)
    ├── run_sql.py             # runs a .sql file and prints results
    ├── dashboard.py           # Streamlit dashboard
    └── generate_synthetic.py  # fake data for testing the pipeline only
```

## Dataset
[eCommerce behavior data from multi category store](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store) (REES46) on Kaggle. Only `2019-Oct.csv` is used.

## How to run
```bash
git clone https://github.com/yashdodiya9/commerce-funnel-retention-analysis.git
cd commerce-funnel-retention-analysis
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Download 2019-Oct.csv from Kaggle into data/
mkdir -p data

# 2. Load a 5% user sample into DuckDB (scans the full file, takes a few minutes)
python src/setup_db.py --csv data/2019-Oct.csv --user-pct 5

# 3. Run the analysis in order (02 builds tables that 03 uses)
python src/run_sql.py sql/01_data_quality.sql
python src/run_sql.py sql/02_funnel.sql
python src/run_sql.py sql/03_retention.sql

# 4. Launch the dashboard
streamlit run src/dashboard.py
```

## Method notes
- **Sampling by user, not by row.** The file is sorted by time, so the first N rows cover only about 2 days and retention would be impossible. I keep 5% of users by hashed `user_id` with all their events, which gives 2,100,840 events, 150,547 users and 461,087 sessions across 31 days.
- **Funnel anchored on view→purchase.** Purchases can exceed carts because cart events are incomplete, so raw cart→purchase can exceed 100%. The memo reports strict and loose funnels.
- **Cleaning decisions.** Exact duplicates removed; missing category and brand kept as `unknown` (about 36% of sessions have no category); non-positive prices flagged, not dropped.
- **Retention.** Only users with at least 7 days of follow-up are counted.

## Limitations
- One month from one store, 5% user sample, hours in UTC with unknown store time zone.
- The data has no device, geography or traffic source, so explanations for segment differences are hypotheses to test.
- Data starts on Oct 1, so users "first seen" in the first week include existing customers. Cohort-to-cohort retention decline is therefore not read as a real trend, and the last calendar week is partial and excluded from the cohort heatmap.
- Cart-based experiments can only enrol users with a tracked cart event, which is under half of purchasers.
- `generate_synthetic.py` produces fake data to test the pipeline. None of the results above come from it.

## Author
Yash Dodiya · [GitHub](https://github.com/yashdodiya9) · [LinkedIn](https://linkedin.com/in/yashdodiya)
