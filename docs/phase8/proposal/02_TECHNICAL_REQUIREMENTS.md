# Technical Requirements Document
<!-- @codebase_provenance_JEO -->

- **Status:** Proposed target architecture; not implemented
- **Baseline:** `origin/main` at `b67e31572187001c89266839871c9e28456b90e8`
- **Last reviewed:** 2026-10-17
- **Research verdict:** `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`

## Proposed system architecture

Phase 8 should retain a Python-first research engine and add a static web client only after separate implementation approval. Python produces versioned model, research-summary, and registration artifacts. A static client reads reviewed artifacts and runs G0 locally with the browser's Web Crypto API. V1 has no backend or application database, and it sends no generated lines to project storage.

The baseline is a research repository, not a deployed application. Existing Python and data-validation conventions remain the starting point. Proposed frontend technology is not a repository fact. Hosting is unresolved. The read-only registry is a static view over committed manifests; it does not accept public POST requests. A future database or API requires an evidenced concurrency, retention, or operational need and a separate architecture decision.

## Stable technical requirements

| ID | Technical requirement | Planned evidence |
| --- | --- | --- |
| TR-001 | Python shall own research fitting, reference probabilities, schema validation, and release-artifact creation; the client shall consume versioned artifacts. | TEST-008, TEST-012 |
| TR-002 | G0 and G1 shall use exact fixed-cardinality probability definitions and unbiased sampling methods; G1 must pass its predeclared concentration guardrail before release. | TEST-003, TEST-005 |
| TR-003 | G2 shall use finite positive-support parameters, exact normalization, an exact sampler, and a predeclared concentration guardrail, or remain unavailable. | TEST-006, TEST-007, TEST-013 |
| TR-004 | Training, validation, locked-test, and prospective outcome paths shall be isolated; Phase 8 may access only approved training inputs and authorized post-registration outcomes. | TEST-009, TEST-018 |
| TR-005 | Versioned JSON/JSONL artifacts shall use stable IDs, schema versions, canonical hashes, and append-only corrections/evaluations. | TEST-008, TEST-011 |
| TR-006 | External result ingestion shall require independent source identity, access, and reuse review; adapters remain disabled until approved. | TEST-010, TEST-020 |
| TR-007 | Public research registration shall freeze a complete manifest and verify an independent RFC 3161 timestamp before the target draw; the hosted registry is read-only. | TEST-011, TEST-017 |
| TR-008 | Visitor combinations shall remain browser-local, with no visitor write endpoint or central visitor-data persistence in v1. | TEST-016 |
| TR-009 | The client shall target WCAG 2.2 AA and include manual accessibility evidence. | TEST-021 |
| TR-010 | The initial client shall meet the proposed, device-specific performance target only after measurement on an agreed reference browser/device. | TEST-022 |
| TR-011 | Hosting shall serve static files/artifacts; host selection, provider privacy, deployment triggers, and public release require a separate review. | TEST-017, deployment review |
| TR-012 | A collector implementation shall make no network request by default and shall fail closed without a current source-specific access/reuse review record. | TEST-010, TEST-020 |
| TR-013 | A future Python result collector shall use source-specific adapters, ordinary retrieval and parsing rules, provenance-preserving normalization, conflict quarantine, and offline synthetic parser fixtures before any separately approved live pilot. | TEST-008, TEST-015, TEST-020, TEST-024 |
| TR-014 | Probability APIs and displays shall distinguish fair-draw probability, validated model-selection probability, and observed historical pattern frequency; unavailable measures shall remain explicitly unavailable. | TEST-014 |

## Technology stack and alternatives

| Option | Strengths | Costs and limits | Proposal disposition |
| --- | --- | --- | --- |
| Python engine + Vite/React/TypeScript static client | Preserves Python research workflow; static delivery; client-local generation; explicit artifact boundary | Two-language sampler parity; build toolchain; no server-side writes | Preferred proposal; framework choice still requires approval |
| Streamlit application | Python-only prototype and direct charting | Server runtime and session/state behavior; weaker fit for no-backend, visitor-local static delivery | Do not select for v1; reconsider only if the product becomes an internal research tool |
| FastAPI + frontend | Supports controlled write APIs and dynamic operations | Adds service operations, auth, abuse controls, persistent storage, and privacy responsibilities | Defer until a concrete backend requirement is approved |
| Static HTML/JavaScript without React | Fewer dependencies and simpler build | May be harder to sustain as interactions and accessibility states grow | Viable minimum alternative if the approved UI remains small |

Use Python already established by the research repository for fitting and validation. Vite, React, TypeScript, and specific package versions are proposed, not selected dependencies. The first implementation plan must record compatibility versions, lockfiles, support policy, and reproducible build evidence. Do not add dependencies during this documentation task.

## Python package and module boundaries

Proposed package boundaries, not current modules:

| Component | Responsibility | Must not own |
| --- | --- | --- |
| `phase8.contracts` | Versioned schemas, enums, validation, canonical serialization | Source collection or UI state |
| `phase8.generators` | G0/G1/G2 target distributions and sampling interfaces | Reading sealed partitions |
| `phase8.fit` | Training-only feature extraction, fitting, chronological development folds | Public hosting or future-outcome selection |
| `phase8.artifacts` | Hashing, model manifests, generated batches, append-only evaluation events | Visitor profiles |
| `phase8.sources` | Disabled adapter interfaces and source review records | Network access until approved |
| `phase8.evaluation` | Frozen-protocol metrics over authorized post-registration outcomes | Model tuning after observing registered outcomes |
| Static client | Accessible local generation, display, download, and read-only artifact viewing | Persistent visitor storage or mutation of research artifacts |

The Python research core is authoritative for model fitting and artifact validation. Browser implementations must implement the same mathematical contracts; they must not independently redefine a model.

## Generator interfaces and contracts

Proposed interface shape:

```text
GeneratorSpec:
  algorithm_id: G0 | G1 | G2
  model_version: string
  config_hash: sha256
  status: baseline | experimental_control | pending_calibration | approved_for_experimental_use | retired

generate(batch_size, mode, random_source) -> transient GenerationResult
probability_of(sorted_combination, model_spec) -> probability
validate_combination(values) -> ValidationResult
freeze_research_batch(result, study_manifest) -> GeneratedBatch
```

Every public or research generation call validates a positive bounded batch size and exactly six distinct integers from 1 through 42. A combination is an unordered set; canonical serialized lines sort values ascending. `mode=independent_with_replacement` is the default batch mode. `mode=distinct_sets` is a separate product option and has a different joint distribution.

### Common mathematical contract

The valid universe size is `C(42,6) = 5,245,786`; G0 assigns each valid unordered combination probability `1/C(42,6)`. For one fixed line against an independent fair draw:

```text
P(K=k) = C(6,k) C(36,6-k) / C(42,6), k=0..6
numerators = [1947792, 2261952, 883575, 142800, 9450, 216, 1]
E[K] = 6 * 6/42 = 6/7
```

The numerator sum equals the denominator. For `M` distinct lines where `0 <= M <= C(42,6)`, jackpot probability is `M/C(42,6)`. For `M` independent lines with replacement, it is `1-(1-1/C(42,6))^M`. These are analytic fair-baseline values; empirical outcome performance must be evaluated separately.

For two valid six-number sets whose intersection has `r` elements, `Jaccard distance = d_J = 1 - r/(12-r) = (12-2r)/(12-r)`, where `r` is an integer in `[0,6]`. If an explicitly selected rule requires `d_J >= d_min`, then `r <= floor(12(1-d_min)/(2-d_min))`; verify equality against the discrete distance table because strict thresholds have different edge behavior. The distances for `r=0..6` are `1, 10/11, 4/5, 2/3, 1/2, 2/7, 0`. A thresholded distance filter changes the probability law and must not be applied to G0. If an explicitly user-selected diversity feature is ever added, show its threshold and altered sampling design; it is outside this proposal's MVP.

Probability outputs have separate contracts:

- **Fair-draw probability:** for one specified valid line, `1/5,245,786` (approximately `0.00001906%`) is its exact six-match probability under the fair independent draw assumption. This is equal for every valid line.
- **Model selection probability:** `P_G1(S)` or `P_G2(S)` describes the chance that a named generator selects `S`. It is not the fair draw's chance of selecting `S`, nor the probability of winning. Show an exact value/percentage only when the target distribution is normalized and validated. Otherwise report `Not calculated` or `Not established`.
- **Historical pattern frequency:** `count(pattern)/N` is an empirical frequency for an explicit feature definition and source sample. For the established training analysis, display `N=902`, date range 2016-08-30 to 2022-11-12, data/model version, and feature definition. Do not label it a future probability.

No probability number may imply a guaranteed outcome or predictive effectiveness. Summary metadata must state the category and its applicable denominator, dataset, time span, model version, and feature definition; inapplicable fields are null rather than inferred.

### G0 uniform fair-random

Sample six distinct integers without replacement using a uniform method. In Python runtime generation, use a standard-library cryptographic bounded-integer source such as [`secrets.randbelow`](https://docs.python.org/3/library/secrets.html); in browsers, use the Web Crypto API (see the current [W3C Web Cryptography publication](https://www.w3.org/TR/webcrypto/)) with rejection sampling for bounded integers so modulo reduction does not introduce bias. The linked Web Cryptography Level 2 document is a Working Draft at this review date; confirm API support against the approved browser matrix before implementation. If Web Crypto is unavailable, fail closed. A deterministic injected source may be used for tests and research reproduction, but production browser randomness is not replayable unless its seed/source is actually recorded and suitable for that purpose.

### G1 historical-weighting control

For positive smoothed number weights `w_i`, a six-number set `S` has:

```text
P_G1(S | w) = product(w_i for i in S) / e_6(w_1,...,w_42)
```

`e_6` is the sixth elementary symmetric polynomial and normalizes the fixed-cardinality distribution. Use dynamic programming to compute the normalizer and sample a weighted subset. Fit smoothing only on approved training observations. Version all weights, smoothing configuration, training-data hash, and cutoff. Positive support prevents zero-probability combinations but does not prevent near-concentration. Before fitting, approve a concentration diagnostic and threshold (for example, maximum combination mass or cumulative mass over a fixed number of combinations); keep G1 unavailable if its exact normalized distribution fails the guardrail. G1 remains experimental regardless of whether it matches training marginals more closely.

### G2 calibrated soft-constraint model

Define a finite-parameter exponential-family target over valid sorted sets:

```text
P_G2(S | theta) = exp(theta · f(S)) / Z(theta)
Z(theta) = sum over all valid six-number sets S of exp(theta · f(S))
```

`f(S)` may contain low-dimensional odd/even, high/low, sum, sorted-gap, and consecutive-structure features. Define features so the energy decomposes into unary number terms plus adjacent sorted-number transition terms; this permits a dynamic-programming partition function and exact sequential sampling over the 42-number subset graph. If that decomposition is not sufficient for a proposed feature, that feature requires a new reviewed exact-normalization/sampler design before use.

Fit `theta` on approved historical training-only chronological development folds, with explicit regularization/shrinkage toward the uniform baseline. No fixed coefficient values are assumed. Finite scores ensure all valid sets retain positive probability but do not prevent near-concentration. Approve a concentration diagnostic and threshold before feature/parameter search and keep G2 unavailable if its exact normalized distribution fails the guardrail. Before release, also validate the partition function, sampler against small enumerated reference spaces, browser/Python distribution parity, calibration stability, and measured compute cost. If exact parity or acceptable cost is not demonstrated, keep G2 unavailable; do not substitute an unvalidated approximate chain or rejection sampler.

## Python and browser implementation consistency

- Store one versioned model contract and feature-definition version; both runtimes read the same serialized parameters.
- Canonicalize sets as six ascending integers and use the same combination universe and edge conditions.
- Compare exact probability values and sampler frequencies on toy universes where full enumeration is tractable.
- Run seeded cross-runtime fixtures to verify deterministic algorithms under an injected test random source.
- For production G0, use independent runtime-safe random sources; equivalence means equal target law, not equal output sequence.
- Any implementation, model artifact, dependency, or feature-definition change invalidates affected parity evidence.

## RNG behavior and reproducibility

Separate three modes: (1) visitor runtime generation uses platform randomness and does not promise sequence replay; (2) research fitting and exact probability calculations are deterministic for a fixed dataset hash, code revision, and configuration; (3) test fixtures inject a deterministic source and are never presented as real user randomness. Never log visitor-generated values remotely. A research batch records its outputs, generator/model/config hashes, software revision, mode, and generation time before it is timestamped.

## Model configuration and versioning

Each `ModelSpec` is immutable after approval. It includes schema and feature-definition versions, algorithm ID, model version, training artifact hash, training cutoff, fitting code revision, parameters or their public artifact, regularization configuration, normalizer specification, status, and review record. A new change creates a new version; do not rewrite a frozen version. G0 is the default. G1 is an experimental control. G2 stays pending until calibrated and reviewed.

## Data access restrictions

Only approved training inputs may be read during model development. Keep the existing 902 training records and their 2016-08-30 to 2022-11-12 boundary as the currently documented training fact. Do not open or score validation or locked-test rows. Build-time access controls and tests should allowlist training artifact paths and fail if a protected path is requested. New post-freeze observations belong to a separate prospective store and cannot be retroactively treated as training data for that frozen study.

Treat `source_row` as provenance metadata, never as a chronological key. Enforce uniqueness of source identifiers and chronological order by validated draw date. Do not modify or reorder original datasets.

New post-cutoff observations belong in a separate prospective store and shall not be merged into the original training source or the sealed validation/locked-test partitions, or retroactively treated as training data for a frozen study.

## Source acquisition and parser contract

Collection is design-only and disabled. The proposed Python `DrawSourceAdapter` contract is:

```text
check_access_conditions() -> SourceEligibility
health_check() -> SourceStatus
fetch_draws(date_range, game_id="lotto-6-42") -> SourceResponse
parse_response(response, parser_version) -> ParsedSourceRecords
normalize_records(records) -> DrawObservation candidates
report_source_status() -> SourceStatus
```

No health check or adapter operation may make a network request while its source is disabled or lacks a current approved access/reuse review. Eligibility checks include the current source identity, terms, robots rules, allowed request method, pacing, and any conditions or expiry. A written permission record is required only when applicable law, source terms, or source-specific restrictions require it; this is not a blanket prerequisite for every public page. A human-reviewed feasibility report is required before a production collection pilot.

The proposed ingestion stages are: (1) source eligibility; (2) ordinary permitted public retrieval; (3) source-specific HTML or structured-response parsing under a versioned parser; (4) date and combination normalization; (5) validation of Lotto 6/42 identity, date and exactly six distinct integers in 1..42; (6) stable game/draw deduplication without rewriting source files; (7) independent source cross-check where available; (8) quarantine of malformed, incomplete, conflicting, or unverified observations; (9) versioned JSON/JSONL storage with provenance and revisions; and (10) downstream use only for approved, verified post-registration outcomes.

Feasibility inputs and current limits:

- **PCSO official** `https://www.pcso.gov.ph/searchlottoresult.aspx` is the preferred authority. The public page currently exposes start/end date controls, a game selector, and a result table with game, combination, draw date, jackpot, and winners. Investigate ordinary WebForms GET/POST behavior, hidden form state, date filtering, pagination, and historical coverage. This page review did not establish its submission method, a documented API, robots rules, or reuse permission.
- **LottoPCSO.com** `https://www.lottopcso.com/6-42-lotto-result-history-and-summary/` is an independent third-party comparison candidate. Its visible history includes date, winning combination, and jackpot fields; its disclaimer says it is not affiliated with PCSO, disclaims completeness/accuracy, and directs readers to PCSO for verification. Review current terms, robots rules, and reuse scope before automation; never grant official verification without an authoritative cross-check.
- **LottoMatik** remains excluded from automation. The prior project review recorded restrictions on automated collection and redistribution; current terms could not be reverified in this review. Do not implement an adapter unless current restrictions are reviewed and resolved.
- FOI is excluded as an operational data-acquisition dependency. Public visibility and absence of an explicit ban do not by themselves establish permission.

Candidate implementation libraries for later evaluation, not approved dependencies: `requests` or `httpx` for ordinary HTTP; Python standard-library `html.parser` as a minimal alternative; BeautifulSoup4 or `lxml` for HTML parsing; Pandas only if its tabular handling is needed; and Pydantic or JSON Schema validation for contract checks. Reuse repository/platform code or installed dependencies first and record a compatibility rationale before adding any dependency.

Offline fixture design must cover differing date formats; published versus sorted number order; missing jackpot/winner fields; duplicate rows; incomplete/duplicate/out-of-range combinations; unexpected headers; unavailable placeholders; malformed markup; pagination and date-range boundaries; changed markup; HTTP denial, timeout and server failure; conflicts between sources; and corrected official results. Unresolved values remain null or quarantined; never infer a replacement. Preserve the original published combination separately from its canonical ascending numbers. Do not run live scraping or network tests as part of this proposal.

If a future scheduled collector is approved, retrieve at low frequency after result publication, verify the current PCSO draw timetable before configuring a schedule, and use bounded retries and configurable pacing that follows source-specific rules. A GitHub Actions schedule is not proof of exact execution time and must not be used as pre-draw timestamp evidence. Stop on access denial, clear prohibition, or unresolved restriction. No CAPTCHA solving, stealth browser, proxy rotation, authentication evasion, or WAF circumvention is allowed.

## Build and deployment architecture

Python commands validate and emit versioned JSON/JSONL artifacts. A static frontend build reads only approved public artifacts and emits static files. There is no v1 API, server-side generator, public write route, or app database. Compare GitHub Pages and Cloudflare Pages in a later deployment review; do not choose a host in this proposal. [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) describes static HTML/CSS/JavaScript hosting from a repository and says visitor IP addresses are logged and stored for security. [Cloudflare Pages Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/) documents automatic deployments on branch pushes and preview builds. Either can publish a static read-only registry, but neither by itself resolves public write registration.

Use Git-reviewed manifest commits plus external RFC 3161 timestamp tokens for prospective registration: canonicalize and hash the full frozen manifest, obtain the timestamp token before the target draw, preserve the request/response and verification evidence, and publish the read-only artifact when deployment policy permits. The token supports an assertion that the hashed data existed by the trusted time; it does not prove the content is true, legal, or predictive. Git commit timestamps alone are insufficient. A timestamp service, key custody, token verification, retention, and publication delay policy remain to be selected.

Do not rely on a scheduled GitHub Actions workflow as proof of exact draw-time execution: [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) says scheduled workflows run on the default branch and may be delayed or dropped during load, and public-repository schedules may be disabled after inactivity. Any future collector needs monitored, idempotent operation and separate authorization; missed runs must be recoverable without bypassing source restrictions.

## Client-side privacy and security

- No login, submission API, visitor profile, or visitor-number persistence in v1.
- Serve model and result artifacts read-only; validate schema versions, hashes where published, and all rendered text/data.
- Do not embed tokens or secrets in static assets or the repository.
- Treat downloaded CSV/JSON as user-controlled local output; sanitize filenames and content.
- Provide privacy notice for hosting-provider request logs and any hosting telemetry after provider review.
- Disable all source adapters by default. No request, crawl, scraping, WAF bypass, authentication bypass, or rate-limit evasion is permitted.
- Any future server or collector is a new trust boundary requiring threat review, data minimization, access controls, logging limits, and incident/recovery design.

## Accessibility and performance targets

Target WCAG 2.2 AA, verified by manual and automated checks. Preserve keyboard access, visible focus, semantic headings, labels and error associations, screen-reader descriptions of charts, non-color-only cluster/mode distinctions, reduced motion, zoom/reflow, and accessible downloads. Proposed performance target is NFR-006 in the PRD; identify a reference device and measure the 100-line batch before acceptance. G2's DP runtime and serialized artifact size require measurement rather than assumed limits.

## Testing and verification strategy

| ID | Verification | Acceptance condition |
| --- | --- | --- |
| TEST-001 | Combination boundary unit test | Exactly six unique integer values, all in `[1,42]`; invalid lengths/types/ranges rejected |
| TEST-002 | Input and duplicate-ball tests | Reject duplicate, malformed, and out-of-range values; reject nonpositive or excessive batch sizes |
| TEST-003 | G0 exact small-space and statistical tests | Uniform bounded selection passes exact toy-space checks and a predeclared goodness-of-fit check; no test is misrepresented as a proof of perfect randomness |
| TEST-004 | Batch-mode tests | Independent mode permits repeated complete lines; distinct mode has no repeated complete lines and is labelled separately |
| TEST-005 | G1 normalization and parity tests | DP normalizer agrees with exhaustive toy spaces; seeded sampler matches reference; positive weights retain support; an approved concentration diagnostic and threshold frozen before fitting are met |
| TEST-006 | G2 partition-function tests | Exact DP normalization agrees with enumeration on toy universes and sums to one within a predeclared numerical tolerance |
| TEST-007 | G2 sampler and parity tests | Exact sampler agrees with reference law on toy spaces; feature/model versions match in Python and browser |
| TEST-008 | Schema/manifest validation | Required fields, nullability, IDs, versions, hashes, and lifecycle transitions validated |
| TEST-009 | Access-boundary test | Build/test harness rejects any access to validation or locked-test paths |
| TEST-010 | Source-gate test | Collector adapters make no network request when disabled; approved source checks precede any later activation |
| TEST-011 | Registration-integrity test | Canonical manifest hash, TSA token, token verification, target draw, and frozen output agree |
| TEST-012 | Provenance rendering test | UI exposes generator/model version, data hash/cutoff, and experimental status |
| TEST-013 | G2 release gate | Independent reviewer signs calibration, normalization, sampler fidelity, compute-cost, and predeclared concentration-guardrail evidence before UI enablement |
| TEST-014 | Research-copy and plot review | Exact match law, all three probability categories, fair chance, source/sample/cutoff, disclaimers, and limitations are correct and accessible |
| TEST-015 | Results provenance test | Only reviewed/reuse-approved artifacts render; source classification, corrections, cross-verification, and missing source values remain explicit |
| TEST-016 | Local download/privacy test | Copy/download works; generated lines are absent from network requests and central storage |
| TEST-017 | Read-only registry test | Static registry has no visitor write route and lists only pre-draw frozen project batches |
| TEST-018 | Evaluation isolation test | Evaluation reads only outcomes after frozen timestamp and target draw; protocol cannot mutate in place |
| TEST-019 | Statistical plan test | Primary metric, multiplicity, uncertainty, power/sensitivity, and stopping rule frozen before outcomes |
| TEST-020 | Collector eligibility gate | Activation blocked unless ordinary access conditions, current terms/robots review, applicable reuse conditions, rate limits, owner, expiry, and approvals are documented; require written permission only where applicable |
| TEST-021 | A11y and compatibility review | WCAG 2.2 AA target assessed across keyboard, assistive technology, responsive states, and supported browsers |
| TEST-022 | G0 performance benchmark | 100-line generation meets the proposed 1-second p95 target on an agreed reference device/browser after page load; report exact environment and distribution |
| TEST-023 | Exclusive game-scope test | Inputs, artifacts, filters, and source parsers accept only Philippine Lotto 6/42 and reject or ignore other games |
| TEST-024 | Offline parser-contract fixtures | Synthetic fixtures cover normalization, malformed/missing/conflicting data, duplicate/correction handling, and disabled-source behavior without network requests |

Statistical tests are safeguards, not evidence of predictive advantage. Keep verification of source legality, privacy, accessibility, and actual hosted behavior distinct from unit-test evidence.

## Logging, errors, and recoverability

Do not send visitor combinations to logs. Display local validation errors beside the relevant field; do not silently coerce invalid numbers. On bad public artifacts, stop rendering the affected module and show its version and validation failure. Research batch manifests are immutable; corrections and failed attempts are separate append-only events with references to prior hashes. Back up registration manifests, RFC 3161 request/response tokens, verification status, and source-review evidence in controlled repositories. A failed timestamp or integrity check means the batch is not registered.

## Dependency and runtime compatibility

Use only dependencies needed for approved implementation. Python remains established; browser stack and version policy are pending approval. Pin versions and maintain lockfiles after implementation approval. Recheck Web Crypto availability on the browser support matrix. Do not add a database, server framework, collector dependency, or analytics SDK for the v1 static product.

## Technical risks and architecture decisions

1. **Static hosting versus registration writes:** resolved for v1 by a static read-only registry backed by Git-reviewed artifacts and an external timestamp; visitor submissions remain out of scope.
2. **G2 computational viability:** use exact DP over decomposable features; keep G2 unavailable if cost or parity is unacceptable.
3. **Source rights and machine access:** blocked pending primary-source review and written authorization where required.
4. **Host/provider privacy:** hosting itself may emit request metadata; complete provider-specific review before deployment.
5. **Statistical power:** no fixed confirmatory sample count; run power/sensitivity analysis against a predeclared primary metric.
6. **Evidence source gap:** no AGY proposal artifact was available; this proposal cannot assert AGY-specific agreement.

The proposed architecture baseline, generator roles, source gate, browser-local privacy boundary, and research verdict are shared with [01 Product Requirements](01_PRODUCT_REQUIREMENTS.md), [03 Application and Data Flow](03_APPLICATION_AND_DATA_FLOW.md), and [05 Backend and Data Schema](05_BACKEND_AND_DATA_SCHEMA.md).
