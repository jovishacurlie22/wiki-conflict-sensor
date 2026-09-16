"""
PRE-REGISTERED CONFIRMATORY TEST (Part 1).

Tests whether the pre-registered event windows score higher than would be
expected by chance, for each signal separately and for the combined
anomaly_score.

Method: permutation test. For each registered event, take the +/-3 day
window and record the maximum score in it. Then draw many random windows of
the same width from that article's non-event days and record their maxima.
The p-value is the fraction of random windows scoring at least as high as
the observed one.

Why a permutation test rather than a t-test: the z-scored count data is
heavily right-skewed (most days near zero, rare enormous spikes), so
normality assumptions don't hold. A permutation test makes no distributional
assumptions -- it only assumes exchangeability of window placement under the
null, which is what we want to test.

Why max-in-window rather than mean-in-window: an event's reaction may land
on any day within the window (we already saw the Rittenhouse edit spike
arrive a day after the verdict). Taking the max asks "did this window
contain an unusual day", which matches the detection question. The mean
would dilute a single sharp spike across six quiet days.

NOTE: this script reports the pre-registered result as-is. Do not tune the
window, the signals, or the score in response to what it prints -- any such
change belongs in the clearly-labelled post-hoc section instead.

Usage:
    python statistical_test.py \\
        --input data/rittenhouse_scored.csv --events 2021-11-19 --label Rittenhouse \\
        --input data/depp_heard_scored.csv --events 2022-06-01 --label "Depp v. Heard" \\
        --input data/dobbs_scored.csv --events 2022-05-02,2022-06-24 --label Dobbs
"""

import argparse
import numpy as np
import pandas as pd

SIGNALS_DEFAULT = ["anomaly_score", "z_edits_count", "z_revert_rate", "z_editor_churn"]
N_PERMUTATIONS = 10_000
RANDOM_SEED = 42  # fixed so the reported p-values are reproducible


def window_max(df: pd.DataFrame, center: pd.Timestamp, window_days: int, signal: str) -> float:
    mask = (df["timestamp"] - center).abs() <= pd.Timedelta(days=window_days)
    vals = df.loc[mask, signal]
    return vals.max() if len(vals) else np.nan


def permutation_test(df: pd.DataFrame, event: pd.Timestamp, signal: str,
                      window_days: int, rng: np.random.Generator) -> dict:
    observed = window_max(df, event, window_days, signal)

    # Null windows are drawn only from days outside ANY event window, so the
    # null distribution isn't contaminated by the very events we're testing.
    eligible = df.loc[df["is_baseline"], "timestamp"]
    if len(eligible) == 0:
        raise ValueError("No baseline rows available to draw null windows from.")

    centers = rng.choice(eligible.values, size=N_PERMUTATIONS, replace=True)
    null_maxima = np.array([
        window_max(df, pd.Timestamp(c, tz="UTC"), window_days, signal) for c in centers
    ])
    null_maxima = null_maxima[~np.isnan(null_maxima)]

    # One-sided: we only care about scoring HIGHER than chance.
    # +1 in numerator and denominator is the standard correction that keeps
    # p from ever being exactly 0 (we can't prove p=0 from finite draws).
    n_at_least = (null_maxima >= observed).sum()
    p_value = (n_at_least + 1) / (len(null_maxima) + 1)

    return {
        "observed_max": observed,
        "null_median": float(np.median(null_maxima)),
        "null_p95": float(np.percentile(null_maxima, 95)),
        "p_value": p_value,
        "n_null": len(null_maxima),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", action="append", required=True, help="Path to a _scored.csv (repeatable)")
    parser.add_argument("--events", action="append", required=True, help="Comma-separated event dates for matching --input")
    parser.add_argument("--label", action="append", required=True, help="Display label for matching --input")
    parser.add_argument("--window-days", type=int, default=3, help="Window half-width in days (default: 3, matches pre-registration)")
    parser.add_argument("--signals", default=",".join(SIGNALS_DEFAULT),
                         help=f"Comma-separated column names to test (default: {','.join(SIGNALS_DEFAULT)})")
    parser.add_argument("--out", default=None, help="Optional CSV path to save the results table")
    args = parser.parse_args()
    signals = [s.strip() for s in args.signals.split(",")]

    if not (len(args.input) == len(args.events) == len(args.label)):
        raise ValueError("--input, --events, and --label must be given the same number of times, in matching order")

    rng = np.random.default_rng(RANDOM_SEED)
    rows = []

    for input_path, events_str, label in zip(args.input, args.events, args.label):
        df = pd.read_csv(input_path, parse_dates=["timestamp"])
        events = [pd.Timestamp(d.strip(), tz="UTC") for d in events_str.split(",")]

        for event in events:
            for signal in signals:
                res = permutation_test(df, event, signal, args.window_days, rng)
                rows.append({
                    "article": label,
                    "event_date": str(event.date()),
                    "signal": signal,
                    **res,
                })

    results = pd.DataFrame(rows)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", None)
    print("\nPRE-REGISTERED PERMUTATION TEST RESULTS")
    print(f"(window = +/-{args.window_days}d, {N_PERMUTATIONS} permutations, seed={RANDOM_SEED})\n")
    for (article, event_date), grp in results.groupby(["article", "event_date"], sort=False):
        print(f"--- {article} | {event_date} ---")
        display = grp[["signal", "observed_max", "null_median", "null_p95", "p_value"]]
        print(display.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
        print()

    if args.out:
        results.to_csv(args.out, index=False)
        print(f"Saved results table -> {args.out}")


if __name__ == "__main__":
    main()