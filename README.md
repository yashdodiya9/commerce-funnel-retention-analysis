# Quick-Commerce Funnel, Cohort & Retention Analysis

**Business question:** Where do users drop off between view → cart → purchase, which cohorts keep coming back, and what should the product team change first?

**Stack:** DuckDB (SQL) · Python · Plotly/Streamlit · statsmodels (for the A/B test plan)

## Status
- [x] Step 1: Setup and data-quality checks
- [ ] Step 2: Funnel analysis (SQL)
- [ ] Step 3: Cohort retention (SQL)
- [ ] Step 4: Dashboard
- [ ] Step 5: Insights memo + "how I'd test this"

## Setup
```bash
pip install -r requirements.txt

# Real data (recommended for the final submission)
# 1. Download "eCommerce behavior data from multi category store" from Kaggle (REES46)
# 2. Put 2019-Oct.csv in data/
python src/setup_db.py --csv data/2019-Oct.csv --sample 2000000

# OR synthetic data (for building/testing only, NEVER report its numbers as findings)
python src/generate_synthetic.py --users 20000
python src/setup_db.py --csv data/events_synthetic.csv

# Run any SQL file
python src/run_sql.py sql/01_data_quality.sql
```

## Data note
Final results in this repo must come from the real REES46 data. Synthetic data is used only to develop and test the pipeline.
