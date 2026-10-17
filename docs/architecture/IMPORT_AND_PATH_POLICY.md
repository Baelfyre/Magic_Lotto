<!-- @codebase_provenance_JEO -->
# Import and path policy

## Package imports

Reusable Phase 7 code lives under `src/magic_lotto/` and is installed from the repository's `pyproject.toml`. Production-style imports use the package namespace, for example:

```python
from magic_lotto.application.services.phase7_analysis_service import Phase7AnalysisService
from magic_lotto.domain.draw_642 import encode_draws
```

The active package does not add the repository root to `sys.path`. The old `scripts/phase7_kmeans_642.py` import and command remain as a thin compatibility entrypoint. Phase 4 through Phase 6 research utilities and notebook generators stay under `scripts/` because they are existing script interfaces; their source paths are not being presented as reusable application services.

## Repository and artifact paths

`magic_lotto.paths.REPOSITORY_ROOT` resolves from the installed `src` package. `repository_path(root, relative_path)` resolves current relative paths directly and maps only exact historical Phase 1 through Phase 3 basenames to their current locations. It does not search the filesystem or fall back to similarly named files.

Do not introduce machine-specific absolute paths. Notebook cells receive a verified root from the shared bootstrap. New application code should accept paths at the infrastructure or interface boundary; domain and research calculations should not locate files themselves.

The `scripts.repository_paths` module is a compatibility import for the existing Phase 4 through Phase 6 scripts. Historical recorded paths and hashes in reports remain unchanged. See the [migration guide](FILE_MIGRATION_MAP.md) before interpreting a stored hash against a current path.

## CLI and notebook interfaces

Install the editable package before using the console command:

```bash
python -m pip install -e ".[notebook]"
magic-lotto-phase7 --null-replicates 100 --seed 162
```

The compatibility command remains:

```bash
python scripts/phase7_kmeans_642.py --null-replicates 100 --seed 162
```

Notebook setup installs `.[notebook]` with the active kernel's `sys.executable`, changes to the verified root, checks required paths, then imports required modules. It recognizes `MAGIC_LOTTO_ROOT` for local Jupyter and `MAGIC_LOTTO_REF` for a Colab clone. Existing checkouts are never switched or reset. See the [notebook guide](NOTEBOOK_EXECUTION_GUIDE.md).
