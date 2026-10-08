# Magic Lotto

Magic Lotto is a simple exploratory project that looks at past 3D Lotto 9PM and Lotto 6/42 results to see whether previous draws contain any useful pattern that may help estimate the next number combination.

## What is this project about?

It explores whether past draws can help estimate complete combinations for future draws. It focuses on full combinations, not on finding numbers that appeared most often.

## Purpose

The project tests whether past results can provide useful information for future draws. It does not assume that often repeated numbers are more likely to appear.

## What is the project trying to achieve?

It compares different ways of studying past draws with normal random guessing. The goal is to see whether any method can estimate complete combinations more reliably.

## Current assessment

The research found a few small patterns in past data, including one in historical Lotto 6/42 results. They did not consistently help estimate complete future combinations better than random guessing. The current status is `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`, so further prediction testing with this dataset has stopped.

The locked test data remains unopened.

## Important note

These results do not prove that lottery prediction is impossible. They only show that the data and methods tested so far did not find a reliable advantage.

## Project structure

```text
Magic_Lotto/
├── data/        Data used during the research
├── scripts/     Programs used to clean and study the data
├── notebooks/   Step-by-step research notebooks
├── models/      Saved settings used during testing
├── reports/     Results and checks from each research stage
├── docs/        Final project documentation
└── README.md    Overview of the project
```

Some earlier research files remain in the top folder because the saved scripts and records refer to them there.

## Research files

The project keeps the original data, cleaned data, scripts, notebooks, and reports so the work can be reviewed and repeated. The `data/` folder currently contains files prepared for later analysis.

The [Phase 6B review notebook](notebooks/lotto_phase6b_model_semantic_review.ipynb) explains how the tested models and patterns were reviewed before deciding whether any model was ready for final testing.

## Research stages

- Clean and check the historical lottery data.
- Look for patterns and unusual results.
- Compare the real results with random simulated draws.
- Prepare past-draw information without looking at future results.
- Test whether prediction methods perform better than random guessing.
- Check whether small patterns help estimate complete future combinations.
- Review the evidence before deciding whether more prediction testing is justified.
