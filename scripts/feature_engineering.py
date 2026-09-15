"""
Normalize each article's daily metrics into z-scores relative to that
article's OWN baseline (mean/std), so activity levels become comparable
across articles with very different normal traffic.

Baseline is computed EXCLUDING a window around each pre-registered event
date, so the event itself doesn't inflate what counts as "normal" and mute
its own signal. This makes the later anomaly-detection test more sensitive,
at the cost of needing to disclose the choice plainly in the writeup --
which this script does by printing exactly what was excluded.

Event dates are pre-registered here, once, before any anomaly detection is
run. Do not edit this list after looking at detection results.

Usage:
    python feature_engineering.py \\
        --input data/rittenhouse_daily.csv --events 2021-11-19 --window-days 3 --out data/rittenhouse_features.csv \\
        --input data/depp_heard_daily.csv --events 2022-06-01 --window-days 3 --out data/depp_heard_features.csv \\
        --input data/dobbs_daily.csv --events 2022-05-02,2022-06-24 --window-days 3 --out data/dobbs_features.csv
"""

import argparse
import pandas as pd

# Metrics to z-score. mean_edit_size is left out of the default composite
# later, but normalizing it here too costs nothing and may be useful in
# exploratory analysis.
METRICS = [
    "edits_count", "unique_editors", "new_editors",
    "mean_edit_size", "revert_rate", "editor_churn",
]


def parse_events(events_str: str) -> list[pd.Timestamp]:
    # Daily CSVs carry UTC-aware timestamps (from the original API's
    # Z-suffixed timestamps). Localize event dates to UTC too, or the
    # subtraction in exclude_event_windows() fails on naive-vs-aware.
    return [pd.Timestamp(d.strip(), tz="UTC") for d in events_str.split(",")]


def exclude_event_windows(df: pd.DataFrame, events: list[pd.Timestamp], window_days: int) -> pd.Series:
    """Boolean mask: True for rows to KEEP in the baseline (i.e. NOT near an event)."""
    keep = pd.Series(True, index=df.index)
    for event in events:
        near_event = (df["timestamp"] - event).abs() <= pd.Timedelta(days=window_days)
        keep &= ~near_event
    return keep


def add_zscores(df: pd.DataFrame, events: list[pd.Timestamp], window_days: int) -> pd.DataFrame:
    baseline_mask = exclude_event_windows(df, events, window_days)
    n_excluded = (~baseline_mask).sum()
    print(f"  baseline: {baseline_mask.sum()} rows, excluded {n_excluded} rows "
          f"within {window_days}d of {[str(e.date()) for e in events]}")

    for metric in METRICS:
        baseline_mean = df.loc[baseline_mask, metric].mean()
        baseline_std = df.loc[baseline_mask, metric].std()
        z_col = f"z_{metric}"
        if baseline_std == 0 or pd.isna(baseline_std):
            # Degenerate case: a metric that's constant (often 0) across the
            # whole baseline. Undefined z-score -> leave as 0 rather than
            # dividing by zero, and flag it so it's not silently misread.
            print(f"    WARNING: baseline std for {metric} is 0 or NaN -- z_{metric} set to 0 throughout")
            df[z_col] = 0.0
        else:
            df[z_col] = (df[metric] - baseline_mean) / baseline_std

    df["is_baseline"] = baseline_mask
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", action="append", required=True, help="Path to a daily CSV (repeatable)")
    parser.add_argument("--events", action="append", required=True,
                         help="Comma-separated pre-registered event dates (YYYY-MM-DD) for the matching --input (repeatable)")
    parser.add_argument("--out", action="append", required=True, help="Output path for the matching --input (repeatable)")
    parser.add_argument("--window-days", type=int, default=3, help="Days around each event date to exclude from baseline (default: 3)")
    args = parser.parse_args()

    if not (len(args.input) == len(args.events) == len(args.out)):
        raise ValueError("--input, --events, and --out must be given the same number of times, in matching order")

    for input_path, events_str, out_path in zip(args.input, args.events, args.out):
        print(f"\n{input_path}")
        df = pd.read_csv(input_path, parse_dates=["timestamp"])
        events = parse_events(events_str)
        df = add_zscores(df, events, args.window_days)
        df.to_csv(out_path, index=False)
        print(f"  saved -> {out_path}")


if __name__ == "__main__":
    main()