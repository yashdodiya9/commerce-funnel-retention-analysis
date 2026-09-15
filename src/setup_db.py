"""
Load an events CSV (real REES46 or synthetic) into DuckDB and build a clean
`events` table.

Why sample BY USER, not by first-N-rows:
  The REES46 file is sorted by time, so the first 2M rows cover ~2 days and
  nobody can "return" - retention would be impossible. Keeping a random % of
  users with ALL their events across the month keeps behaviour intact.

Usage:
  python src/setup_db.py --csv data/2019-Oct.csv --user-pct 5      # real data (~2M events)
  python src/setup_db.py --csv data/events_synthetic.csv --user-pct 100
"""
import argparse, pathlib, duckdb

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--db", default="data/events.duckdb")
    ap.add_argument("--user-pct", type=int, default=5,
                    help="Keep this %% of users (deterministic hash of user_id), all their events.")
    a = ap.parse_args()

    pathlib.Path(a.db).parent.mkdir(exist_ok=True)
    con = duckdb.connect(a.db)

    con.execute("DROP TABLE IF EXISTS events_raw")
    con.execute(f"""
        CREATE TABLE events_raw AS
        SELECT * FROM read_csv_auto('{a.csv}', header=true)
        WHERE hash(user_id) % 100 < {a.user_pct}
    """)

    # Clean table. Decisions (document these in your memo):
    #  - DISTINCT removes exact duplicate rows
    #  - unknown category/brand are KEPT as 'unknown' (dropping would lose ~1/3 of data)
    #  - bad prices are flagged, not dropped (they only matter for revenue metrics)
    con.execute("DROP TABLE IF EXISTS events")
    con.execute("""
        CREATE TABLE events AS
        SELECT DISTINCT
            CAST(replace(CAST(event_time AS VARCHAR), ' UTC', '') AS TIMESTAMP) AS event_ts,
            CAST(CAST(replace(CAST(event_time AS VARCHAR), ' UTC', '') AS TIMESTAMP) AS DATE) AS event_date,
            event_type,
            product_id,
            category_id,
            COALESCE(category_code, 'unknown')                       AS category_code,
            split_part(COALESCE(category_code, 'unknown'), '.', 1)   AS category_l1,
            COALESCE(brand, 'unknown')                               AS brand,
            price,
            (price IS NULL OR price <= 0)                            AS bad_price,
            user_id,
            user_session
        FROM events_raw
        WHERE event_type IN ('view', 'cart', 'purchase')
          AND user_id IS NOT NULL
          AND user_session IS NOT NULL
    """)
    n, d, u = con.execute("SELECT COUNT(*), COUNT(DISTINCT event_date), COUNT(DISTINCT user_id) FROM events").fetchone()
    print(f"Loaded {n:,} events | {u:,} users | {d} distinct days -> {a.db}")
    con.close()

if __name__ == "__main__":
    main()