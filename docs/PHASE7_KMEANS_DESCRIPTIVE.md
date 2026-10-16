# Phase 7: K-means descriptive clustering experiment

**Classification:** Exploratory analysis only. This does not reverse the existing project verdict `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`.

## Objective and scope

Inspect whether unordered 6/42 training draws form visually interpretable groups and whether their K-means compactness is unusually high relative to independent fair-random 6/42 histories.

- Source: existing `lotto_6_42_cleaned_normalized.csv` at repository root.
- Preserved training partition: 902 draws, August 30, 2016 through November 12, 2022, source rows 103 through 1008.
- The reader consumes only the first 1003 cleaned records and asserts the train boundary before selecting the established 902-row training partition.
- No validation or locked test rows are read or scored. Previous test-seal policy remains in force.
- Original data and prior analyses are not modified.

## Method

An unordered six-number draw becomes a 42-element binary vector containing exactly six ones. Applying K-means to the raw sorted six integers would introduce misleading positional distances, so we instead use number membership. K-means minimizes Euclidean within-cluster sum of squares in indicator space.

A fixed `k=6`, `random_state=162`, and `n_init=5` define the inferential reference comparison. The elbow chart from k=2 to k=8 is descriptive only; its shape does not constitute selection evidence. PCA is used only for a two-dimensional illustration.

Each of 100 synthetic reference datasets contains 902 independent uniform 6-of-42 sets. The same k and K-means fit specification is applied to every synthetic dataset. The one-sided empirical lower-tail probability is `(1 + number of null inertias <= actual inertia) / (simulations + 1)`. A lower inertia can indicate closer historical grouping under the chosen algorithm, not future drawing advantages.

The per-ball frequency and pair-count residual charts are also descriptive. Their unadjusted visual differences should not be treated as individually significant tests. Cluster medoids are actual past combinations chosen to explain the groups, not recommendations for wagers.

## Reproduce

From the repository root:

```bash
python -m pip install -r requirements-phase7.txt
python -m unittest discover -s tests -p "test_phase7*.py" -v
python scripts/phase7_kmeans_642.py --null-replicates 100 --seed 162
```

Run `notebooks/lotto_phase7_kmeans_descriptive.ipynb` from the same directory to display all generated figures.

The run writes `reports/phase7_kmeans_642/summary.json`, `reports/phase7_kmeans_642/README.md`, and six PNG charts. These outputs must be generated and reviewed before describing Python-run quantitative results as verified.

## Independent preliminary screen (not Python execution)

An independent in-memory calculation inspected the 902 existing repository training draws with a custom deterministic K-means implementation and 100 simulated fair histories. It produced approximate inertia 4167.34 (actual), mean fair-reference inertia 4156.41, and one-sided lower-tail p = 0.911. Its centroid initialization and pseudo-random generator differ from scikit-learn/NumPy, so the actual Python results must not be represented as identical to this preliminary screen.

The preliminary outcome does not establish compactness beyond the fair-random reference and does not support predicting a future combination.

## Governance and limitations

Historical clusters always exist after K-means fitting, even when every combination is generated independently and uniformly. Any result from this work remains exploratory, especially given prior exploration of the dataset and prior validation usage. Do not reopen sealed test targets, use cluster patterns as probability claims, or promote this analysis to an approved forecast.

No TypeSafe/JEV call is required to adjudicate this bounded descriptive experiment; any future predictive phase would require a separately reviewed design and authorization.
