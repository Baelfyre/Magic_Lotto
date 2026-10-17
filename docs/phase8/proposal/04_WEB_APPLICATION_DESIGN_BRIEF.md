# Web Application Design Brief
<!-- @codebase_provenance_JEO -->

- **Status:** Proposed design direction; no UI is implemented
- **Baseline:** `origin/main` at `998f16d133b4500dfd65fa57fb73f9d84c91f8f4` (merged PR #4)
- **Last reviewed:** 2026-10-17
- **Research verdict:** `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`

**Scope:** Philippine Lotto 6/42 only. Exclude 3D Lotto, all other lottery games, and unrelated prediction systems from controls, results, and research views.

## Design objectives and audience

The interface should help visitors generate valid Philippine Lotto 6/42 combinations and understand how the generator relates to the fair-random chance model. Research readers should be able to inspect model versions, data cutoffs, sources, and limitations. The site must communicate that no mode predicts winning numbers and that historical pattern fit is not predictive evidence.

Primary audiences are visitors using local generation, research readers exploring approved artifacts, and maintainers/reviewers auditing provenance. The design does not support sales, betting, account creation, social sharing of personal picks, or visitor submissions.

## Product identity and visual direction

Use a calm, neutral research-tool identity: clear typography, restrained color, data-forward layouts, and no casino-style visual cues. Avoid lucky-number symbolism, jackpot imagery, urgency, near-miss animation, or language that could imply a better chance of winning. Present every mode with a persistent status label and explain the baseline near the action that generates combinations.

## Information architecture

| Page | Purpose | Default visitor action |
| --- | --- | --- |
| Generate | Local combination generation and mode explanation | Generate with G0 |
| Methods | Explain G0, G1, G2, probability formulas, and research limitations | Compare the methods |
| Results Explorer | Browse only reviewed, permitted draw artifacts | Filter a published series |
| Research Registry | Inspect frozen pre-draw research batches and later append-only evaluations | Verify a study manifest |
| About and Sources | Source status, data provenance, correction policy, privacy notice, and project verdict | Review evidence and boundaries |

Navigation must not imply that a page exists before its data/artifact gate passes. If no approved result artifacts exist, show a clear “not available; source review pending” state rather than an empty chart that looks like zero results.

## Page hierarchy and navigation

1. **Generate** is the landing page and visibly defaults to G0.
2. **Methods** provides plain-language details with links to exact definitions.
3. **Results Explorer** appears only when a compatible approved artifact is available.
4. **Research Registry** separates registered project batches from visitor generation.
5. **About and Sources** contains source/reuse status and project research verdict.

Use one descriptive page heading, a short purpose statement, primary task region, limitations/source context, and secondary details. Keep the selected generator, model version, and privacy behavior visible when navigating or downloading.

## Current repository foundation and proposed client boundary

Merged PR #4 added the Phase 7 package and shared startup for the six notebooks. It did not add a web client, frontend source directory, Phase 8 model artifacts, public registry, or results API. The existing `reports/phase7_kmeans_642/` outputs are descriptive Phase 7 evidence, not a stable browser data contract or a source of approved public result records. Keep the design here as proposed until the frontend stack and client source location are approved. The shared notebook bootstrap is for research notebooks; it is not a browser-client runtime.

If approved, the client will read only versioned Phase 8 JSON artifacts whose schema, provenance, public-display status, and reuse conditions have passed review. Proposed model artifacts, public research/registry artifacts, and future observations are kept under the proposed locations `models/phase8/`, `reports/phase8/`, and `data/prospective/lotto-6-42/`, respectively. These directories are not present in the current tree and must not be treated as implemented. Do not repurpose historical result files or the Phase 7 output directory as a client API.

## Generator interface

Recommended order:

1. Mode selector with G0 selected initially.
2. Plain-language mode description and status: `baseline`, `experimental control`, or `experimental; calibration gate required`.
3. Number of lines input with documented bounds, default, keyboard operation, and validation feedback.
4. Optional complete-line sampling mode: `independent lines (may repeat)` by default; `distinct lines` is separately selected and explained.
5. Generate button, then result region with a polite live announcement.
6. Combination list, copy/download actions, generator/model provenance, fair-probability notice, and no-prediction notice.

Do not expose G1 or G2 until their artifact status and release checks pass, including the predeclared concentration guardrail. G2 should remain unavailable if calibration, exact-normalization, sampler-parity, concentration, or performance evidence is missing. Do not let an experimental mode appear selected merely because it was the last used mode on a shared device.

## Uniform and experimental mode differentiation

- **G0 — Uniform fair-random:** primary/default style, neutral label, explanation that all `5,245,786` valid combinations are equally likely under the fair draw model.
- **G1 — Historical-weighting control:** secondary label “experimental control”; explain that historical weighting does not establish future advantage and show model version/cutoff.
- **G2 — Calibrated soft constraints:** disabled until approved; when approved, show features and calibration version and preserve an “experimental, not a forecast” notice.

Use text and icon/shape as well as color so mode status is not color-only. Do not use promotional words such as “hot,” “due,” “smart pick,” “optimized win,” or “high probability.”

## Combination presentation

Show each line as a text list in ascending order with the six values separated clearly. Do not communicate likelihood through size, brightness, gold styling, animation, or ranking. If optional descriptive statistics are displayed, label them as summaries of the line, not likelihood scores. For a batch, state whether duplicate complete lines are allowed by the selected mode. Copy and downloads should have a text equivalent and preserve the model/configuration metadata when generated as a research batch; visitor downloads need not contain personal metadata.

## Distribution and statistical visualization

Visualizations must identify data source, record count, time window, verification state, and whether the view is empirical or theoretical. Always distinguish and label:

- **Fair-draw probability:** for one exact valid line, 1/5,245,786 (approximately 0.00001906%) under a fair independent draw. Every valid line has the same jackpot chance.
- **Model selection probability:** the probability that the named, validated G1/G2 distribution selects that line. It describes generator selection, not a draw outcome or chance of winning.
- **Historical pattern frequency:** the observed count of a defined pattern divided by its stated sample size. For training data, show N=902, the 2016-08-30 to 2022-11-12 date range, data/model version, and feature definition.
- **Post-registration outcome evaluation:** a separate prospective metric evaluated only under the frozen protocol and using authorized post-registration outcomes.

Show exact model percentages only after mathematical normalization and validation. Otherwise show “Not calculated” or “Not established.” Do not use a model score as a substitute for jackpot probability.

Use frequency bars with denominators and uncertainty where appropriate. Include a table or text alternative for every chart. Do not imply that a deviation in a small sample predicts a future draw. The exact match-count mass function is hypergeometric as documented in [01 Product Requirements](01_PRODUCT_REQUIREMENTS.md); no rounded visual display should replace the formula or expose unverified entropy or sampler acceptance-rate claims.

## Historical draws explorer

The explorer reads only reviewed, versioned artifacts with approved reuse status. Its game filter and data contract are limited to Philippine Lotto 6/42. Identify PCSO as the authoritative result publisher and preferred source candidate. Identify LottoPCSO.com as an independent third-party comparison site; it cannot confer official verification without suitable PCSO cross-check. LottoMatik remains excluded from automated collection pending current terms review. Provide draw-date filters, source attribution, source classification, access/reuse status, verification status, missing-field disclosure, and correction history. A website link or public page does not itself authorize copying, automated retrieval, or republication. If a source gate is not met, hide the data or show a clear unavailable state; never fill missing winner counts, amounts, or source dates by guesswork.

## Prospective research dashboard

Separate registered project research from visitor picks. For each study, display:

- study ID and immutable manifest version/hash;
- target draw date/time zone and registration status;
- timestamp authority and token-verification status;
- generator/model/config versions and exact registered line count;
- frozen primary/secondary metrics and analysis-plan version;
- after the draw, outcome-source verification and append-only evaluation events.

Show registration as pre-draw only when the RFC 3161 token verifies against the manifest hash and precedes the scheduled draw time. Git commit time or page publication time alone must not appear as the authoritative registration timestamp. The public view is read-only. Do not collect visitor-generated combinations through it.

## Model version and provenance display

For G1/G2, show algorithm ID and name, model/config version, training-data hash/reference, training cutoff, feature-definition version, calibration status, and release-review link. For G0, show algorithm name, runtime random source class, and statement that no user sequence is centrally recorded. Every research chart should expose the same provenance panel or a direct link to it.

## Scientific notices and limitations

Persistent concise notice near generation:

> Magic Lotto is an independent educational project for Philippine Lotto 6/42 only. It is not affiliated with or endorsed by PCSO or any Philippine government agency. These experimental combinations are not predictions or guaranteed wins; under a fair draw every valid line has the same 1 in 5,245,786 jackpot chance. No tickets or wagers are sold or accepted.

The About and Methods views shall provide this full disclaimer using original project wording:

> Magic Lotto is an independent educational and experimental project focused only on Philippine Lotto 6/42. It is not affiliated with, authorized by, sponsored by, or endorsed by the Philippine Charity Sweepstakes Office (PCSO) or any Philippine government agency. Its research purposes include machine learning experimentation, probability theory, statistical pattern analysis, random-behavior analysis, probabilistic combination generation, and statistical simulation and comparison. Generated combinations are not predictions or guaranteed winning numbers. Under a fair draw, every valid Lotto 6/42 combination has the same 1 in 5,245,786 jackpot probability. A model's probability of selecting a combination describes its own output distribution, not the chance that the draw will produce that combination. Historical pattern frequencies describe recorded data and do not establish future predictive effectiveness. Magic Lotto does not sell lottery tickets, accept wagers, or operate games. PCSO is identified as the authoritative draw-result publisher; independent reference sites are labelled third-party and remain subject to access and reuse review.

Methods/research views should also state the existing STOP verdict, distinguish descriptive model fit from predictive effectiveness, note the 902-draw training boundary, and state that current validation and locked-test partitions remain sealed. No new claim may reverse that verdict without independent review of new evidence under a separately approved protocol.

## Interaction and state behavior

- Keep G0 selected on first load. Persist no visitor output in a shared browser profile unless a later privacy decision explicitly approves local persistence.
- Validate inputs on submission and associate errors with controls; preserve the last valid local output if a subsequent request fails.
- Use an accessible status region to announce completion and errors without moving focus unexpectedly.
- Disable copy/download when there is no result; confirm successful copy accessibly.
- Do not display stale model artifacts as current: show their version and mark them unavailable if schema or hash validation fails.
- Treat “distinct lines” as an explicit mode change and explain its effect before generation.
- Reduce or eliminate motion; no auto-advancing charts or flashing outcomes.

## Responsive design

Support narrow phone portrait, phone landscape, tablet, and desktop widths. Controls should stack on small screens; the result list should remain readable without horizontal scroll. Charts may reflow, but must retain labels and a text alternative. At 200% zoom, primary generation controls and notices remain available without clipped content.

## Accessibility target: WCAG 2.2 AA

This is a proposed target, not a conformance claim. Acceptance review must include keyboard-only use, visible focus, semantic names/roles, heading order, screen-reader mode and result announcements, non-color mode status, contrast, text resizing/zoom, reduced-motion settings, accessible validation, touch target sizing, and chart alternatives. Automated scans supplement but do not replace manual review. Reference [WCAG 2.2](https://www.w3.org/TR/WCAG22/) during implementation and document tested browsers/assistive technology.

## Color, typography, and component recommendations

- **Color:** neutral dark text on light backgrounds, restrained blue/teal accent for informational controls, amber for experimental status, and red only for errors or blocked states. Verify contrast; do not use color as the sole indicator.
- **Typography:** system sans-serif for interface text; tabular numerals for number lines and metrics; readable body size and line length.
- **Components:** native labelled inputs and buttons; mode cards with explicit status; result list; provenance disclosure; source badge with text; accessible chart container plus table; inline validation summary; downloadable-data notice.
- **Layout:** consistent spacing, clear focus outlines, limited decorative imagery, predictable reading order.

## Empty, loading, and error states

| State | User-facing treatment |
| --- | --- |
| No result yet | Explain the next action; no empty placeholder combinations |
| Results source not approved | Explain that the explorer is unavailable pending source-specific access/reuse review; link to PCSO as publisher if appropriate |
| Model artifact loading | Identify model/version, use a concise status message, and leave G0 available if safe |
| Invalid/unsupported model | Hide the affected mode and explain integrity/version failure; do not fall back silently |
| Invalid input | Show a specific associated message and keep valid local results intact |
| Web Crypto unsupported | Disable generation with a supported-browser explanation |
| Registry has no frozen batches | State “no approved registered batches” rather than imply there are no predictions/outcomes |
| Timestamp evidence missing/invalid | Mark the batch unregistered/quarantined; do not show a pre-draw claim |
| Network unavailable | Keep G0 available; indicate that static model/result artifacts cannot be refreshed |

## Usability testing plan

After implementation approval, test with representative novice visitors and research readers. Tasks: identify default mode and its odds; generate/download lines; find why G1/G2 are experimental or unavailable; locate the model version/cutoff; find the source/reuse status; distinguish visitor output from a registered study batch; and interpret a historical plot without calling it a forecast. Record task completion, observed confusion, assistive technology/browser, and changes. Do not ask participants to provide personal ticket choices or retain generated combinations.

## Design acceptance criteria

1. G0 is the default and the equal-probability statement is visible before generation.
2. Experimental modes have distinct text labels and cannot be enabled without approved model status.
3. No interface copy suggests prediction, improved odds, lucky or due numbers.
4. Local generation/copy/download requires no account and sends no generated values over the network.
5. Charts identify source, range, sample size, verification state, and have a text/table alternative.
6. Result explorer and registry are read-only and show source/timestamp status.
7. Primary flows pass the planned WCAG 2.2 AA review and responsive checks.
8. Empty, blocked, invalid, and offline states explain what happened and what remains possible.
9. Every result and research view is limited to Lotto 6/42 and distinguishes the three probability categories with their denominators and provenance.
10. The concise generator notice and full independent-project disclaimer are present and do not imply PCSO affiliation or predictive effectiveness.

## Decisions pending design review

Approve or revise the page hierarchy, framework, browser support policy, exact mobile performance target, host/provider privacy notice, chart library, and whether any historical artifact qualifies for display. The supplied disclaimer wording is a proposal for human review. Current PCSO access/reuse conditions and LottoPCSO.com terms/robots/reuse require source-specific review; LottoMatik stays excluded until its current terms are reverified. Those choices do not change the G0 default, exclusive game scope, sealed partitions, or STOP verdict.
