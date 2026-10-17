"""Output contract for the Phase 7 command-line use case."""

from __future__ import annotations

# @codebase_provenance_JEO
from pathlib import Path
from typing import Protocol


class Phase7ArtifactWriter(Protocol):
    def write(self, result: dict, output_dir: Path, seed: int) -> None:
        """Write the existing Phase 7 charts and descriptive reports."""
