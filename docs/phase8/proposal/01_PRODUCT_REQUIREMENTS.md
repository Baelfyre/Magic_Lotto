# Product Requirements Document
<!-- @codebase_provenance_JEO -->

- **Status:** Proposal for human review; not implementation authorization
- **Baseline:** `origin/main` at `b67e31572187001c89266839871c9e28456b90e8`
- **Prepared:** 2026-10-17
- **Research verdict:** `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`

## Executive overview

Phase 8 proposes a transparent Lotto 6/42 research randomizer and static web client. The product separates a uniform fair-random generator (G0), an experimental historical-weighting control (G1), and a calibrated soft-constraint experiment (G2). G0 is the default. Historical resemblance, descriptive structure, and generator fidelity are not evidence of predictive advantage.

Versioned JSON and JSONL research artifacts are the proposed v1 storage. The web client is static and runs generation in the visitor's browser. It does not upload or centrally store visitor combinations. A separate, read-only public registry may display frozen project research batches after they have been registered before a draw. It is not a submission endpoint. Official-result collection is blocked pending verified access and reuse authority. The existing validation and locked-test partitions remain sealed, and the STOP verdict remains in force.

This document and its five companion documents are proposals. None describes implemented Phase 8 behavior or permits implementation, collection, deployment, or a change to the research verdict.

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
| FR-013 | Any official-results collector shall remain disabled until source access, reuse rights, operating limits, and a review owner are documented and approved. | Must | `TEST-020` |

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

## Official results exploration requirements

The UI may provide a source-aware explorer only after a result source and reuse mode have been approved. A PCSO-hosted results page is a candidate official source, but the machine-access method and reuse terms were not verified in this review. LottoMatik's current Terms of Use prohibit automated crawler/scraper access without express written permission and restrict copying, republication, or derivative works without express permission. Therefore, do not activate automated collection or publish copied result records from that source without written permission and review. Missing winner counts or other source fields must be stored as `null`, never inferred or fabricated.

The initial client can ship without a results explorer if no reviewed result artifact exists. It may explain the source-status gate and link to the publisher, but it must not imply that a linked source has approved project reuse.

## Privacy and consent boundaries

- Browser-local generation only; no submission endpoint, analytics payload containing generated lines, or visitor registry in v1.
- Download is initiated by the visitor and remains their local file.
- Public registration is for frozen project-generated research batches, not visitor submissions.
- Do not create consent records for data that is not collected. Any later visitor submission, account, feedback capture, or cross-device persistence requires a separate privacy design and approval.
- Static hosts can log request metadata. [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) specifically says visitor IP addresses are logged and stored for security. Hosting choice, retention, jurisdiction, notice, and operational access require provider-specific deployment review.
- Source collection and source reuse are independent approvals from randomizer development.

## In-scope and out-of-scope features

**In scope for the proposal:** mathematical and artifact contracts; local G0 product behavior; gated G1/G2 capabilities; source-status presentation; read-only static registration; future testing, accessibility, privacy, and research gates.

**Out of scope for v1:** ticket sales, payments, account profiles, gambling transactions, visitor-combination uploads, public comments, central analytics of generated lines, a database, an API backend, an enabled collector, forecasting claims, automated wager advice, and access to the existing validation or locked-test partitions.

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
| Official source access/reuse | `BLOCKED_PENDING_AUTHORIZATION` | Obtain and review authoritative access and reuse terms; confirm machine-access method |
| Hosting provider | Unresolved; evaluate GitHub Pages and Cloudflare Pages | Privacy, build, URL, deployment control, and operational review |
| G2 parameters | Uncalibrated and unapproved | Fit on approved training folds; independent review and freeze |
| Prospective sample size | Unset | Complete a power/sensitivity analysis for a predeclared primary endpoint |
| Timestamp authority | Not selected | Approve an independent RFC 3161 TSA and token retention/verification procedure |
| Research verdict | Existing STOP verdict preserved | Revisit only through separately governed, independently reviewed evidence |

## Source basis and limits

Repository facts were checked at baseline `b67e31572187001c89266839871c9e28456b90e8`: [README](../../../README.md), [Phase 7 report](../../PHASE7_KMEANS_DESCRIPTIVE.md), [Phase 5R report](../../../reports/phase5r_predictive_information.md), [Phase 6B adjudication](../../../reports/phase6b_642_semantic_adjudication.json), and [repository structure](../../REPOSITORY_STRUCTURE.md). The Phase 7 report states that it uses only the established 902-row training partition and that `source_row` is provenance metadata, not a chronological key.

External sources checked 2026-10-17: [PCSO official results search result](https://www.pcso.gov.ph/?content=hasil), [LottoMatik results page](https://lottomatik.pcso.gov.ph/lotto-results), [LottoMatik Terms and Conditions](https://lottomatik.pcso.gov.ph/terms), [RFC 3161](https://www.rfc-editor.org/info/rfc3161/), [GitHub Pages overview](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [Cloudflare Pages Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/), and [GitHub Actions scheduled-workflow limits](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows). The direct PCSO results page could not be opened in the browser source review; the result page's existence is treated as a candidate lead, not evidence of an API or reuse permission. The AGY proposal remains unavailable.
