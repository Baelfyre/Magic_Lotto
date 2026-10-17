# Implementation Plan
<!-- @codebase_provenance_JEO -->

- **Status:** Proposed roadmap; no implementation authorized by this document
- **Baseline:** `origin/main` at `998f16d133b4500dfd65fa57fb73f9d84c91f8f4` (merged PR #4)
- **Prepared:** 2026-10-17
- **Research verdict:** `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`

## Delivery objectives and constraints

Deliver a small, reproducible G0-first randomizer and research artifact pipeline with a static client, explicit provenance, and separately gated prospective evaluation. The Python research engine and versioned JSON/JSONL artifacts are the proposed foundation. No item in this plan authorizes implementation, dataset changes, source collection, deployment, or changes to the current STOP verdict.

PR #4 completed the initial repository migration and Phase 7 package foundation in `src/magic_lotto/`. Phase 8 must extend that package's existing domain, research, application, infrastructure, and interface layers; do not schedule another package-architecture refactor or recreate its training repository, output writer, notebook bootstrap, or path policy. PR #4 did not implement Phase 8 generators, a web client, a general artifact store, a source adapter, or an evaluation workflow.

**Research scope:** Philippine Lotto 6/42 only. 3D Lotto, all other lottery games, and unrelated prediction systems are excluded. Phase 8 remains an educational and experimental project, not an affiliated PCSO product or a predictive service.

Hard constraints throughout delivery:

- Use only explicitly approved training inputs; preserve the documented 902-row training boundary and the 2016-08-30 through 2022-11-12 interval.
- Do not open or score validation or locked-test records; automated checks should reject those paths.
- Do not modify or reorder original or cleaned datasets.
- Keep G0 uniform and default; G1/G2 are experimental, and G2 needs calibration and release review.
- Use synthetic fixtures for source or schema tests unless and until a source is approved.
- Distinguish fair-draw probability, validated model-selection probability, and historical pattern frequency; unavailable values remain “Not calculated” or “Not established.”
- Keep visitor generation browser-local; no central visitor-combination collection.
- Keep all result collection disabled until source identity, ordinary access conditions, current terms/robots findings, applicable reuse conditions, operating limits, and a human-reviewed feasibility report are approved. Written permission is required only when law, terms, or source-specific restrictions require it.
- Do not depend on an FOI workflow for ordinary collection; keep LottoMatik excluded from automation pending current terms review.
- Do not make predictive, accuracy, significance, acceptance-rate, or entropy claims without actual reviewed evidence.
- Do not deploy or merge as part of a milestone without separate approval.

## Architecture prerequisites

Before coding, human reviewers should approve the product scope and the Phase 8 extension map against the merged `src/magic_lotto/` architecture; confirm local repository and partition access controls; approve dependency/browser support policy; and resolve whether React/TypeScript is necessary for the client and where its source will live. Reuse `magic_lotto.domain.draw_642` for combination invariants and place approved generator mathematics in the existing `magic_lotto.research` layer. Add application ports and infrastructure persistence only for an approved consumer. The first implementation work must not depend on an unverified official API or assumed reuse right. G0 can proceed independently of source collection. G1/G2, a public result explorer, prospective registry, collector, and evaluation have their own gates.

The AGY proposal is `[NEEDS SOURCE]`; this plan cannot claim that document was reviewed. The earlier reconciled Codex proposal was present in conversation history but not as a standalone repository file. Reconciliation remains based on the shared decisions in the current request and verified repository evidence until the missing proposal is supplied.

## Milestone 8A: Python mathematical core

**Scope:** Reuse `magic_lotto.domain.draw_642` combination validation; add approved G0 generation, versioned contracts, and exact combinatorial utilities in the existing `src/magic_lotto/research/` layer; preserve established training boundaries. G1's fixed-cardinality math may be implemented only after its training inputs/configuration are separately approved. No G2 release in this milestone.

**Tasks:** Define canonical sorted-line type and schema version; implement invalid-input rejection; define injected random source for tests and cryptographic runtime source; implement G0 sample and exact match PMF; implement G1 normalization/sampling if authorized; add assertions for `C(42,6)`, exact numerator sum, expected match count, and the Jaccard formula; create tests that forbid protected-data paths.

**Acceptance:** TEST-001 through TEST-005, TEST-008, and TEST-009 pass on the reviewed code revision; exact formulas and boundaries are independently reviewed; 902 training-row count and date endpoints are verified from the approved training source without accessing protected partitions; source files remain unchanged.

**Definition of done:** Reviewed API/schema, passing focused unit tests, recorded runtime/dependency versions, no accidental source-data diff, and a separate human review gate before any model fitting.

## Milestone 8B: Statistical fidelity and reproducibility

**Scope:** Fit/version G1 as a control and develop G2 only on approved training data using chronological development folds. Calibrate regularization and feature set, compute exact normalizers, validate sampler fidelity, quantify numerical and compute behavior, and prepare training-only reports. Existing validation and locked-test partitions remain sealed.

**Tasks:** Predefine candidate features and development comparisons; approve the concentration diagnostic and threshold before the feature/parameter search; use chronological folds inside approved training data; document every feature/parameter search and multiplicity adjustment; compare fitted distributions with fair null using exact/simulation checks with seeded fixtures; validate G2's unary/adjacent-transition DP against exhaustive toy universes; compare Python and browser contracts; record fit stability and compute measurements; submit G1/G2 artifacts for independent review.

**Acceptance:** TEST-005 through TEST-009 and TEST-013 pass; G1/G2 meet the predeclared concentration guardrail, and G2 has normalized probabilities, positive support over all valid combinations, matching sampler implementation, a reviewed training cutoff/hash, and a published measurement report. If any condition fails, the affected experimental mode remains unavailable and G0 remains usable. No result from these checks reverses the STOP verdict.

**Definition of done:** Immutable G1/G2 `ModelSpec` candidates, reproducibility notes, completed training-only validation, and independent model review. A G2 candidate is not user-facing until the release reviewer records approval.

## Milestone 8C: Static web application

**Scope:** Build the responsive, accessible, static client for browser-local G0 generation, copy/download, research explanations, and only approved model/summary artifacts. The client source location and frontend stack must be approved before this work; no frontend directory exists in the current repository. Add G1/G2 controls only after 8B gates. No visitor write endpoint, database, collector, or deployment in this milestone.

**Tasks:** Confirm framework and browser matrix; implement the information architecture and mode labels; use Web Crypto bounded-integer rejection sampling for G0; load and validate read-only artifacts; provide accessible text/table alternatives for charts; add privacy/source/research notices; test network requests to confirm generated lines stay in-browser; document static hosting candidates without selecting one.

**Acceptance:** TEST-001 through TEST-008 and TEST-012, TEST-014, TEST-016, TEST-021, TEST-022 pass. Proposed performance target is 100 G0 lines within 1 second at the 95th percentile on a human-agreed reference mobile browser. Record actual device/browser and results. No deployment until separate hosting/privacy review.

**Definition of done:** UI review, supported-browser behavior, keyboard/screen-reader/contrast/zoom evidence, local-download validation, no visitor-data network flow, and reviewed artifact integrity. Hosting/deployment remains a separate approval checkpoint.

## Milestone 8D: Source feasibility and conditional collection

**Scope:** 8D is separate from randomizer development. All adapters remain disabled throughout this proposal stage, and source-policy review does not itself activate collection. PCSO is the primary source candidate; LottoPCSO.com is secondary and requires cross-checking; LottoMatik is excluded from automation pending current terms review. FOI is not an operational dependency.

**8D.1 Offline parser feasibility:** Specify the DrawSourceAdapter methods, versioned normalization, schema/provenance, error states, deduplication, correction, quarantine, and source-status reporting. If approved for implementation, keep source adapters in a new `src/magic_lotto/infrastructure/sources/` extension; this package is intentionally absent today. Build only from synthetic offline HTML fixtures representing the observed source layouts and edge cases. Evaluate existing/standard-library options before approving dependencies. Disabled adapters and health checks make no network requests.

**Acceptance:** TEST-008, TEST-015, TEST-023, and TEST-024 pass on synthetic fixtures. Tests cover date formats, published versus sorted order, missing optional fields, duplicate and incomplete records, unexpected headers, placeholders, malformed markup, pagination/date boundaries, layout changes, access denial, timeout/server failure, conflicting sources, and corrections. No live request or copied protected result row is used.

**8D.2 Source-policy and feasibility review:** Recheck the PCSO result page's ordinary form/request behavior, source terms and robots rules, historical coverage, update behavior, and applicable reuse scope. Repeat the same source-specific review for LottoPCSO.com before any secondary adapter. Record unresolved questions and a human-reviewed recommendation. Treat public access or absence of an explicit ban as insufficient proof of reuse permission. Written permission is a condition only where applicable law, terms, or source-specific restrictions require it.

**Acceptance:** TEST-020 has a current, source-specific record for identity, ordinary access method, terms/robots review, applicable reuse conditions, request pacing, reviewer, and expiry. If a source is denied or uncertain, its adapter stays disabled. Source review does not require or await an FOI response.

**8D.3 Conditional live pilot:** Only after separate human approval, pilot one eligible source with a low-frequency request after draw-result publication, bounded retries, configurable pacing, monitored failures, and idempotent writes. Verify the current PCSO draw timetable before configuring any schedule. Do not use a scheduled workflow as exact-time evidence. Stop on access denial, clear prohibition, or changed/unresolved terms. Do not use CAPTCHA solving, stealth browsers, proxy rotation, or WAF/authentication circumvention.

**Acceptance:** TEST-010, TEST-015, and TEST-020 pass; a disabled adapter makes zero requests; an enabled pilot follows the approved source limits; unknown values remain null; conflicts and corrections create quarantined or superseding records; only Lotto 6/42 observations reach the proposed `data/prospective/lotto-6-42/` store; original datasets and sealed partitions remain untouched.

**Definition of done:** Offline parser contract is reviewed; source feasibility and current policy status are documented; any live pilot is separately approved and bounded; source record revisions and recovery procedure are retained. No source approval or human activation means no collection.

## Milestone 8E: Prospective research registry

**Scope:** Create a read-only static view for project-generated batches only. Proposed storage locations are `models/phase8/` for model artifacts and `reports/phase8/` for reviewed public research artifacts and frozen registry manifests; these directories are not present today. Freeze study manifests and results before target draws, obtain an external RFC 3161 token, verify it, and publish the verified record under an approved hosting process. This is not a public visitor registration form.

**Tasks:** Select an independent TSA and verification procedure; define canonical manifest serialization; generate equal-size G0 and experimental comparison batches under a frozen protocol; hash all artifacts; timestamp manifest before target draw; retain token/cert verification; commit the manifest/token/event references; implement a read-only static page; disclose timestamp time separately from site deployment time.

**Acceptance:** TEST-008, TEST-011, TEST-017, and TEST-018 pass; timestamp token imprint matches canonical bytes and precedes the target draw; batches are immutable and source-independent until outcome; static registry has no write route; a timestamp failure means no registration claim.

**Definition of done:** Reviewer-approved protocol, verified timestamp package, exact static registry content, public privacy/retention notice, and separate deployment approval.

## Milestone 8F: Pilot and evaluation

**Scope:** First run an operational pilot to exercise freezing, timestamp verification, artifact publication, source review, and append-only evaluation. A 50-draw pilot is not automatically confirmatory and must not be used as evidence of prediction. Confirmatory evaluation requires a separate predeclared design and power/sensitivity analysis.

**Statistical design gate:** Select one primary endpoint before registration. A proposed endpoint is paired per-draw full-combination log-score difference between an experimental model and G0 on the same target draws. For a draw `S_t`, `d_t = log p_model(S_t) - log(1/5,245,786)`. Under the fair independent-draw null, uniform G0 is the true distribution and is optimal in expected log score; any observed positive finite-sample difference is uncertain and does not alone establish an advantage. Define the smallest scientifically meaningful alternative `delta`, the paired standard deviation `sigma_d`, Type I error `alpha`, power `1-beta`, any multiplicity adjustment, missing-outcome handling, and stopping rule before sampling target outcomes.

For a two-sided normal-approximation sensitivity calculation, `n ≈ ((z_(1-alpha*/2) + z_(1-beta)) * sigma_d / delta)^2`. At unadjusted `alpha=0.05`, `80%` power, and independent paired draw differences, `n=50` corresponds roughly to a standardized effect `delta/sigma_d ≈ 0.40`. This is illustrative only. Dependence, multiplicity, non-normality, model selection, and uncertain variance can require more observations. A pilot can establish operational reliability; if it estimates outcome variance or informs the confirmatory effect size, freeze and disclose that design choice before the confirmatory series and account for the pilot in the analysis plan.

**Acceptance:** TEST-011, TEST-018, and TEST-019 pass; verify only authorized outcomes after the registered draw; analysis follows the frozen manifest; all endpoints, missing outcomes, uncertainty, and corrections are reported; no selective ticket or model chosen after observing outcomes; no claim unless independently reviewed and permitted by a new evidence decision.

**Definition of done:** Pilot process report and separately approved confirmatory protocol, if pursued. This milestone does not reopen the existing locked test partition or automatically change the STOP verdict.

## Work breakdown and implementation order

1. Approve the Phase 8 extension map for the merged package, identifiers, mathematical definitions, data boundaries, privacy boundary, and test plan. Do not repeat PR #4's completed package-structure work.
2. Complete 8A mathematical contracts and G0 reference; review before fitting.
3. Complete 8B statistical and model gates; leave G2 unavailable if it fails.
4. Complete 8C static client and accessibility/privacy review.
5. Review 8D source feasibility and applicable access/reuse conditions independently; it is not a prerequisite to G0.
6. Approve timestamp provider, canonicalization, registration protocol, and read-only hosting for 8E.
7. Approve the power/sensitivity analysis and prospective outcomes source before 8F.
8. At every gate, review exact diff, tests, data-access audit, and evidence against the current branch/commit. Deployment, merge, and publication each require separate authorization.

## Task-level acceptance and test plan

| Test ID | Planned test family | Milestone(s) | Core check |
| --- | --- | --- | --- |
| TEST-001 | Ball/combination invariants | 8A, 8C | Six unique integers, 1-42, canonical ordering |
| TEST-002 | Input validation | 8A, 8C | Invalid types, bounds, duplicates, and batch sizes rejected |
| TEST-003 | G0 distribution | 8A, 8C | Exact toy spaces, bounded-integer edge cases, predeclared statistical checks |
| TEST-004 | Batch sampling design | 8A, 8C | Replacement versus distinct-set behavior and labels |
| TEST-005 | G1 normalization/sampling | 8A, 8B | Fixed-cardinality normalizer and sampler against exhaustive toy spaces; predeclared concentration diagnostic passes |
| TEST-006 | G2 normalization | 8B | DP partition function agrees with exhaustive toy universe and sums to one |
| TEST-007 | G2 sampler parity | 8B, 8C | Target law and Python/browser parity on toy/reference fixtures |
| TEST-008 | Schema and artifacts | 8A-8E | Versioning, nullability, stable IDs, hash integrity and lifecycle |
| TEST-009 | Partition access boundary | 8A, 8B | Protected validation/test paths are not opened by tests/build tasks |
| TEST-010 | Collector disabled state | 8D | No network requests absent activation and current approval |
| TEST-011 | Timestamp and manifest | 8E, 8F | Canonical hash, token verification, time precedes target draw |
| TEST-012 | Provenance presentation | 8B, 8C | Model/version/cutoff/status visible |
| TEST-013 | G2 release review | 8B | Calibration, exact normalization, sampler fidelity, concentration-guardrail, and compute-cost approval |
| TEST-014 | Scientific display | 8C | Fair-draw probability, model-selection probability, and historical frequency are separately labelled; exact values and limitations are correct |
| TEST-015 | Result provenance | 8C, 8D | Only reuse-approved verified records, source classes, cross-checks, correction states and nulls are displayed |
| TEST-016 | Visitor privacy | 8C | No generated line in network requests or central persistence |
| TEST-017 | Static registry | 8E | Read-only published view; only frozen pre-draw project batches |
| TEST-018 | Evaluation isolation | 8E, 8F | Authorized outcomes only, after freeze/draw, append-only protocol |
| TEST-019 | Statistical plan | 8F | Primary endpoint, power, multiplicity, uncertainty, stopping rule frozen |
| TEST-020 | Source eligibility and policy review | 8D.2, 8D.3 | Current terms/robots, ordinary access method, applicable reuse conditions, pacing, reviewer, and expiry precede activation; written permission only where applicable |
| TEST-021 | Accessibility/compatibility | 8C | WCAG 2.2 AA target and browser support matrix manually reviewed |
| TEST-022 | G0 performance | 8C | 100-line batch meets proposed 1-second p95 target on agreed device/browser; actual environment recorded |
| TEST-023 | Lotto 6/42-only scope | 8A, 8C, 8D | Inputs, artifacts, filters, and parsers reject or ignore all other games |
| TEST-024 | Offline source parser contract | 8D.1 | Synthetic fixtures validate parsing, normalization, nulls, duplicates, conflict/correction handling, and disabled-source zero-network behavior |

The tests above are future acceptance criteria. They have not been run by this proposal. Source rights, real browser behavior, screen-reader behavior, and actual Colab/hosted behavior require their own evidence class.

## Training partition and leakage safeguards

1. Maintain a reviewed allowlist for the 902-row approved training source and its exact hash.
2. Validate row count, date endpoints, unique source identifiers, valid draw shape, and chronological order by draw date.
3. Treat `source_row` as provenance metadata only; uniqueness is an integrity condition, not an ordering requirement.
4. Use chronological folds only within the approved training boundary for development.
5. Prohibit paths and data loaders for the existing validation and locked-test partitions in Phase 8 tasks.
6. Use synthetic fixtures for parser, schema, and sampler tests; avoid copied protected rows.
7. Keep future prospective outcomes in a separate directory/namespace and only read them after the timestamped target draw.
8. Make any training-data expansion a separately reviewed decision; do not silently incorporate prospective outcomes into a frozen evaluation.

## Integration, end-to-end, accessibility, and security validation

Integration tests should trace `ModelSpec` to generated output to frozen manifest to RFC 3161 token to static rendering, and then append a synthetic `EvaluationEvent` without any live source. End-to-end tests should inspect network requests and demonstrate that visitor combinations are not transmitted. Tests should verify local download and accessible errors. Security review should verify static artifact integrity, no secrets, no write endpoint, no unexpected third-party scripts, and disabled collector behavior. Accessibility review should combine automated scans with keyboard, screen-reader, responsive, contrast, zoom, and reduced-motion checks. Do not treat a local static pass as hosted deployment proof.

## Effort estimates and assumptions

| Milestone | Estimate | Assumptions |
| --- | --- | --- |
| 8A | 4-6 person-days | One Python engineer familiar with current repository, focused G0/contracts work, no source-data repair |
| 8B | 5-8 person-days | Approved data access and independent statistical reviewer available; G2 may remain blocked |
| 8C | 8-13 person-days | One frontend engineer; approved stack, design review, no backend or deployment operations |
| 8D | 5-10 person-days after feasibility review | One source first; source-specific access/reuse conditions resolved, written permission only if required; source-owner delays excluded |
| 8E | 4-7 person-days | TSA and verification process selected; no public submission API |
| 8F | 4-8 person-days plus prospective draw period | Frozen protocol and source are ready; calendar wait for draws excluded |

Total engineering effort is a rough 30-52 person-days before external approval delays, rework, or follow-up draw time. These are planning estimates, not delivery commitments; they assume no broad frontend redesign, no database, and an available reviewer. Re-estimate after stack, source, and study-design decisions.

## Risk register and mitigations

| Risk | Impact | Mitigation / gate |
| --- | --- | --- |
| Users interpret experimental distribution as better odds | Misleading product claim | G0 default, persistent notices, experimental labels, independent copy review |
| Model overfit through feature exploration | False discovery | Chronological training-only folds, frozen feature search, multiplicity correction, no holdout access |
| G2 exact sampler too slow or implementation diverges | Incorrect or unusable output | Decomposable feature contract, exact toy-space tests, cross-runtime parity; hide G2 if gate fails |
| Source access/reuse unresolved or changes | Operational or rights exposure | Disabled adapter, current source-specific terms/robots/reuse review, written permission only where required, stop on denial/change, no circumvention |
| HTML layout or pagination changes | Missed, duplicated, or malformed result records | Versioned parser rules, synthetic fixtures, schema validation, quarantine, and manual source-status review |
| Static registration lacks write endpoint | Missing or late registration | Maintainer-controlled manifest process, pre-draw independent timestamp, static read-only display |
| GitHub scheduled workflow delay/disablement | Missed collection or timing | Do not use a scheduled job as timestamp evidence; monitoring/recovery and host review if later needed |
| Timestamp proof misunderstood | False pre-draw claim | Verify token imprint, signature, policy and UTC time; distinguish timestamp from deployment and truth |
| Visitor values leak through analytics/logs | Privacy failure | No analytics SDK or submission route; inspect network; review host logs and privacy notice |
| Sample size too small | Inconclusive evaluation | Pre-register endpoint and sensitivity/power analysis; 50-draw pilot is operational only |
| AGY proposal unavailable | Reconciliation incomplete | Mark source gap; request canonical document before claiming it was reviewed |

## Documentation and change-control process

Keep the six Phase 8 proposal documents cross-linked and versioned with implementation artifacts only after separate approval. Changes to definitions, schemas, model features, endpoints, data access, source permissions, or privacy behavior require a new review and updated traceability. Update the `StudyManifest` schema only through a new version. Preserve prior research verdicts and evidence; propose a separate decision record if future evidence warrants a verdict review.

For each milestone, record baseline commit, exact implementation commit, working-tree scope, commands, runtime versions, test outcomes, skipped checks, and limitations. Evidence becomes stale after source/model/config changes. Human review precedes deployment or public artifact release.

## Required human approval checkpoints

1. **Architecture/scope:** confirm Python engine, artifact storage, static local client, framework, identifiers, and no-backend v1.
2. **Data boundary:** approve exact training source/hash and test protections before model work.
3. **Model release:** independent approval for G1/G2 calibration, normalization, sampler fidelity, and claims.
4. **Privacy/accessibility:** approve host, provider data flows, privacy notice, and accessibility evidence before deployment.
5. **Source feasibility and policy:** approve source-specific identity, terms/robots findings, ordinary access method, applicable reuse conditions, request controls, and expiry separately from generator development. Written permission is required only where applicable; FOI is not a prerequisite. Keep LottoMatik excluded unless current restrictions are resolved.
6. **Registration:** approve TSA, canonicalization, preregistration process, public static artifacts, and retention before any study batch is registered.
7. **Confirmatory evaluation:** approve endpoint, minimum meaningful effect, power/sensitivity, multiplicity, stopping rule, outcome access, and independent reviewer before prospective outcomes.
8. **Publication/deployment/merge:** each is a separate authorization; completion of a milestone does not authorize any of them.

## Requirements traceability matrix

Components: C1 uses the existing `domain.draw_642` and `research.kmeans_642` foundation with proposed Phase 8 generators under `src/magic_lotto/research/`; C2 uses the Phase 7-specific repository/writer only as architectural examples, with a proposed Phase 8 artifact store; C3 static client, C4 registry view, C5 prospective evaluation, C6 source adapter, and C7 timestamp service are proposed and not implemented. The current Phase 7 ports and IO modules must not be described as generic Phase 8 services. Tests are defined in [02 Technical Requirements](02_TECHNICAL_REQUIREMENTS.md); milestones are defined above.

| Requirement | Component(s) | Test | Milestone |
| --- | --- | --- | --- |
| FR-001, FR-002 | C3 | TEST-001, TEST-003 | 8A, 8C |
| FR-003 | C1, C2, C3 | TEST-005, TEST-012 | 8A, 8B, 8C |
| FR-004 | C1, C2, C3 | TEST-006, TEST-007, TEST-013 | 8B, 8C |
| FR-005, FR-006 | C1, C3 | TEST-002, TEST-004 | 8A, 8C |
| FR-007 | C3, C5 | TEST-014, TEST-019 | 8C, 8F |
| FR-008 | C2, C3, C6 | TEST-008, TEST-015 | 8C, 8D |
| FR-009 | C2, C3 | TEST-008, TEST-012 | 8B, 8C |
| FR-010 | C3 | TEST-016 | 8C |
| FR-011 | C2, C4, C7 | TEST-011, TEST-017 | 8E |
| FR-012 | C5, C7 | TEST-018, TEST-019 | 8F |
| FR-013 | C6 | TEST-010, TEST-020 | 8D |
| FR-014 | C1, C2, C3, C6 | TEST-023 | 8A, 8C, 8D |
| FR-015, FR-016 | C3, C5 | TEST-014 | 8C |
| FR-017 | C2, C3, C6 | TEST-015, TEST-020, TEST-024 | 8D |
| NFR-001, DATA-014 | C3 | TEST-016 | 8C |
| NFR-002, TR-009 | C3 | TEST-021 | 8C |
| NFR-003 | C1, C3, C5 | TEST-014, TEST-019 | 8B, 8C, 8F |
| NFR-004, DATA-013 | C1, C2, C7 | TEST-008, TEST-011 | 8A, 8E |
| NFR-005 | C3 | TEST-021 | 8C |
| NFR-006, TR-010 | C3 | TEST-022 | 8C |
| NFR-007 | C2, C3 | TEST-008, TEST-011 | 8A, 8E |
| NFR-008 | C1, C2, C3 | TEST-008, TEST-009 | 8A-8C |
| TR-001 | C1, C2 | TEST-008, TEST-012 | 8A, 8B |
| TR-002 | C1, C3 | TEST-003, TEST-005 | 8A, 8B, 8C |
| TR-003 | C1, C3 | TEST-006, TEST-007, TEST-013 | 8B, 8C |
| TR-004 | C1, C5 | TEST-009, TEST-018 | 8A, 8F |
| TR-005 | C2 | TEST-008 | 8A, 8B, 8E |
| TR-006, TR-012 | C6 | TEST-010, TEST-020 | 8D |
| TR-013 | C2, C6 | TEST-008, TEST-015, TEST-020, TEST-024 | 8D |
| TR-014 | C1, C3 | TEST-014 | 8A, 8C |
| TR-007 | C2, C4, C7 | TEST-011, TEST-017 | 8E |
| TR-008 | C3 | TEST-016 | 8C |
| TR-009 | C3 | TEST-021 | 8C |
| TR-011 | C2, C3, C4 | TEST-017 | 8C, 8E |
| DATA-001, DATA-002 | C1, C2 | TEST-008 | 8A, 8B |
| DATA-003 | C1, C6 | TEST-001, TEST-015 | 8A, 8D |
| DATA-004 | C6 | TEST-010, TEST-020 | 8D |
| DATA-005 | C1, C2 | TEST-008, TEST-012, TEST-013 | 8B |
| DATA-006 | C2, C7 | TEST-011 | 8E |
| DATA-007 | C1, C2 | TEST-008, TEST-017 | 8E |
| DATA-008 | C5 | TEST-018, TEST-019 | 8F |
| DATA-009 | C3, C6 | TEST-015 | 8C, 8D |
| DATA-010 | C2, C6 | TEST-008, TEST-015 | 8D |
| DATA-011 | C1, C5 | TEST-009, TEST-018 | 8A, 8F |
| DATA-012 | C2, C6 | TEST-008, TEST-015 | 8D |
| DATA-013 | C2, C7 | TEST-011 | 8E |
| DATA-014 | C3 | TEST-016 | 8C |
| DATA-015 | C1, C2, C5, C6 | TEST-009, TEST-018, TEST-023 | 8A, 8D, 8F |
| DATA-016, DATA-017 | C2, C6 | TEST-008, TEST-015, TEST-020, TEST-024 | 8D |
| DATA-018 | C1, C2, C3 | TEST-008, TEST-014 | 8A, 8C |

The exact data-field contract is in [05 Backend and Data Schema](05_BACKEND_AND_DATA_SCHEMA.md). All requirements and acceptance tests are proposed; none is evidence of implementation or research success.

## Definition of done for the proposal

The six proposal files are cross-consistent, formulas and schema examples have been reviewed, local links and Markdown have been checked, missing sources and unresolved approvals are visible, and the changes are limited to the six requested documents. This documentation delivery does not implement the roadmap, access protected partitions, activate collection, deploy, or alter the research verdict.
