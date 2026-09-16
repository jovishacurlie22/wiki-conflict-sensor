# Wikipedia as a Sensor: Detecting Real-World Events from Edit Anomalies

Does unusual Wikipedia editing behavior — edit volume, revert rate, editor
churn — correspond to real-world events and controversy? This project tests
that hypothesis with a pre-registered validation, rather than just plotting
some spikes and calling it a day.

## Headline result

Edit volume is a strong, statistically significant detector of real-world
attention (3 of 4 pre-registered events, surviving conservative
multiple-comparisons correction for 3 of them). But it isn't the whole
story: **revert rate — not edit volume — was the only signal that detected
a genuine content dispute** (the Kyle Rittenhouse verdict), where reaction
was smaller in scale but more contested. Two separate post-hoc attempts to
fix a combined "one number" score into catching both kinds of events made
things *worse*, not better — a real, demonstrated finding, not a
shortcoming glossed over. Full reasoning in [`docs/part1_prereg_results.md`](docs/part1_prereg_results.md)
and [`docs/part2_posthoc_results.md`](docs/part2_posthoc_results.md).

## Method, in brief

1. Pre-registered three articles and four event dates **before** running
   any anomaly detection: Kyle Rittenhouse (verdict, 2021-11-19), Depp v.
   Heard (verdict, 2022-06-01), Dobbs v. Jackson (leak 2022-05-02, decision
   2022-06-24).
2. Pulled full revision history for each via the Wikipedia API.
3. Cleaned and classified every edit (bot / human / anonymous / identity
   -suppressed), detected reverts, and structured into daily time series.
4. Z-scored each signal against that article's own baseline — excluding a
   locked ±3 day window around each registered date, so an event couldn't
   inflate its own "normal."
5. Combined signals into an equal-weighted `anomaly_score` and tested it
   (and each component separately) with a 10,000-draw permutation test
   against the registered dates. This is the confirmatory result.
6. Two post-hoc rescaling attempts (percentile rank, winsorized z-scores)
   were tried afterward to address a scale-dominance issue found in step
   5, and reported honestly even though neither improved on it.

Every judgment call behind steps 3–5 (bot list limitations, revert
detection heuristics, hidden-editor handling, the ±3 day window, why
equal weights) is documented in [`docs/data_dictionary.md`](docs/data_dictionary.md).

## Repo structure

```
wiki-conflict-sensor/
├── scripts/
│   ├── fetch_bots.py              # pull current Wikipedia bot-flagged accounts
│   ├── fetch_revisions.py         # pull full revision history for one article
│   ├── structure_revisions.py     # raw revisions -> cleaned daily/hourly time series
│   ├── feature_engineering.py     # time series -> z-scored features (baseline-excluded)
│   ├── compute_anomaly_score.py   # z-scores -> equal-weighted anomaly_score (Part 1)
│   ├── rescale_percentile.py      # post-hoc attempt: percentile-rank composite (Part 2a)
│   ├── winsorize_score.py         # post-hoc attempt: winsorized composite (Part 2b)
│   └── statistical_test.py        # permutation test against registered event dates
├── data/                          # generated CSV/JSON outputs (see below to reproduce)
├── docs/
│   ├── data_dictionary.md         # every column + every judgment call, documented
│   ├── part1_prereg_results.md    # confirmatory result and conclusion
│   └── part2_posthoc_results.md   # exploratory rescaling attempts and why they failed
├── analysis.ipynb                 # visual companion notebook, pre-executed
├── requirements.txt
└── README.md
```

## Reproducing this

```bash
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
mkdir data

# One-time: bot list
python scripts/fetch_bots.py --out data/bot_usernames.json

# Per article: raw revision history
python scripts/fetch_revisions.py "Kyle Rittenhouse" --out data/rittenhouse_revisions.json
python scripts/fetch_revisions.py "Depp v. Heard" --out data/depp_heard_revisions.json
python scripts/fetch_revisions.py "Dobbs v. Jackson Women's Health Organization" --out data/dobbs_revisions.json

# Per article: structure into daily (and optionally hourly) time series
python scripts/structure_revisions.py data/rittenhouse_revisions.json --bots data/bot_usernames.json --out data/rittenhouse_daily.csv --freq 1D
python scripts/structure_revisions.py data/depp_heard_revisions.json --bots data/bot_usernames.json --out data/depp_heard_daily.csv --freq 1D
python scripts/structure_revisions.py data/dobbs_revisions.json --bots data/bot_usernames.json --out data/dobbs_daily.csv --freq 1D

# Feature engineering: z-score against baseline, excluding ±3d around each event
python scripts/feature_engineering.py \
  --input data/rittenhouse_daily.csv --events 2021-11-19 --out data/rittenhouse_features.csv \
  --input data/depp_heard_daily.csv --events 2022-06-01 --out data/depp_heard_features.csv \
  --input data/dobbs_daily.csv --events 2022-05-02,2022-06-24 --out data/dobbs_features.csv

# Composite score (Part 1, pre-registered)
python scripts/compute_anomaly_score.py \
  --input data/rittenhouse_features.csv --out data/rittenhouse_scored.csv \
  --input data/depp_heard_features.csv --out data/depp_heard_scored.csv \
  --input data/dobbs_features.csv --out data/dobbs_scored.csv

# Pre-registered statistical test (Part 1)
python scripts/statistical_test.py \
  --input data/rittenhouse_scored.csv --events 2021-11-19 --label Rittenhouse \
  --input data/depp_heard_scored.csv --events 2022-06-01 --label "Depp v. Heard" \
  --input data/dobbs_scored.csv --events 2022-05-02,2022-06-24 --label Dobbs \
  --out data/prereg_test_results.csv

# Post-hoc rescaling attempts (Part 2) + their tests
python scripts/rescale_percentile.py \
  --input data/rittenhouse_scored.csv --out data/rittenhouse_v2.csv \
  --input data/depp_heard_scored.csv --out data/depp_heard_v2.csv \
  --input data/dobbs_scored.csv --out data/dobbs_v2.csv

python scripts/winsorize_score.py \
  --input data/rittenhouse_scored.csv --out data/rittenhouse_v3.csv \
  --input data/depp_heard_scored.csv --out data/depp_heard_v3.csv \
  --input data/dobbs_scored.csv --out data/dobbs_v3.csv \
  --cap 5

python scripts/statistical_test.py \
  --input data/rittenhouse_v2.csv --events 2021-11-19 --label Rittenhouse \
  --input data/depp_heard_v2.csv --events 2022-06-01 --label "Depp v. Heard" \
  --input data/dobbs_v2.csv --events 2022-05-02,2022-06-24 --label Dobbs \
  --signals anomaly_score_v2,pct_edits_count,pct_revert_rate,pct_editor_churn \
  --out data/posthoc_test_results.csv

python scripts/statistical_test.py \
  --input data/rittenhouse_v3.csv --events 2021-11-19 --label Rittenhouse \
  --input data/depp_heard_v3.csv --events 2022-06-01 --label "Depp v. Heard" \
  --input data/dobbs_v3.csv --events 2022-05-02,2022-06-24 --label Dobbs \
  --signals anomaly_score_v3,z_edits_count_clip,z_revert_rate_clip,z_editor_churn_clip \
  --out data/posthoc_v3_test_results.csv
```

Then open `analysis.ipynb` to reproduce the plots.

## Known limitations

See [`docs/data_dictionary.md`](docs/data_dictionary.md) for the full list.
Briefly: the bot-account list reflects *current* bot-flagged status, not a
historical snapshot; revert detection combines a reliable tag-based signal
with a comment-pattern fallback that hasn't been manually audited at scale;
and edits with suppressed editor identity (RevisionDeleted) are collapsed
into a single sentinel "editor," likely undercounting true unique-editor
and churn figures on articles where this occurs.

## What this project is not claiming

This is not a general-purpose "controversy detector." It was validated
against three articles and four dates, chosen for their well-documented
event timing — not a random or representative sample. The result that
edit volume and revert rate detect different things is itself the main
finding; treat it as a hypothesis worth testing further, not a proven
production signal.