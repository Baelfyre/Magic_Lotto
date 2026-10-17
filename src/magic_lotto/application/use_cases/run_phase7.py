"""Run the established Phase 7 analysis and write its existing outputs."""

from __future__ import annotations

# @codebase_provenance_JEO
from pathlib import Path

from magic_lotto.application.ports.phase7_artifact_writer import Phase7ArtifactWriter
from magic_lotto.application.services.phase7_analysis_service import Phase7AnalysisService


def run_phase7(
    service: Phase7AnalysisService,
    writer: Phase7ArtifactWriter,
    output_dir: Path,
    null_replicates: int = 100,
    seed: int = 162,
) -> dict:
    result = service.run(null_replicates=null_replicates, seed=seed)
    writer.write(result, output_dir, seed)
    return {
        "summary_path": str(output_dir / "summary.json"),
        "observed_inertia": float(result["model"].inertia_),
        "null_mean_inertia": float(result["null_inertia"].mean()),
        "lower_tail_p": float(result["p_lower"]),
    }
