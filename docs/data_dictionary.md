# Data Dictionary

Documents every column produced by the pipeline and the judgment calls
behind them. Anywhere a decision could reasonably have gone another way,
that's noted explicitly rather than presented as the only option.

## Pipeline overview

```
fetch_bots.py           -> data/bot_usernames.json
fetch_revisions.py       -> data/<article>_revisions.json      (raw, per-revision)
structure_revisions.py   -> data/<article>_hourly.csv           (--freq 1h, zoom-in use)
                          -> data/<article>_daily.csv            (--freq 1D, analysis base)
feature_engineering.py   -> data/<article>_features.csv         (adds z-scores + is_baseline)
compute_anomaly_score.py -> data/<article>_scored.csv            (adds anomaly_score)
rescale_percentile.py    -> data/<article>_v2.csv                (post-hoc, percentile rescale)
winsorize_score.py       -> data/<article>_v3.csv                (post-hoc, winsorized rescale)
statistical_test.py      -> data/*_test_results.csv              (permutation test output)
```

## Raw revision fields (from `*_revisions.json`)

| Field | Meaning |
|---|---|
| `revid` / `parentid` | Revision ID and the ID of the revision it replaced |
| `timestamp` | UTC, ISO 8601 |
| `user` | Editor username or IP. **Missing (NaN) for RevisionDeleted/oversighted edits** — see "Hidden users" below |
| `userid` | Wikipedia numeric user ID. `0` = anonymous/IP editor |
| `size` | Article size in **bytes after** this revision |
| `comment` | Edit summary, editor-supplied and free text |
| `tags` | MediaWiki-assigned tags (e.g. `mw-undo`, `mw-rollback`, `visualeditor`) |

## Structured time-series columns (from `*_hourly.csv` / `*_daily.csv`)

| Column | Definition | Notes / limitations |
|---|---|---|
| `edits_count` | Number of revisions in this time bin | Safe to sum across finer bins into coarser ones |
| `unique_editors` | Distinct editors active in this bin | **Not** safe to sum across bins — the same editor active in two hours of one day would be double-counted if hourly counts were summed to get a daily figure. Each grain is computed independently from raw revisions for this reason |
| `new_editors` | Editors in this bin whose first-ever edit **to this article** falls in this bin | Article-scoped, not wiki-scoped — an editor experienced elsewhere counts as "new" here on their first edit to this page |
| `editor_churn` | `new_editors / unique_editors` for the bin | Fraction of that bin's editors who are newcomers to the article, not a turnover rate over time |
| `mean_edit_size` | Mean absolute byte change per human (non-bot) edit in the bin | Bot edits excluded to avoid large automated reformatting edits skewing the average |
| `revert_rate` | Fraction of edits in the bin flagged as reverts | See "Revert detection" below |
| `bot_edit_share` | Fraction of edits by bot-flagged accounts | See "Bot classification" below |
| `hidden_user_share` | Fraction of edits with a RevisionDeleted/suppressed editor identity | See "Hidden users" below |

## Feature columns (from `*_features.csv`)

| Column | Definition |
|---|---|
| `z_<metric>` | `(value - baseline_mean) / baseline_std` for that metric, computed per-article |
| `is_baseline` | `True` if this row was included in computing that article's baseline mean/std, `False` if it fell within ±3 days of a pre-registered event date for that article |

**Baseline exclusion window (±3 days):** chosen after observing, in an early
manual check on Rittenhouse, that its real edit spike landed a day after
the verdict rather than on it — the window needs to be wide enough to
absorb real-world reaction lag. This is a judgment call, not a value
derived from the data, and was **locked before running the pre-registered
test** (Part 1) — it was not adjusted afterward even when a later finding
(Rittenhouse's revert-rate peak landing near the edge of the window) might
have tempted a post-hoc widening.

## Composite score columns

| Column | File | Definition |
|---|---|---|
| `anomaly_score` | `*_scored.csv` | Equal-weighted mean of `z_edits_count`, `z_revert_rate`, `z_editor_churn`. **Pre-registered** — this is the confirmatory score reported in Part 1 |
| `anomaly_score_v2` | `*_v2.csv` | Post-hoc: mean of within-baseline percentile ranks of the three raw metrics. Reported in Part 2 as a **failed** fix — see `docs/part2_posthoc_results.md` |
| `anomaly_score_v3` | `*_v3.csv` | Post-hoc: mean of z-scores winsorized (capped) at ±5. Also reported in Part 2 as a **failed** fix |

**Final recommendation (Part 2 conclusion):** none of the three composite
scores serves all four registered events well. `z_edits_count` and
`z_revert_rate` are reported as separate signals rather than combined,
since they detect qualitatively different phenomena (attention vs. genuine
content dispute).

## Bot classification

`is_bot` = editor username appears in the current Wikipedia bot-user-group
list (`fetch_bots.py`, via `action=query&list=allusers&augroup=bot`).

**Limitation:** this is the *current* bot-flagged account list, not a
historical snapshot. An account that lost its bot flag after editing an
article years ago will now be misclassified as human. Not corrected for —
disclosed here instead.

## Revert detection

`is_revert` = `True` if either:
1. The revision's `tags` include `mw-rollback`, `mw-undo`, or
   `mw-manual-revert` (primary signal — tool-assigned, reliable), **or**
2. The edit `comment` matches a regex for common revert language (`rv`,
   `rvv`, `revert(ed/ing)`, `undid revision`, `undo`) — fallback for manual
   reverts that don't trigger a MediaWiki revert tool

**Limitation:** the comment-pattern fallback will miss a manual revert
whose comment doesn't use these words, and could in principle
false-positive on an edit that merely mentions "revert" in an unrelated
context. Not manually audited at scale — a documented approximation, not a
guarantee.

## Hidden users (RevisionDeleted / oversighted edits)

Some revisions — observed concretely on Depp v. Heard, plausibly because
of its legally sensitive subject matter — have no `user` field at all;
Wikipedia suppressed the editor's identity. These are:
- Flagged via `is_hidden_user = True`
- Given the sentinel username `"[hidden]"` so they don't crash
  editor-uniqueness logic, but this means **all hidden-user edits on an
  article are treated as one "editor"** for `unique_editors` /
  `editor_churn` purposes, which likely undercounts the true number of
  distinct (unknowable) editors behind those edits
- Tracked separately via `hidden_user_share` so their prevalence is visible
  rather than silently folded into another category

