# Phase 8A: Lotto 6/42 mathematical core (G0 only)

**Status:** Implementation candidate for human review; not deployed or merged.

This milestone extends the existing `src/magic_lotto/` Python package. It does not re-run historical analyses, open validation/locked-test partitions, fit G1/G2, build a website, collect lottery results, or register research batches. The research assessment remains `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`.

## Implementation boundaries

| Module | Responsibility |
| --- | --- |
| `magic_lotto.domain.combination_642` | Strict, immutable sorted six-ball Lotto 6/42 values and input validation |
| `magic_lotto.research.g0_uniform` | Cryptographic G0 default; exact uniform sampling with injectable bounded-integer source for tests |
| `magic_lotto.research.fair_probability` | Exact combinatorial identities, hypergeometric match PMF, batch-match probabilities, Jaccard distance |
| `magic_lotto.application.use_cases.generate_g0` | Transient in-memory use-case entry point; no persistence |
| `tests/test_phase8a_g0.py` | Synthetic exhaustive toy sampling, contracts, no-I/O and numerical identities |

No DAO or repository was introduced: G0 does not need persistent storage or historical data. The existing Phase 7 DAO remains train-only and unchanged.

## Mathematical contract

A Lotto 6/42 line is exactly six unique integers from 1 through 42, serialized in ascending order. The valid unordered space contains `C(42,6) = 5,245,786` lines. Under a fair independent draw, every line has exact jackpot probability `1/5,245,786` (approximately `0.00001906%`). For `k` matching balls against a fixed line:

`P(K=k) = C(6,k) * C(36,6-k) / C(42,6)` for `k = 0..6`.

Numerators are `1947792, 2261952, 883575, 142800, 9450, 216, 1`; they sum to the space size. Expected matches are exactly `6/7`. For two lines overlapping in `r` balls, Jaccard distance is `(12-2r)/(12-r)`. Calculations return exact `fractions.Fraction` values, not purported predictions.

## G0 sampling semantics

`generate_g0()` defaults to `independent_with_replacement`, independently sampling each unordered six-number line via partial Fisher-Yates. Repeated *whole lines* are possible. The default bound generator is Python `secrets.randbelow` and there is no implicit pattern filter, model weighting, deterministic production seed, or training-data access.

The opt-in `distinct_sets` mode samples unique combination ranks via a sparse partial Fisher-Yates mapping and un-ranks them to sorted combinations. It is a different joint distribution, **not independent line sampling**. A visitor's transient result is not a `GeneratedBatch` or permission to store/upload visitor numbers.

The Phase 8A Python API accepts only integer batch sizes from 1 to 100. `MAX_BATCH_SIZE=100` is a documented initial API limit aligned with the future 100-line client performance target; it can be reconsidered during Phase 8C review. The pure toy samplers accept smaller synthetic universes for exhaustive tests. Injection of a deterministic bounded-integer source is for tests only; deployed G0 must use approved platform cryptographic randomness.

```python
from magic_lotto.application.use_cases.generate_g0 import generate_g0_lines
from magic_lotto.research.fair_probability import fair_exact_match_probability, match_count_pmf

result = generate_g0_lines(batch_size=3)
assert result.algorithm_id == "G0"
assert len(result.lines) == 3
print(fair_exact_match_probability())  # Fraction(1, 5245786)
print(match_count_pmf(6))              # Fraction(1, 5245786)
```

## Scope and acceptance status

- **TEST-001/002/003/004/023:** covered by the Phase 8A synthetic domain, sample-design, exact small-universe and Lotto 6/42 scope tests. A later browser implementation still requires its own tests.
- **TEST-008:** transient result schema labels are present (`schema_version`, `algorithm_id`, `game_id`, `sampler_contract_version`, `sampling_mode`). Full JSON/JSONL artifact lifecycle, hashes and persistence are **not** implemented or approved in 8A.
- **TEST-009:** pure Phase 8A G0 tests run with file access prohibited; historical validation/locked-test partitions are not opened. Existing Phase 7 training/data boundary remains unchanged.
- **TEST-005 (G1):** **deferred**, since training configuration, concentration diagnostics and separate authorization have not been approved. G2 remains deferred to Phase 8B.

This milestone does not validate Web Crypto parity, UI performance, source permissions, browser privacy, hosted Colab, prospective evaluation or any predictive improvement. Those are separate gates. The project is an independent educational experiment and is not affiliated with PCSO.
