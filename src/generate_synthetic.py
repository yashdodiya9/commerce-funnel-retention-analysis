"""
Generate a SYNTHETIC event log with the same schema as the REES46 eCommerce
behaviour dataset, so you can build and test every query before (or without)
downloading the real data.

!! This is simulated data. Never report its numbers as real findings. !!
Swap in the real CSV with `python src/setup_db.py --csv <path>` and re-run.
"""
import argparse
import numpy as np
import pandas as pd

HOUR_W = np.array([1,1,1,1,1,2,3,4,5,6,6,6,6,6,6,6,7,8,9,10,9,7,4,2], dtype=float)
HOUR_P = HOUR_W / HOUR_W.sum()

def generate(n_users=20000, days=30, seed=42):
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2019-10-01")

    categories = {
        "electronics.smartphone": (0.35, 250, 0.030),
        "electronics.audio.headphone": (0.15, 60, 0.050),
        "appliances.kitchen": (0.20, 90, 0.045),
        "apparel.shoes": (0.15, 55, 0.060),
        "computers.notebook": (0.15, 600, 0.020),
    }
    cat_names = list(categories)
    cat_p = [v[0] for v in categories.values()]
    cat_ids = {c: 2_000_000_000_000_000_000 + i * 1111 for i, c in enumerate(cat_names)}
    brands = ["samsung", "apple", "xiaomi", "sony", "lg", "nike", "acer", "huawei"]

    rows = []
    session_counter = 0
    for uid in range(1, n_users + 1):
        user_id = 500_000_000 + uid
        first_day = int(rng.integers(0, days))
        mobile = rng.random() < 0.6   # hidden driver of behaviour (not a column in real data)
        n_visits = 1 + rng.poisson(1.2 if mobile else 1.8)
        day = first_day
        for v in range(n_visits):
            if day >= days:
                break
            session_counter += 1
            sess = f"sess-{session_counter:08d}"
            t = start + pd.Timedelta(days=int(day), hours=int(rng.choice(24, p=HOUR_P)),
                                     minutes=int(rng.integers(0, 60)))
            for _ in range(1 + rng.poisson(4)):
                cat = str(rng.choice(cat_names, p=cat_p))
                _, base_price, base_cart = categories[cat]
                price = round(float(base_price * rng.lognormal(0, 0.4)), 2)
                pid = int(rng.integers(1_000_000, 1_000_400))
                brand = str(rng.choice(brands))
                t = t + pd.Timedelta(seconds=int(rng.integers(5, 240)))
                rows.append((t, "view", pid, cat_ids[cat], cat, brand, price, user_id, sess))
                p_cart = base_cart * (0.7 if mobile else 1.1) * (1.3 if v > 0 else 1.0)
                if rng.random() < p_cart * 4:
                    t = t + pd.Timedelta(seconds=int(rng.integers(10, 120)))
                    rows.append((t, "cart", pid, cat_ids[cat], cat, brand, price, user_id, sess))
                    p_buy = 0.32 * (0.8 if mobile else 1.0) * (1.4 if v > 0 else 1.0)
                    if rng.random() < p_buy:
                        t = t + pd.Timedelta(seconds=int(rng.integers(30, 600)))
                        rows.append((t, "purchase", pid, cat_ids[cat], cat, brand, price, user_id, sess))
            day += int(rng.integers(1, 15))
    df = pd.DataFrame(rows, columns=["event_time", "event_type", "product_id", "category_id",
                                     "category_code", "brand", "price", "user_id", "user_session"])
    df = df.sort_values("event_time").reset_index(drop=True)
    df["event_time"] = df["event_time"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return df

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=20000)
    ap.add_argument("--out", default="data/events_synthetic.csv")
    a = ap.parse_args()
    df = generate(a.users)
    df.to_csv(a.out, index=False)
    print(f"Wrote {len(df):,} synthetic events to {a.out}")
