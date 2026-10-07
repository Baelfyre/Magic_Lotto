# Lotto Data Cleaning and Normalization Report

## Scope

This cleaning pass covers:

- `swertres9pm.md`
- `6-42.csv`

The raw files were left unchanged. Cleaned outputs were written as separate CSV files.

## Source integrity

| Source | SHA-256 |
|---|---|
| `swertres9pm.md` | `b8c1e1f762c8b3059956d96b344804498bc20bc9f174a358fc616ae115ecb1a3` |
| `6-42.csv` | `9d8bf396373cd20ac197f423ed245407fa701bbd28895b2bb55e1dca92e3e8a8` |

## 3D Lotto 9PM

### Raw audit

- Raw data rows: **3,729**
- Exact duplicate rows removed: **6**
- Cleaned canonical rows: **3,723**
- Valid draw-result rows: **3,718**
- Rows with missing combination (`--`): **5**
- Remaining duplicate draw dates after cleanup: **0**
- Date range: **2016-01-02 to 2026-10-07**

### Transformations

1. Removed only **exact duplicate records**.
2. Converted draw dates from `M/D/YYYY` to ISO `YYYY-MM-DD`.
3. Preserved 3D combinations as text in `x-x-x` form.
4. Split each valid combination into `digit_1`, `digit_2`, and `digit_3`.
5. Standardized game metadata into `lotto_game = 3D Lotto` and `draw_session = 9PM`.
6. Converted jackpot values to numeric decimal text without thousands separators.
7. Converted winners to integers.
8. Preserved rows containing `--` as `missing_combination`; no result was guessed or imputed.
9. Sorted records chronologically.
10. Added `record_status` and `source_row` for auditability.

### Analysis-ready dataset

`swertres_9pm_analysis_ready.csv` contains only rows with a valid three-digit result. Missing-result rows remain in the canonical cleaned file but are excluded from the analysis-ready copy.

## Lotto 6/42

### Raw audit

- Raw data rows: **1,609**
- Exact duplicate rows removed: **4**
- Cleaned canonical rows: **1,605**
- Invalid combination rows after validation: **0**
- Remaining duplicate draw dates after cleanup: **0**
- Date range: **2016-01-02 to 2026-10-06**

### Transformations

1. Removed only **exact duplicate records**.
2. Trimmed whitespace from source column names and values.
3. Converted draw dates from `M/D/YYYY` to ISO `YYYY-MM-DD`.
4. Preserved the published six-number order in `combination_published`.
5. Added `combination_sorted` as a canonical unordered representation for set-based analysis.
6. Split each draw into `number_1` through `number_6`.
7. Validated that every draw has exactly six distinct numbers in the range 1 to 42.
8. Standardized combinations to two-digit text such as `03-07-16-25-31-42`.
9. Removed the `PHP` label and thousands separators from jackpot values while preserving two decimal places.
10. Converted winners to integers.
11. Sorted records chronologically.
12. Added `record_status` and `source_row` for auditability.

## Cleaning boundaries

No missing lottery result was inferred from surrounding draws. No statistical imputation was used. No outlier was removed based on jackpot size, winner count, digit frequency, or number frequency. Those values may be analytically interesting and should remain available for later statistical testing.

The cleaned datasets are suitable for the next stage: descriptive statistics, randomness diagnostics, chronological train/validation/test splitting, Monte Carlo baselines, and later ML/JEV evaluation.
