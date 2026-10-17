"""Pure in-memory Phase 8A G0 entry point; no IO or historical-data consumer."""

from __future__ import annotations

from magic_lotto.research.g0_uniform import (
    INDEPENDENT_WITH_REPLACEMENT, G0GenerationResult, RandBelow, generate_g0,
)


def generate_g0_lines(
    batch_size: int = 1, *,
    sampling_mode: str = INDEPENDENT_WITH_REPLACEMENT,
    random_source: RandBelow | None = None,
) -> G0GenerationResult:
    return generate_g0(batch_size, sampling_mode=sampling_mode, random_source=random_source)
