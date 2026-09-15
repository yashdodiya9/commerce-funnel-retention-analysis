# Where do users drop off, and what should we fix first?
**Funnel, cohort and retention analysis of an e-commerce store (REES46, Oct 2019)**

## Summary
Conversion is about 6.8% of sessions, and roughly half of carts are abandoned. Three things stand out, in the order I would act on them:
1. **Cart tracking is unreliable**, so fix it before anyone runs cart-based experiments.
2. **Conversion falls from ~8.3% to ~5.4% in the afternoon peak**, when ~30% of sessions arrive.
3. **Most abandoned carts are never recovered, and first-session commitment predicts coming back.** A reminder or second-purchase nudge is the clearest test to run.

## Data and method
- Source: REES46 multi-category store events, October 2019 (public on Kaggle).
- Sample: 5% of users chosen by hashed user_id, with all of their events. That gives 2,100,840 events, 150,547 users and 461,087 sessions across all 31 days. (Taking the first N rows would have covered only 2 days and made retention impossible.)
- Tools: DuckDB SQL (CTEs, window functions, conditional aggregation), Python, Streamlit/Plotly.
- Cleaning: exact duplicates removed, missing category and brand kept as `unknown`, non-positive prices flagged and not dropped.
- Definitions: a session converts if it contains a purchase event. Funnel rates use view→purchase as the primary metric. Hours are UTC. Retention counts only users with 7+ days of follow-up.

## Findings

### 1. The cart event is incomplete (data quality, fix first)
- 54.2% of purchase sessions (16,920 of 31,245) have no cart event, so raw cart→purchase reads 111%.
- Apparel shows 0.00% view→cart but 1.84% view→purchase, so the cart event likely never fires there (or there is a buy-now path).
- **Recommendation:** use view→purchase as the north-star conversion metric. Audit cart instrumentation before running experiments on add-to-cart rate.

### 2. Conversion drops when traffic peaks
| Window (UTC) | Sessions | View→purchase |
|---|---|---|
| 04:00-11:59 | 207,896 | 8.3% |
| 13:00-17:59 | 140,737 (30.5% of sessions) | 5.4% |

- Sizing (hypothetical): lifting the 13:00-17:59 window by 1 percentage point adds ~1,400 purchase sessions in this sample, about +4.5%.
- **Caveat:** this is a correlation. The peak may bring different traffic (new vs returning users, regions, browsing intent). **Next step:** split these hours by new vs returning users and by category mix before proposing a fix. Day of week is flat (6.5-7.0%) and not actionable.

### 3. Abandoned carts and repeat purchase
- Cart abandonment is 48.9% (13,709 of 28,034 cart sessions). 26.8% of abandoning sessions are followed by a purchase from the same user within 7 days, so about 10,000 are not recovered. (Recovery counts any purchase, not necessarily the same item.)
- Users who purchase in their first session return within 7 days at **41.1%**, vs **31.6%** for view-only users (D1: 16.8% vs 10.5%). Carted-but-not-purchased users return at 39.2%. Only 4.9% of users purchase in their first session, so 92.7% of users are view-only. This is an association, not proof that buying causes return.
- 26.4% of purchasers (4,581 of 17,328) buy on two or more days. Among them the median gap to the second purchase is 4 days (mean 6.1), so any nudge should land in the first week. The median is biased low because late-October first purchases have less time to repeat.
- Sizing (hypothetical): a cart reminder that recovers 5% of the ~10,000 unrecovered carts adds ~500 purchase sessions (+1.6%). A second-purchase nudge that lifts repeat purchasers by 2 points adds ~350 repeat purchasers (+7.6% of repeat purchasers).

## Retention overview
- Of users with 7+ days of follow-up (127,658): D1 10.9%, D7 6.4%, back at least once within 7 days 32.2%.
- Later weekly cohorts show lower retention (back within 7 days: 31.5% → 27.4% → 23.2% for the Oct 7, 14 and 21 cohorts). I do **not** treat this as a real decline: the data starts Oct 1, so early "first seen" users include existing customers, and that contamination fades over the month. A cleaner read needs prior-month data to separate new from existing users.

## How I would test this
**Experiment:** send a cart-reminder message to users who abandon a cart.
- **Unit and split:** randomise by user, 50/50 control vs reminder.
- **Primary metric:** purchase within 7 days of the abandoned session. Baseline 26.8%.
- **Guardrails:** opt-out or unsubscribe rate, 14-day purchases per user (to catch pulled-forward demand), and cost per incremental order if an incentive is used.
- **Sample size** (two-sided, alpha 0.05, power 0.8, baseline 26.8%):

| Minimum detectable lift | Users per arm |
|---|---|
| +1 pp | 31,153 |
| **+2 pp (target)** | **7,875** |
| +3 pp | 3,537 |

- **Duration:** enrol for at least 1-2 full weeks to cover weekday patterns, then follow for 7 days. Check sample-ratio mismatch before reading results, and do not stop early on a good-looking interim result.
- **Limitation:** only users with a tracked cart event can be enrolled, and finding 1 says that is under half of purchasers.

## Limitations
- One month from one store, 5% user sample, hours in UTC with unknown store time zone.
- No device, geography or traffic source in the data, so segment explanations are hypotheses.
- Opportunity sizes are rough and hypothetical, not forecasts.