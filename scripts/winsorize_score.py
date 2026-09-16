"""
PART 2b -- POST-HOC ANALYSIS (second attempt). Developed after seeing that
the percentile-rescaled score (Part 2a) performed WORSE than the original
equal-weight z-score average, because percentile's hard ceiling at 1.0
destroyed the tail-magnitude information that made z_edits_count powerful,
and interacted badly with the max-in-window test statistic.

This attempt keeps z-scores (preserving magnitude information, unlike
percentiles) but WINSORIZES them: caps each z-score at CAP before
averaging. This tames edits_count's scale dominance without discarding how
extreme a value is beyond the cap -- a capped 8 and a capped 50 both read
as CAP, but anything below CAP keeps its original, uncompressed value,
unlike percentile rank which compresses the entire upper tail into a
single bounded range everywhere.

anomaly_score_v3 = mean(clip(z_edits_count, -CAP, CAP),
                         clip(z_revert_rate, -CAP, CAP),
                         clip(z_editor_churn, -CAP, CAP))

Usage:
    python winsorize_score.py \\
        --input data/rittenhouse_scored.csv --out data/rittenhouse_v3.csv \\
        --input data/depp_heard_scored.csv --out data/depp_heard_v3.csv \\
        --input data/dobbs_scored.csv --out data/dobbs_v3.csv \\
        --cap 5
"""

import argparse
import pandas as pd

Z_COMPONENTS = ["z_edits_count", "z_revert_rate", "z_editor_churn"]


def add_winsorized_score(df: pd.DataFrame, cap: float) -> pd.DataFrame:
    for col in Z_COMPONENTS:
        df[f"{col}_clip"] = df[col].clip(lower=-cap, upper=cap)
    df["anomaly_score_v3"] = df[[f"{c}_clip" for c in Z_COMPONENTS]].mean(axis=1)
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", action="append", required=True, help="Path to a _scored.csv (repeatable)")
    parser.add_argument("--out", action="append", required=True, help="Output path for the matching --input (repeatable)")
    parser.add_argument("--cap", type=float, default=5.0, help="Winsorization cap (default: 5.0)")
    args = parser.parse_args()

    if len(args.input) != len(args.out):
        raise ValueError("--input and --out must be given the same number of times, in matching order")

    for input_path, out_path in zip(args.input, args.out):
        df = pd.read_csv(input_path, parse_dates=["timestamp"])
        df = add_winsorized_score(df, args.cap)
        top5 = df.nlargest(5, "anomaly_score_v3")[
            ["timestamp", "anomaly_score_v3"] + [f"{c}_clip" for c in Z_COMPONENTS]
        ]
        print(f"\n{input_path}")
        print(f"  top 5 anomaly_score_v3 days (cap={args.cap}):")
        print(top5.to_string(index=False))
        df.to_csv(out_path, index=False)
        print(f"  saved -> {out_path}")


if __name__ == "__main__":
    main()