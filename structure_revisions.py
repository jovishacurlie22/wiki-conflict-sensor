"""
Turn raw revision JSON (from fetch_revisions.py) into an hourly time series
of edit activity metrics: edits_per_hour, unique_editors, new_editors,
editor_churn, mean_edit_size, revert_rate.

Usage:
    python structure_revisions.py data/rittenhouse_revisions.json \\
        --bots data/bot_usernames.json \\
        --out data/rittenhouse_timeseries.csv
"""

import argparse
import json
import re
import pandas as pd

# Comment-pattern fallback for reverts not caught by tags.
# Tags (mw-rollback, mw-undo, mw-manual-revert) are the primary signal;
# this catches manual reverts where an editor retypes an old version
# and describes it in the edit summary without using a revert tool.
REVERT_COMMENT_PATTERN = re.compile(
    r"\brv\b|\brvv\b|revert(ed|ing)?|undid revision|undo", re.IGNORECASE
)

REVERT_TAGS = {"mw-rollback", "mw-undo", "mw-manual-revert"}


def load_revisions(path: str) -> pd.DataFrame:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def classify_editors(df: pd.DataFrame, bot_usernames: set[str]) -> pd.DataFrame:
    df["is_bot"] = df["user"].isin(bot_usernames)
    # userid == 0 means the edit was made by an IP / logged-out editor
    df["is_anonymous"] = df["userid"] == 0
    return df


def detect_reverts(df: pd.DataFrame) -> pd.DataFrame:
    tag_revert = df["tags"].apply(
        lambda tags: bool(REVERT_TAGS.intersection(tags)) if isinstance(tags, list) else False
    )
    comment_revert = df["comment"].fillna("").str.contains(REVERT_COMMENT_PATTERN)
    df["is_revert"] = tag_revert | comment_revert
    df["revert_method"] = "none"
    df.loc[comment_revert & ~tag_revert, "revert_method"] = "comment_heuristic"
    df.loc[tag_revert, "revert_method"] = "tag"
    return df


def compute_size_change(df: pd.DataFrame) -> pd.DataFrame:
    # 'size' is the article size in bytes AFTER this revision.
    # size_change is this edit's contribution: current size minus previous.
    df["size_change"] = df["size"].diff().fillna(df["size"])
    return df


def build_hourly_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    df = df.set_index("timestamp")

    # First-ever-appearance timestamp per editor, used to flag "new" editors
    # within a given hour (their very first edit to this article).
    first_seen = df.groupby("user").apply(lambda g: g.index.min())

    def hourly_group(g: pd.DataFrame) -> pd.Series:
        editors_this_hour = set(g["user"])
        new_editors = sum(
            1 for u in editors_this_hour if first_seen[u] >= g.index.min()
            and first_seen[u] <= g.index.max()
        )
        human_edits = g[~g["is_bot"]]
        return pd.Series({
            "edits_per_hour": len(g),
            "unique_editors": g["user"].nunique(),
            "new_editors": new_editors,
            "mean_edit_size": human_edits["size_change"].abs().mean() if len(human_edits) else 0.0,
            "revert_rate": g["is_revert"].mean() if len(g) else 0.0,
            "bot_edit_share": g["is_bot"].mean() if len(g) else 0.0,
        })

    hourly = df.resample("1h").apply(lambda g: hourly_group(g) if len(g) else pd.Series({
        "edits_per_hour": 0, "unique_editors": 0, "new_editors": 0,
        "mean_edit_size": 0.0, "revert_rate": 0.0, "bot_edit_share": 0.0,
    }))

    # editor_churn: fraction of this hour's editors who are new to the article
    hourly["editor_churn"] = (hourly["new_editors"] / hourly["unique_editors"]).fillna(0.0)

    return hourly.reset_index()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revisions_json", help="Path to raw revisions JSON")
    parser.add_argument("--bots", required=True, help="Path to bot usernames JSON")
    parser.add_argument("--out", required=True, help="Output CSV path")
    args = parser.parse_args()

    with open(args.bots, encoding="utf-8") as f:
        bot_usernames = set(json.load(f))

    df = load_revisions(args.revisions_json)
    print(f"Loaded {len(df)} revisions.")

    df = classify_editors(df, bot_usernames)
    df = detect_reverts(df)
    df = compute_size_change(df)

    print(f"  bot edits: {df['is_bot'].sum()} ({df['is_bot'].mean():.1%})")
    print(f"  anonymous edits: {df['is_anonymous'].sum()} ({df['is_anonymous'].mean():.1%})")
    print(f"  reverts: {df['is_revert'].sum()} ({df['is_revert'].mean():.1%})")

    hourly = build_hourly_timeseries(df)
    hourly.to_csv(args.out, index=False)
    print(f"Saved {len(hourly)} hourly rows to {args.out}")


if __name__ == "__main__":
    main()