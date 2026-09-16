"""
PART 2 -- POST-HOC ANALYSIS. Developed AFTER seeing the Part 1 pre-registered
results (equal-weight anomaly_score missed Rittenhouse at p=0.052 because
z_edits_count's scale dominated the average). This script is exploratory,
not confirmatory -- label it as such wherever it's reported.

Fix: instead of averaging raw z-scores (whose scale differs hugely between
an unbounded count like edits_count and a bounded ratio like revert_rate),
convert each metric to its PERCENTILE RANK within that article's own
baseline distribution. A percentile is bounded in [0, 1] no matter what the
underlying metric's scale is, so averaging three percentiles gives each
signal genuinely comparable influence -- unlike averaging three z-scores.

anomaly_score_v2 = mean(pct_edits_count, pct_revert_rate, pct_editor_churn)

where pct_X for a given row = fraction of BASELINE rows with value <= X's
value (empirical CDF, evaluated only against non-event days, same
baseline-exclusion logic as Part 1's z-scores).

Usage:
    python rescale_percentile.py \\
        --input data/rittenhouse_scored.csv --out data/rittenhouse_v2.csv \\
        --input data/depp_heard_scored.csv --out data/depp_heard_v2.csv \\
        --input data/dobbs_scored.csv --out data/dobbs_v2.csv
"""

import argparse
import pandas as pd

RAW_METRICS = ["edits_count", "revert_rate", "editor_churn"]


def percentile_rank(value: float, baseline_values: pd.Series) -> float:
    if pd.isna(value):
        return float("nan")
    return (baseline_values <= value).mean()


def add_percentile_scores(df: pd.DataFrame) -> pd.DataFrame:
    baseline = df.loc[df["is_baseline"]]
    for metric in RAW_METRICS:
        baseline_vals = baseline[metric]
        df[f"pct_{metric}"] = df[metric].apply(lambda v: percentile_rank(v, baseline_vals))
    df["anomaly_score_v2"] = df[[f"pct_{m}" for m in RAW_METRICS]].mean(axis=1)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", action="append", required=True, help="Path to a _scored.csv (repeatable)")
    parser.add_argument("--out", action="append", required=True, help="Output path for the matching --input (repeatable)")
    args = parser.parse_args()

    if len(args.input) != len(args.out):
        raise ValueError("--input and --out must be given the same number of times, in matching order")

    for input_path, out_path in zip(args.input, args.out):
        df = pd.read_csv(input_path, parse_dates=["timestamp"])
        df = add_percentile_scores(df)
        top5 = df.nlargest(5, "anomaly_score_v2")[
            ["timestamp", "anomaly_score_v2", "pct_edits_count", "pct_revert_rate", "pct_editor_churn"]
        ]
        print(f"\n{input_path}")
        print("  top 5 anomaly_score_v2 days:")
        print(top5.to_string(index=False))
        df.to_csv(out_path, index=False)
        print(f"  saved -> {out_path}")


if __name__ == "__main__":
    main()