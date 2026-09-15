"""Run every statement in a .sql file and print results (statements that return no rows, like CREATE TABLE, are just executed).
Usage: python src/run_sql.py sql/02_funnel.sql"""
import sys, duckdb, pandas as pd
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30); pd.set_option("display.max_rows", 100)
con = duckdb.connect("data/events.duckdb")
for stmt in [s.strip() for s in open(sys.argv[1]).read().split(";") if s.strip()]:
    title = next((l for l in stmt.splitlines() if l.startswith("--")), "")
    con.execute(stmt)
    if con.description is not None:
        print("\n" + title)
        print(con.fetchdf().to_string(index=False))
    else:
        print("\n[ran] " + (title or stmt.splitlines()[0][:60]))