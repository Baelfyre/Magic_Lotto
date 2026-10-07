# Phase 2: Statistical EDA and Preliminary Randomness Diagnostics

## Purpose

This phase asks whether the cleaned historical results show obvious deviations from the behavior expected under a fair random process.

This is **not** yet a prediction phase. The results below are diagnostics only. Apparent frequency differences are not treated as predictive evidence unless they later survive chronological backtesting and Monte Carlo comparison.

## Evaluation rule

For this experiment, number placement is not used as the main prediction target.

- **Lotto 6/42:** each draw is treated as an unordered set of six distinct numbers.
- **3D Lotto 9PM:** each draw is represented by an unordered three-digit **multiset**, so repeated digits are preserved. For example, `1-1-7`, `1-7-1`, and `7-1-1` map to the same canonical form `1-1-7`.

The original published order remains in the canonical cleaned data for auditability.

---

# 1. 3D Lotto 9PM

## Dataset

- Valid draws analyzed: **3,718**
- Total digit observations: **11,154**
- Date range: **2016-01-02 to 2026-10-07**

## 1.1 Pooled digit frequency

Under a simple fair-digit model, each digit 0-9 has an expected share of 10%.

- Chi-square statistic: **9.0536**
- Degrees of freedom: **9**
- p-value: **0.43234**

Most frequent digits in the historical sample:

|   digit |   observed_count |   observed_pct |
|--------:|-----------------:|---------------:|
|   7.000 |         1157.000 |         10.373 |
|   0.000 |         1154.000 |         10.346 |
|   1.000 |         1147.000 |         10.283 |

Least frequent digits in the historical sample:

|   digit |   observed_count |   observed_pct |
|--------:|-----------------:|---------------:|
|   8.000 |         1050.000 |          9.414 |
|   6.000 |         1091.000 |          9.781 |
|   9.000 |         1094.000 |          9.808 |

### Interpretation

This test asks whether pooled digit counts differ more from equal 10% frequencies than expected from ordinary sampling variation.

A small p-value would justify **further investigation**, not a claim that a digit is more likely in the next draw. Later Monte Carlo testing will determine whether the same level of deviation is common in simulated fair histories of equal length.

## 1.2 Repetition structure

For three independent fair decimal digits, the theoretical pattern probabilities are:

- All three digits distinct: 72%
- Exactly one pair: 27%
- Triple: 1%

Observed versus expected:

| Pattern | Observed | Expected |
|---|---:|---:|
| All distinct | 2644 | 2676.96 |
| One pair | 1033 | 1003.86 |
| Triple | 41 | 37.18 |

- Chi-square statistic: **1.6442**
- Degrees of freedom: **2**
- p-value: **0.439514**

## 1.3 Preliminary serial diagnostic

Lag-1 correlation of the three-digit sum:

- **r = -0.0033**

This is only a coarse diagnostic. The next phase will use simulation and chronological backtesting rather than treating this single correlation as evidence of predictability.

---

# 2. Lotto 6/42

## Dataset

- Valid draws analyzed: **1,605**
- Total selected-number observations: **9,630**
- Date range: **2016-01-02 to 2026-10-06**
- Expected appearances per number under equal marginal frequency: **229.29**

## 2.1 Number frequency

- Preliminary Chi-square statistic: **24.1209**
- Degrees of freedom: **41**
- Nominal p-value: **0.983433**

Most frequent numbers in the historical sample:

|   number |   observed_count |   observed_pct_of_draws |
|---------:|-----------------:|------------------------:|
|   18.000 |          253.000 |                  15.763 |
|   31.000 |          250.000 |                  15.576 |
|   41.000 |          250.000 |                  15.576 |
|   12.000 |          244.000 |                  15.202 |
|   36.000 |          244.000 |                  15.202 |

Least frequent numbers in the historical sample:

|   number |   observed_count |   observed_pct_of_draws |
|---------:|-----------------:|------------------------:|
|   28.000 |          207.000 |                  12.897 |
|   26.000 |          211.000 |                  13.146 |
|   11.000 |          212.000 |                  13.209 |
|   32.000 |          215.000 |                  13.396 |
|   40.000 |          215.000 |                  13.396 |

### Important limitation

The six numbers inside a 6/42 draw are sampled **without replacement**, so number counts within the same draw are not independent. The Chi-square result is therefore treated only as a preliminary marginal-frequency diagnostic.

The stronger test in the next phase will compare the observed statistic with simulated fair 6/42 histories of the same size.

## 2.2 Consecutive-draw overlap

- Observed mean shared numbers between consecutive draws: **0.8647**
- Theoretical expected overlap for two independent 6-of-42 draws: **0.8571**

This is descriptive at this stage. Monte Carlo simulation will determine whether the observed overlap behavior is unusual.

---

# 3. Current evidence boundary

At the end of Phase 2:

1. Historical frequency differences are **observations**, not predictions.
2. No "hot" or "cold" number is treated as having increased future probability.
3. No machine-learning model has yet been trained.
4. No JEV verdict should yet classify a predictive signal as credible.
5. Any potentially unusual statistic must first survive simulation-based calibration and out-of-sample testing.

## Next phase

**Phase 3: Monte Carlo Random Baseline**

For each game, generate many fair synthetic histories matching the real sample size and compare:

- digit/number frequency deviations,
- Chi-square statistics,
- repetition patterns,
- consecutive-draw overlap,
- other selected diagnostics.

The goal is to estimate how often apparently "interesting" patterns arise from randomness alone.
