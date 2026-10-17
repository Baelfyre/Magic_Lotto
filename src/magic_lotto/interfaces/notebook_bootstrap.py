"""Notebook setup helpers for local Jupyter and Google Colab."""

from __future__ import annotations

# @codebase_provenance_JEO
import importlib
import re
import subprocess
import sys
from importlib import util
from pathlib import Path


MAGIC_LOTTO_REPOSITORY_URL = "https://github.com/Baelfyre/Magic_Lotto.git"
MAGIC_LOTTO_ROOT_MARKERS = (
    "README.md",
    "pyproject.toml",
    "src/magic_lotto/__init__.py",
    "docs/REPOSITORY_STRUCTURE.md",
)


def repository_checkout_identity(root: Path, runner=None) -> tuple[str | None, str | None]:
    runner = runner or subprocess.run
    branch = runner(
        ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    commit = runner(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if branch.returncode or commit.returncode:
        return None, None
    return branch.stdout.strip(), commit.stdout.strip()


def validate_notebook_environment(
    root: Path,
    required_modules: tuple[str, ...],
    required_paths: tuple[str, ...],
    in_colab: bool,
    requested_ref: str | None = None,
    runner=None,
) -> tuple[str | None, str | None]:
    root = Path(root).resolve()
    if not all((root / marker).is_file() for marker in MAGIC_LOTTO_ROOT_MARKERS):
        raise RuntimeError(f"The selected path is not a Magic_Lotto repository root: {root}")
    absolute = [path for path in required_paths if Path(path).is_absolute()]
    if absolute:
        raise ValueError(f"Notebook required paths must be repository-relative: {absolute}")
    missing = [path for path in required_paths if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError(
            f"The Magic_Lotto checkout at {root} is missing required notebook inputs: "
            f"{', '.join(missing)}. Check the selected branch and repository contents."
        )
    branch, commit = repository_checkout_identity(root, runner)
    if requested_ref and requested_ref not in (branch, commit):
        raise RuntimeError(
            f"MAGIC_LOTTO_REF requested {requested_ref!r}, but the existing checkout is "
            f"{branch or 'unavailable'!r} at {commit or 'unavailable'}. Setup will not switch or "
            "reset an existing checkout. Restart a fresh Colab runtime so the requested branch can be cloned."
        )
    for module in required_modules:
        try:
            importlib.import_module(module)
        except ImportError as error:
            environment = "Google Colab" if in_colab else "local Jupyter"
            raise ModuleNotFoundError(
                f"Required notebook import {module!r} is unavailable in {environment}. "
                "The editable project install and notebook extra should provide declared dependencies."
            ) from error
    return branch, commit


def build_bootstrap_cell(
    required_modules: tuple[str, ...],
    required_paths: tuple[str, ...] = (),
    content_root: str | Path = "/content/Magic_Lotto",
) -> str:
    """Render the setup cell shared by hand-authored and generated notebooks."""
    return f'''# MAGIC_LOTTO_BOOTSTRAP_V1
from pathlib import Path
import os
import subprocess
import sys

REQUIRED_IMPORTS = {tuple(required_modules)!r}
REQUIRED_PATHS = {tuple(required_paths)!r}
ROOT_MARKERS = {MAGIC_LOTTO_ROOT_MARKERS!r}
COLAB_CLONE_ROOT = Path({str(content_root)!r})
REPOSITORY_URL = {MAGIC_LOTTO_REPOSITORY_URL!r}

def _is_magic_lotto_root(path):
    return all((path / marker).is_file() for marker in ROOT_MARKERS)

def _find_magic_lotto_root(start):
    start = Path(start).resolve()
    return next((path for path in (start, *start.parents) if _is_magic_lotto_root(path)), None)

try:
    import google.colab
except ModuleNotFoundError as error:
    if error.name not in {{"google", "google.colab"}}:
        raise
    IN_COLAB = False
else:
    IN_COLAB = True

REQUESTED_REF = os.environ.get("MAGIC_LOTTO_REF") or None
ROOT_OVERRIDE = os.environ.get("MAGIC_LOTTO_ROOT")
REPO_ROOT = _find_magic_lotto_root(Path(ROOT_OVERRIDE)) if ROOT_OVERRIDE else _find_magic_lotto_root(Path.cwd())
if ROOT_OVERRIDE and REPO_ROOT is None:
    raise FileNotFoundError(f"MAGIC_LOTTO_ROOT is not a Magic_Lotto checkout: {{ROOT_OVERRIDE}}")
if REPO_ROOT is None and IN_COLAB:
    if COLAB_CLONE_ROOT.exists():
        if not _is_magic_lotto_root(COLAB_CLONE_ROOT):
            raise RuntimeError(
                f"Existing Colab path is not a usable Magic_Lotto checkout: {{COLAB_CLONE_ROOT}}. "
                "This setup will not overwrite it."
            )
        REPO_ROOT = COLAB_CLONE_ROOT
    else:
        clone_ref = REQUESTED_REF or "main"
        valid_ref = subprocess.run(
            ["git", "check-ref-format", "--branch", clone_ref],
            capture_output=True, text=True, check=False,
        )
        if valid_ref.returncode:
            raise ValueError(f"MAGIC_LOTTO_REF is not a valid branch name: {{clone_ref!r}}")
        cloned = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", "--branch", clone_ref,
             REPOSITORY_URL, str(COLAB_CLONE_ROOT)],
            capture_output=True, text=True, check=False,
        )
        if cloned.returncode:
            raise RuntimeError(f"Could not clone Magic_Lotto branch {{clone_ref!r}}: {{cloned.stderr.strip()}}")
        if not _is_magic_lotto_root(COLAB_CLONE_ROOT):
            raise RuntimeError(f"The cloned path is not a usable Magic_Lotto checkout: {{COLAB_CLONE_ROOT}}")
        REPO_ROOT = COLAB_CLONE_ROOT

if REPO_ROOT is None:
    raise FileNotFoundError(
        "Could not find a Magic_Lotto checkout in the current directory or its parents. "
        "Set MAGIC_LOTTO_ROOT to a local checkout, or run this notebook in Google Colab."
    )
ROOT = REPO_ROOT.resolve()
os.chdir(ROOT)
sys.dont_write_bytecode = True
installed = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-e", ".[notebook]"],
    capture_output=True, text=True, check=False,
)
if installed.returncode:
    raise RuntimeError(f"Could not install Magic_Lotto dependencies in this notebook kernel: {{installed.stderr.strip()}}")
root = ROOT

from magic_lotto.interfaces.notebook_bootstrap import validate_notebook_environment
BRANCH, COMMIT = validate_notebook_environment(
    ROOT, REQUIRED_IMPORTS, REQUIRED_PATHS, IN_COLAB, REQUESTED_REF, subprocess.run
)
print(f"Magic_Lotto root: {{ROOT}}")
print(f"Checkout: {{BRANCH or 'unavailable'}} @ {{COMMIT or 'unavailable'}}")
print(f"Notebook imports validated: {{', '.join(REQUIRED_IMPORTS) or 'standard library only'}}")
'''
