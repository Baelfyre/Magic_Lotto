# Product Requirements Document
<!-- @codebase_provenance_JEO -->

- **Status:** Proposal for human review; not implementation authorization
- **Baseline:** `origin/main` at `998f16d133b4500dfd65fa57fb73f9d84c91f8f4` (merged PR #4)
- **Prepared:** 2026-10-17
- **Last reviewed:** 2026-10-17
- **Research verdict:** `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`

## Executive overview

Phase 8 proposes a transparent educational and experimental randomizer for the Philippine Lotto 6/42 only. It excludes 3D Lotto, every other lottery game, and unrelated prediction systems. The product separates a uniform fair-random generator (G0), an experimental historical-weighting control (G1), and a calibrated soft-constraint experiment (G2). G0 is the default. Historical resemblance, descriptive structure, and generator fidelity are not evidence of predictive advantage.

Versioned JSON and JSONL research artifacts are the proposed v1 storage. The web client is static and runs generation in the visitor's browser. It does not upload or centrally store visitor combinations. A separate, read-only public registry may display frozen project research batches after they have been registered before a draw. It is not a submission endpoint. Official-result collection is blocked pending verified access and reuse authority. The existing validation and locked-test partitions remain sealed, and the STOP verdict remains in force.

This document and its five companion documents are proposals. None describes implemented Phase 8 behavior or permits implementation, collection, deployment, or a change to the research verdict.

The merged PR #4 is the implementation foundation, not a Phase 8 implementation. It added the installable `src/magic_lotto/` package for the Phase 7 train-only analysis, shared notebook bootstrap, and repository migration documentation. No Phase 8 G0/G1/G2 generator, public result collector, web client, registry, general JSON/JSONL research-artifact store, or prospective evaluation service is implemented. See the [repository architecture](../../architecture/REPOSITORY_ARCHITECTURE.md) for the current module responsibilities.

## Problem statement and research motivation

The repository contains historical analyses of Lotto 6/42. The current research record preserves a 902-draw training partition from 2016-08-30 through 2022-11-12 and a STOP verdict. Phase 7 is explicitly descriptive and reports that its training-only analysis did not access validation or locked-test rows. As one historical development result, Phase 5R reports mean combination NLL of 15.47294 for fair random and 15.49795 for raw expanding frequency on a validation partition already used in Phase 5A; that report says this is not pristine confirmation and that the locked test remains unopened. This does not establish predictive advantage or support advertising G1 as superior.

People exploring lottery numbers can mistake historical frequencies or visually striking patterns for predictive evidence. Phase 8 should make the chance baseline visible, label experimental generators honestly, preserve the research boundary, and distinguish a model that reproduces selected historical summaries from one that improves a pre-registered future outcome score.

## Product vision and objectives

### Vision

Provide an auditable educational randomizer that can generate valid combinations, explain its probability model, and support carefully frozen prospective research without presenting lottery combinations as forecasts.

### Objectives

1. Make G0 uniform fair-random generation the default and explain the equal-probability baseline.
2. Keep G1 and G2 opt-in, versioned, and visibly experimental.
3. Let visitors generate and download combinations locally without a central visitor-data store.
4. Display only research artifacts whose provenance, status, and permitted source use have been reviewed.
5. If prospective research is approved, register an immutable study manifest before its target draw and evaluate it using the frozen protocol.
6. Preserve the existing training, validation, locked-test, and verdict boundaries.

## Target users and stakeholders

| Stakeholder | Need | Boundary |
| --- | --- | --- |
| Curious visitor | Generate combinations and understand how the modes differ | No promise of improved odds; visitor choices remain in-browser |
| Research reader | Inspect methods, sources, model versions, and limitations | Only approved and traceable artifacts are shown |
| Research maintainer | Reproduce training-only fitting and publish versioned artifacts | No validation or locked-test access; changes are reviewed and versioned |
| Data steward | Verify official observations and preserve corrections | Collection stays disabled until access and reuse rights are approved |
| Reviewer | Check requirements, formulas, tests, and registration timing | Must be independent of the implementation and study outcome where practical |

## User needs and user stories

- As a visitor, I want the default mode to sample six distinct values uniformly from 1 through 42 so I can use a neutral baseline.
- As a visitor, I want each experimental mode identified with its model version and limitations so I do not mistake it for a forecast.
- As a visitor, I want to see and download my generated lines without creating an account or sending them to the project.
- As a research reader, I want the chance distribution and source status explained next to plots so visual patterns are not mistaken for prediction.
- As a maintainer, I want a frozen manifest and independently verifiable timestamp before an outcome so prospective evaluations cannot be rewritten after the draw.
- As a reviewer, I want a clear audit trail from a requirement to a component, test, and milestone.

## Functional requirements

Each requirement is proposed and requires approval. Acceptance evidence is planned in [02 Technical Requirements](02_TECHNICAL_REQUIREMENTS.md) and [06 Implementation Plan](06_IMPLEMENTATION_PLAN.md).

| ID | Requirement | Priority | Acceptance evidence |
| --- | --- | --- | --- |
| FR-001 | The client shall generate combinations containing exactly six distinct integers from 1 through 42. | Must | `TEST-001`, `TEST-002` |
| FR-002 | G0 shall be selected by default and shall sample uniformly without replacement; it shall have no mandatory structural or Jaccard filter. | Must | `TEST-003`, `TEST-004` |
| FR-003 | G1 shall be available only as an opt-in historical-weighting control with its model version and training provenance displayed, after its predeclared concentration guardrail passes. | Should | `TEST-005`, `TEST-012` |
| FR-004 | G2 shall remain unavailable to visitors until its parameters are calibrated on approved training data and its target distribution, sampler, and predeclared concentration guardrail pass review. | Must | `TEST-006`, `TEST-007`, `TEST-013` |
| FR-005 | The client shall reject invalid batch sizes and duplicate, missing, non-integer, or out-of-range ball inputs wherever manual input is offered. | Must | `TEST-002` |
| FR-006 | Independent generation with replacement shall be the default batch behavior; optional distinct-line batches shall be explicitly labelled and shall not be described as independent draws. | Must | `TEST-004` |
| FR-007 | The client shall explain the fair baseline, exact match-count distribution, model status, and non-predictive limitations in plain language. | Must | `TEST-014` |
| FR-008 | Historical-result exploration shall consume only reviewed, permitted, versioned public artifacts and shall show source, verification, and correction status. | Must | `TEST-015` |
| FR-009 | The interface shall display generator name, model/configuration version, training cutoff, and artifact provenance for experimental output. | Must | `TEST-012` |
| FR-010 | Visitors shall be able to copy or download their locally generated combinations without an account or network submission. | Should | `TEST-016` |
| FR-011 | A public prospective registry, if approved, shall be read-only and shall display only project-generated batches frozen before the corresponding draw. | Must | `TEST-017` |
| FR-012 | Evaluation shall use only outcomes after a frozen registration, and it shall follow a predeclared metric and analysis plan. | Must | `TEST-018`, `TEST-019` |
| FR-013 | Any result collector shall remain disabled until source identity, ordinary access conditions, applicable terms and robots rules, reuse scope, operating limits, and a human review owner are documented and approved. Written permission is required only when applicable law, source terms, or a source-specific restriction requires it. | Must | `TEST-020` |
| FR-014 | All product models, result records, filters, and research displays shall be restricted to Philippine Lotto 6/42; other games shall be rejected or ignored. | Must | `TEST-023` |
| FR-015 | The interface shall distinguish fair-draw probability, model selection probability, and historical pattern frequency, with their separate meanings and denominators. | Must | `TEST-014` |
| FR-016 | The product shall present an independent educational-project disclaimer and shall not imply PCSO or government affiliation, guaranteed wins, or established predictive effectiveness. | Must | `TEST-014` |
| FR-017 | Future result ingestion shall use source-specific adapters, normalized Lotto 6/42 records, provenance, conflict quarantine, and offline parser fixtures before any separately approved live pilot. | Must | `TEST-024`, `TEST-020` |

## Nonfunctional requirements

| ID | Requirement | Proposed acceptance target |
| --- | --- | --- |
| NFR-001 | Privacy | No visitor-generated numbers, account, or personal profile data are sent to project storage in v1. Hosting-provider request metadata may exist and must be covered by the selected host's privacy review and the product notice. |
| NFR-002 | Accessibility | Meet WCAG 2.2 AA as an implementation target, verified by automated checks plus keyboard, screen-reader, contrast, zoom, and manual interaction review. This is a target, not a current conformance claim. |
| NFR-003 | Scientific integrity | Keep statistical fidelity separate from predictive effectiveness; no promotion based on visual patterns, an unregistered outcome, or an uncorrected multiple comparison. |
| NFR-004 | Reproducibility | Every research model and frozen batch shall reference immutable versions and cryptographic hashes; runtime browser randomness shall not be claimed reproducible from an unrecorded seed. |
| NFR-005 | Compatibility | Support current desktop and mobile browsers with Web Crypto; provide a clear unsupported-browser state instead of silently falling back to biased randomness. Exact browser support policy is a pre-implementation decision. |
| NFR-006 | Performance | Proposed target: generate 100 G0 lines within 1 second at the 95th percentile on an agreed reference mobile browser after page load. Establish and record the reference device before implementation acceptance. |
| NFR-007 | Resilience | A failed artifact parse or integrity check shall fail closed, identify the affected artifact, and leave visitor-local output intact. |
| NFR-008 | Maintainability | Keep the Python research engine, serialized contracts, and static client separated; do not add a server database for v1 without a separately approved requirement. |

## G0, G1, and G2 user-facing capabilities

- **G0 uniform fair-random (default):** choose six distinct numbers uniformly from the 42-number universe. Every unordered combination has probability `1 / 5,245,786`. Multiple lines are independently generated by default and may repeat as complete lines. A separately labelled distinct-line batch is a different sampling design.
- **G1 historical-weighting control (experimental):** use smoothed marginal weights fitted only from approved training data and a fixed-cardinality normalizer. Before fitting, approve a concentration diagnostic and threshold; G1 remains unavailable if the resulting distribution fails that guardrail. It is a control for research comparison, not a recommendation. The prior repository evidence does not support advertising it as superior.
- **G2 calibrated soft-constraint generator (experimental, gated):** use a low-dimensional, regularized exponential-family distribution over all valid combinations. Candidate features include odd/even composition, high/low composition, sum, sorted gaps, and consecutive structure. Parameters must be fitted and frozen using approved training-only development folds. Finite parameters must leave every valid combination with nonzero probability, but positive support alone does not prevent near-concentration. Approve a concentration diagnostic and threshold before the feature/parameter search; G2 remains unavailable if the fitted distribution fails it. The exact normalization and sampler must also be validated before release.

No mandatory filter excludes a valid combination from G0. A user-selected distinct-line mode must not be represented as independent line sampling. G2 is not authorized merely because a UI option is specified.

## Research transparency and interpretation requirements

For one fixed valid line and an independent fair 6/42 draw, the number `K` of matching balls follows:

\[
P(K=k)=\frac{\binom{6}{k}\binom{36}{6-k}}{\binom{42}{6}},\quad k=0,\ldots,6.
\]

The expectation is `E[K]=6/7`. The denominator is `C(42,6)=5,245,786`. The exact numerator sequence for `k=0..6` is `1,947,792; 2,261,952; 883,575; 142,800; 9,450; 216; 1`; the numerators sum to the denominator. Jackpot probability is `M/C` for `M` distinct lines, and `1-(1-1/C)^M` for `M` independent generated lines with replacement. These calculations describe chance, not a model's measured performance.

For two six-number sets with intersection size `r`, Jaccard distance is `d_J = 1 - r/(12-r) = (12-2r)/(12-r)`. If an explicitly selected rule requires `d_J >= d_min`, then `r <= floor(12(1-d_min)/(2-d_min))`; because `r` is an integer from 0 through 6, apply the bound to this discrete set. The possible distances for `r=0..6` are `1, 10/11, 4/5, 2/3, 1/2, 2/7, 0`. A diversity rule changes the sampling distribution and is not imposed on G0. All empirical visualizations must show their sample, source, cutoff, and comparison baseline. Claims of accuracy, significance, entropy, or generator acceptance rate require actual, reviewed evidence and are not supplied by this proposal.

Display and store three distinct probability categories:

1. **Fair-draw probability:** under a fair, independent Lotto 6/42 draw, one specified valid combination has probability `1/5,245,786`, approximately `0.00001906%`, of matching all six numbers. Every valid combination has this same jackpot probability.
2. **Model selection probability:** `P_G1(S)` or `P_G2(S)` is the probability that a specified, validated generator distribution selects combination `S`. It describes the model's output distribution and is not the draw's probability of producing `S` or a probability of winning. Show exact model values or percentages only after mathematical normalization and validation; otherwise show “Not calculated” or “Not established.”
3. **Historical pattern frequency:** the observed count of a precisely defined pattern divided by the stated dataset size. Training summaries must state the 902-record sample, 2016-08-30 through 2022-11-12 date range, dataset/version hash, and feature definition. These are descriptive measurements, not future probabilities.

Never describe generated combinations as guaranteed winning numbers or advertise predictive effectiveness without independently verified evidence. When a probability is unavailable, do not replace it with a model score or an estimate from an undefined denominator.

## Official results exploration requirements

The UI may provide a source-aware explorer only after a result source and reuse mode have been reviewed. PCSO is the authoritative publisher and the preferred source candidate: its public search page exposes date and game controls and a results table, but the request method, hidden WebForms state, pagination, robots rules, and applicable reuse terms remain unverified. No API or reuse permission is claimed. LottoPCSO.com is an independent third-party comparison source, not an official publisher; its disclaimer says results are informational, may not be complete or accurate, and directs readers to PCSO for verification. Its terms, robots rules, automated-access conditions, and reuse scope require review before any adapter or republication. LottoMatik is excluded from automation for now; an earlier source review recorded restrictions on automated access and reuse, while its current terms could not be reverified in this review. It may be considered only for manual comparison after current terms review. FOI is not an operational acquisition dependency. Public accessibility or the absence of an explicit notice is not permission. Written permission is required when applicable law, terms, or source-specific restrictions require it. Missing values remain `null`, never inferred or fabricated.

## Project disclaimer

Magic Lotto is an independent educational and experimental project focused only on Philippine Lotto 6/42. It is not affiliated with, authorized by, sponsored by, or endorsed by the Philippine Charity Sweepstakes Office (PCSO) or any Philippine government agency. Its research purposes include machine learning experimentation, probability theory, statistical pattern analysis, random-behavior analysis, probabilistic combination generation, and statistical simulation and comparison. Generated combinations are not predictions or guaranteed winning numbers. Under a fair draw, every valid Lotto 6/42 combination has the same 1 in 5,245,786 jackpot probability. A model's probability of selecting a combination describes its own output distribution, not the chance that the draw will produce that combination. Historical pattern frequencies describe recorded data and do not establish future predictive effectiveness. Magic Lotto does not sell lottery tickets, accept wagers, or operate games. PCSO is identified as the authoritative draw-result publisher; independent reference sites are labelled third-party and remain subject to access and reuse review.

The initial client can ship without a results explorer if no reviewed result artifact exists. It may explain the source-status gate and link to the publisher, but it must not imply that a linked source has approved project reuse.

## Privacy and consent boundaries

- Browser-local generation only; no submission endpoint, analytics payload containing generated lines, or visitor registry in v1.
- Download is initiated by the visitor and remains their local file.
- Public registration is for frozen project-generated research batches, not visitor submissions.
- Do not create consent records for data that is not collected. Any later visitor submission, account, feedback capture, or cross-device persistence requires a separate privacy design and approval.
- Static hosts can log request metadata. [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) specifically says visitor IP addresses are logged and stored for security. Hosting choice, retention, jurisdiction, notice, and operational access require provider-specific deployment review.
- Source collection and source reuse are independent approvals from randomizer development.

## In-scope and out-of-scope features

**In scope for the proposal:** Philippine Lotto 6/42 only; mathematical and artifact contracts; local G0 product behavior; gated G1/G2 capabilities; source-status presentation; a reviewed, low-frequency public factual-result acquisition design; read-only static registration; future testing, accessibility, privacy, and research gates.

**Out of scope for Phase 8/v1:** 3D Lotto, all other lottery games, unrelated prediction systems, ticket sales, payments, account profiles, gambling transactions, visitor-combination uploads, public comments, central analytics of generated lines, a database, an API backend, an enabled collector, forecasting claims, automated wager advice, an FOI-dependent collection process, and access to the existing validation or locked-test partitions.

## Minimum viable product definition

The proposed first release contains a static, accessible G0 generator, client-side copy/download, an explanation of fair odds and research limits, and only those versioned research summaries approved for publication. G1 can be added as an experimental control after its sampler and provenance checks pass. G2 is deferred until its training-only calibration, exact normalization, sampler fidelity, and computation-cost gates pass. If no historical results artifact has approved source/reuse status, the MVP omits the results explorer. The public research registry and any collector are separate milestones, not MVP prerequisites.

## User acceptance criteria

1. First load selects G0 and clearly states that all valid combinations have equal jackpot probability under the fair baseline.
2. Every generated line contains six distinct integers in range; no deterministic pattern filter is applied to G0.
3. The UI distinguishes independent sampling with replacement from an optional batch of distinct lines.
4. G1 and G2 are visibly marked experimental; G2 cannot be enabled before its approval gate.
5. Copy/download works without sending the numbers to a server.
6. Unsupported randomness, malformed model artifacts, or failed source verification produces a clear error and no silent fallback.
7. Screen-reader and keyboard users can perform all primary actions; charts have text alternatives.
8. The current research verdict and sealed partition boundary remain visible in research material.

## Assumptions, dependencies, and unresolved decisions

| Item | Status | Required resolution |
| --- | --- | --- |
| AGY reconciled proposal | `[NEEDS SOURCE]` Not found in supplied attachments or repository during this task | Provide the exact proposal before claiming AGY-specific reconciliation |
| Codex reconciled proposal | Conversation-history source; no standalone repository artifact found | Human reviewer may supply a canonical saved copy |
| Framework | Vite/React/TypeScript is a proposal; no frontend exists on the baseline | Approve stack and browser support policy before implementation |
| PCSO automated access/reuse | `REVIEW_REQUIRED` | Review current terms, robots rules, ordinary WebForms behavior, coverage, and applicable reuse conditions; request written permission only if required; do not enable an adapter before human review |
| LottoPCSO.com automated access/reuse | `REVIEW_REQUIRED` | Review current terms, robots rules, accuracy/correction handling, and reuse scope; cross-check any observation with PCSO before official verification |
| LottoMatik automation | `EXCLUDED_PENDING_CURRENT_TERMS_REVIEW` | Keep the adapter excluded; reverify the previously recorded restrictions before any policy change |
| FOI acquisition | `EXCLUDED` | No FOI workflow is required for ordinary automated updates; source-specific access and reuse review still applies |
| Hosting provider | Unresolved; evaluate GitHub Pages and Cloudflare Pages | Privacy, build, URL, deployment control, and operational review |
| G2 parameters | Uncalibrated and unapproved | Fit on approved training folds; independent review and freeze |
| Prospective sample size | Unset | Complete a power/sensitivity analysis for a predeclared primary endpoint |
| Timestamp authority | Not selected | Approve an independent RFC 3161 TSA and token retention/verification procedure |
| Research verdict | Existing STOP verdict preserved | Revisit only through separately governed, independently reviewed evidence |

## Source basis and limits

Repository facts were checked at `origin/main` commit `998f16d133b4500dfd65fa57fb73f9d84c91f8f4`, which merges PR #4: [README](../../../README.md), [Phase 7 report](../../PHASE7_KMEANS_DESCRIPTIVE.md), [Phase 5R report](../../../reports/phase5r_predictive_information.md), [Phase 6B adjudication](../../../reports/phase6b_642_semantic_adjudication.json), [repository structure](../../REPOSITORY_STRUCTURE.md), [repository architecture](../../architecture/REPOSITORY_ARCHITECTURE.md), [file migration map](../../architecture/FILE_MIGRATION_MAP.md), [migration manifest](../../REPOSITORY_LAYOUT_MIGRATION.json), [path policy](../../architecture/IMPORT_AND_PATH_POLICY.md), [notebook guide](../../architecture/NOTEBOOK_EXECUTION_GUIDE.md), and [`pyproject.toml`](../../../pyproject.toml). The Phase 7 report states that it uses only the established 902-row training partition and that `source_row` is provenance metadata, not a chronological key. PR #4's migration manifest records the hashes of moved data and historical artifacts; this proposal does not alter them.

External sources checked 2026-10-17: [PCSO official Lotto result search page](https://www.pcso.gov.ph/searchlottoresult.aspx), [LottoPCSO.com 6/42 history](https://www.lottopcso.com/6-42-lotto-result-history-and-summary/), [LottoPCSO.com disclaimer](https://www.lottopcso.com/disclaimer/), [LottoMatik result page](https://lottomatik.pcso.gov.ph/lotto-results), [LottoMatik terms](https://lottomatik.pcso.gov.ph/terms), [RFC 3161](https://www.rfc-editor.org/info/rfc3161/), [GitHub Pages overview](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [Cloudflare Pages Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/), and [GitHub Actions scheduled-workflow limits](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows). The PCSO page was visible with date/game search controls and a mixed-game results table, but its request mechanics, robots rules, and reuse conditions were not resolved; visibility does not establish an API or permission. LottoPCSO.com was visible with 6/42 history and a disclaimer identifying it as unaffiliated and directing readers to PCSO for verification; its current automation/reuse terms remain unreviewed. The LottoMatik terms page could not be reverified in this review, so its prior exclusion remains. FOI is excluded as a collection dependency. The AGY proposal remains unavailable.
