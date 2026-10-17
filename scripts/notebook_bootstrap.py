"""Compatibility imports for existing notebook generator scripts."""
# @codebase_provenance_JEO

from magic_lotto.interfaces.notebook_bootstrap import (
    MAGIC_LOTTO_REPOSITORY_URL,
    MAGIC_LOTTO_ROOT_MARKERS,
    build_bootstrap_cell,
    repository_checkout_identity,
    validate_notebook_environment,
)

__all__ = [
    "MAGIC_LOTTO_REPOSITORY_URL",
    "MAGIC_LOTTO_ROOT_MARKERS",
    "build_bootstrap_cell",
    "repository_checkout_identity",
    "validate_notebook_environment",
]
