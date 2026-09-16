"""
Combine z_edits_count, z_revert_rate, and z_editor_churn into a single
equal-weighted anomaly_score per row. The individual z-scores are kept
in the output alongside the combined score -- the combined score is a
summary, not a replacement for looking at the components.

anomaly_score_t = mean(z_edits_count_t, z_revert_rate_t, z_editor_churn_t)

Equal weights: no component is assumed more important than another without
justification. This means a pure attention spike (edits_count) and a pure
disagreement spike (revert_rate) contribute equally to the score even
though they mean different things -- worth stating plainly in the writeup
rather than treating the single number as if it means one clean thing.

Usage:
    python compute_anomaly_score.py \\
        --input data/rittenhouse_features.csv --out data/rittenhouse_scored.csv \\
        --input data/depp_heard_features.csv --out data/depp_heard_scored.csv \\
        --input data/dobbs_features.csv --out data/dobbs_scored.csv
"""

import argparse
import pandas as pd

COMPONENTS = ["z_edits_count", "z_revert_rate", "z_editor_churn"]


def add_anomaly_score(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in COMPONENTS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}. Run feature_engineering.py first.")
    df["anomaly_score"] = df[COMPONENTS].mean(axis=1)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", action="append", required=True, help="Path to a _features.csv (repeatable)")
    parser.add_argument("--out", action="append", required=True, help="Output path for the matching --input (repeatable)")
    args = parser.parse_args()

    if len(args.input) != len(args.out):
        raise ValueError("--input and --out must be given the same number of times, in matching order")

    for input_path, out_path in zip(args.input, args.out):
        df = pd.read_csv(input_path, parse_dates=["timestamp"])
        df = add_anomaly_score(df)
        top5 = df.nlargest(5, "anomaly_score")[["timestamp", "anomaly_score"] + COMPONENTS]
        print(f"\n{input_path}")
        print(f"  top 5 anomaly_score days:")
        print(top5.to_string(index=False))
        df.to_csv(out_path, index=False)
        print(f"  saved -> {out_path}")


if __name__ == "__main__":
    main()