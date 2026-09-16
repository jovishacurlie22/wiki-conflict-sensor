# Part 1: Pre-Registered Validation Results

## Hypothesis

Unusual patterns in Wikipedia editing behavior — edit volume, revert rate,
and editor churn — correspond to real-world events and controversy
affecting the article's subject.

## Method (summary)

Four event dates were registered **before** any anomaly detection was run,
tied to three articles chosen for their well-documented controversy:

| Article | Event | Date |
|---|---|---|
| Kyle Rittenhouse | Trial verdict | 2021-11-19 |
| Depp v. Heard | Trial verdict | 2022-06-01 |
| Dobbs v. Jackson | Draft opinion leaked | 2022-05-02 |
| Dobbs v. Jackson | Decision issued | 2022-06-24 |

Each article's revision history was cleaned and binned into a daily time
series (`edits_count`, `revert_rate`, `editor_churn`, among others), then
each signal was z-scored against that article's own baseline — computed
**excluding** a ±3 day window around every registered date, so an event
couldn't inflate its own "normal" and mute its own signal. The three
z-scored signals most relevant to conflict (`z_edits_count`,
`z_revert_rate`, `z_editor_churn`) were combined into an equal-weighted
`anomaly_score`.

Significance was assessed with a one-sided permutation test: for each
registered event, the maximum signal value inside the ±3 day window was
compared against the maximum value in 10,000 randomly placed windows of the
same width, drawn from each article's non-event days. Max-in-window (rather
than mean) was used because a real-world reaction doesn't reliably land on
the exact day of the news — the detection question is "did this window
contain an unusual day," not "was this window unusual on average."

## Results

| Article / Event | `anomaly_score` p | `z_edits_count` p | `z_revert_rate` p | `z_editor_churn` p |
|---|---|---|---|---|
| Depp v. Heard (verdict) | **0.0001** | **0.0003** | 0.306 | 0.414 |
| Dobbs (leak) | **0.0012** | **0.0015** | 0.163 | 0.356 |
| Dobbs (decision) | **0.0001** | **0.0001** | 0.166 | 0.664 |
| Rittenhouse (verdict) | 0.052 | 0.061 | **0.031** | 0.266 |

(Bold = significant at uncorrected α=0.05. With a Bonferroni correction for
the 16 tests run — 4 events × 4 signals — only `z_edits_count` for Depp v.
Heard and both Dobbs dates survive the stricter α≈0.003 threshold.)

## Conclusion

**The hypothesis is partially supported, with an important qualification.**

Edit volume (`z_edits_count`) is a strong, statistically robust detector of
real-world attention: three of the four registered events show a highly
significant spike, surviving even conservative multiple-comparisons
correction. This confirms that Wikipedia edit activity does respond
measurably to real-world events.

However, edit volume **narrowly missed significance for the Rittenhouse
verdict** (p=0.052, uncorrected), and the equal-weighted `anomaly_score`
inherited that near-miss (p=0.052) because the score is volume-dominated —
`z_edits_count` runs an order of magnitude larger than the other two
signals, so averaging them gives edit count almost all the influence in
practice.

Critically, `z_revert_rate` was the **only** signal that detected the
Rittenhouse verdict (p=0.031) — and it was the *only* event any signal
other than edit count caught at all. This is consistent with a qualitative
difference between the events tested: the Depp v. Heard and Dobbs dates
appear to have driven mostly high-volume, low-conflict editing (people
adding content, not fighting over it), while the Rittenhouse verdict
produced a smaller but more contested response — exactly the pattern
`revert_rate` was designed to catch and `edits_count` is not well-suited
to.

`editor_churn` did not reach significance for any of the four events. This
is a genuine null result for that signal in this validation, not a data or
methodology failure — it is reported as-is.

## Implication for the composite score

Because the equal-weighted `anomaly_score` is effectively dominated by
`edits_count`'s scale, it buries the one signal that actually detected the
Rittenhouse verdict. This is a real, demonstrated limitation of naive
equal-weight averaging across signals with very different scales — not a
hypothetical concern. It motivates a follow-up, explicitly **post-hoc**
analysis (Part 2) that rescales the components before combining them, to
test whether a scale-corrected composite recovers detection of events like
Rittenhouse's without needing to re-run or alter this pre-registered test.