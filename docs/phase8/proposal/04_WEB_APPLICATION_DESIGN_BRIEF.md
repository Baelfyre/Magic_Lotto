# Web Application Design Brief
<!-- @codebase_provenance_JEO -->

- **Status:** Proposed design direction; no UI is implemented
- **Baseline:** `origin/main` at `b67e31572187001c89266839871c9e28456b90e8`
- **Last reviewed:** 2026-10-17
- **Research verdict:** `STOP_NO_REPRODUCIBLE_PREDICTIVE_SIGNAL`

## Design objectives and audience

The interface should help visitors generate valid Lotto 6/42 combinations and understand how the generator relates to the fair-random chance model. Research readers should be able to inspect model versions, data cutoffs, sources, and limitations. The site must communicate that no mode predicts winning numbers and that historical pattern fit is not predictive evidence.

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

Visualizations must identify data source, record count, time window, verification state, and whether the view is empirical or theoretical. Always distinguish:

- the exact fair-random reference distribution;
- an approved historical empirical distribution;
- a model's fitted training distribution;
- any post-registration outcome evaluation.

Use frequency bars with denominators and uncertainty where appropriate. Include a table or text alternative for every chart. Do not imply that a deviation in a small sample predicts a future draw. The exact match-count mass function is hypergeometric as documented in [01 Product Requirements](01_PRODUCT_REQUIREMENTS.md); no rounded visual display should replace the formula or expose unverified entropy or sampler acceptance-rate claims.

## Historical draws explorer

The explorer reads only reviewed, versioned artifacts with approved reuse status. Provide game/date filters, source attribution, verification status, missing-field disclosure, and a correction history. A source's website link does not itself authorize copying, scraping, or republication. If the source gate is not met, the explorer is hidden or explicitly unavailable; never fill missing winner counts, amounts, or source dates by guesswork.

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

> This tool generates number combinations. It does not predict lottery outcomes or improve the odds of a fair draw. G0 gives every valid 6/42 combination equal probability; experimental modes describe research distributions, not forecasts.

Methods/research views should also state the existing STOP verdict, distinguish descriptive model fit from predictive effectiveness, note the training boundary, and state that current validation and locked-test partitions remain sealed. No new claim may reverse that verdict without independent review of new evidence under a separately approved protocol.

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
| Results source not approved | Explain that the explorer is unavailable pending access/reuse review; link to the publisher if appropriate |
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

## Decisions pending design review

Approve or revise the page hierarchy, framework, browser support policy, exact mobile performance target, final notice wording, host/provider privacy notice, chart library, and whether any historical artifact qualifies for display. Those choices do not change the G0 default, source gate, sealed partitions, or STOP verdict.
