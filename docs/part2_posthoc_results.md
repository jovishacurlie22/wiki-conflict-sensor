# Part 2: Post-Hoc Analysis — Attempting to Fix the Composite Score

**Everything in this section was developed AFTER seeing the Part 1
pre-registered results. It is exploratory, not confirmatory, and is
reported as such.**

## Motivation

Part 1 found that the equal-weighted `anomaly_score` narrowly missed
significance for the Rittenhouse verdict (p=0.052) even though
`z_revert_rate` alone detected it clearly (p=0.031). The suspected cause:
`z_edits_count` runs an order of magnitude larger than the other two
signals for high-volume events, so it dominates an equal-weight average in
practice despite nominally equal weights.

Two post-hoc rescaling attempts were made to test this.

## Attempt 1: Percentile rank

Each raw metric was converted to its percentile rank within that article's
own baseline distribution (bounded to [0, 1]) before averaging. Result:
**worse across the board**, not better.

| Event | Part 1 (raw z) | Attempt 1 (percentile) |
|---|---|---|
| Depp v. Heard | 0.0001 | 0.1316 |
| Dobbs (leak) | 0.0012 | 0.0559 |
| Dobbs (decision) | 0.0001 | 0.0553 |
| Rittenhouse | 0.052 | 0.0838 |

Cause: percentile rank saturates at 1.0. A value that is merely the new
maximum in the baseline and a value that is 50 standard deviations above
normal both read as 1.0, destroying the magnitude information that made
`z_edits_count` powerful for Depp and Dobbs. This interacts badly with the
max-in-window test statistic specifically: the max of any 7-day window
tends to land near the top of the distribution just from having 7 chances
to do so, so random windows' maxima cluster near 1.0 too, shrinking the gap
the significance test relies on.

## Attempt 2: Winsorization (capped z-scores)

Each z-score was capped at ±5 before averaging, preserving magnitude below
the cap instead of collapsing the whole upper tail to a fixed value.

| Event | Part 1 (raw z) | Attempt 2 (winsorized, cap=5) |
|---|---|---|
| Depp v. Heard | 0.0001 | 0.0323 |
| Dobbs (leak) | 0.0012 | 0.0087 |
| Dobbs (decision) | 0.0001 | 0.0105 |
| Rittenhouse | 0.052 | 0.0571 |

Better than percentile rank, but still net negative: Rittenhouse is
essentially unchanged (0.052 → 0.057), while Depp and Dobbs both lose an
order of magnitude of significance. Dobbs' decision-day edit count (raw
z=49.9) genuinely reflects an extraordinarily unlikely volume spike;
capping it to reduce edit-count's influence on the composite discards real
evidence for the events where volume was the correct signal.

## Conclusion

Across three different combining functions (equal-weight raw z-score,
percentile rank, winsorized z-score), `z_revert_rate` alone stays roughly
stable for Rittenhouse (p ≈ 0.03–0.05) while every attempt to help it via
the composite either fails to move it or actively weakens the other three
events. This is not evidence that the "right" weighting or rescaling
hasn't been found yet — it is evidence that **no single composite score
serves all four events well**, because they are not the same kind of
phenomenon:

- Depp v. Heard and both Dobbs dates: high-volume, comparatively
  low-conflict — large audiences editing constructively, not fighting.
- Rittenhouse: lower-volume but genuinely contested — the signal lives in
  *how* people are editing, not how many are.

A composite score is a bet on which of these matters more, and that bet
cannot be won in general. **The methodologically correct choice, supported
by this evidence rather than assumed in advance, is to report
`z_edits_count` and `z_revert_rate` as separate signals** rather than
forcing them into one number. This was one of the two options identified
at the design stage (README/Part 5) and this analysis empirically resolves
which one is right for this data, rather than picking one on convenience.

The raw, pre-registered `anomaly_score` from Part 1 remains the project's
primary confirmatory result. Attempts 1 and 2 are reported here to show
the reasoning was tested rather than assumed, and to document why the
project ultimately does not recommend a single composite score as the
detector.