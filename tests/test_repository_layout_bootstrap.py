"""Synthetic checks for package paths and notebook startup behavior."""
# @codebase_provenance_JEO

from __future__ import annotations

import ast
import builtins
import json
import os
import sys
import types
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_lotto.interfaces import notebook_bootstrap
from magic_lotto.interfaces.notebook_bootstrap import build_bootstrap_cell, validate_notebook_environment
from magic_lotto.paths import LEGACY_REPOSITORY_PATHS, repository_path


NOTEBOOK_NAMES = {
    "lotto_statistical_analysis.ipynb",
    "lotto_phase4_feature_engineering.ipynb",
    "lotto_phase5a_ml_validation.ipynb",
    "lotto_phase5r_predictive_information.ipynb",
    "lotto_phase6b_model_semantic_review.ipynb",
    "lotto_phase7_kmeans_descriptive.ipynb",
}


def make_checkout(root: Path) -> None:
    for relative in (
        "README.md",
        "pyproject.toml",
        "src/magic_lotto/__init__.py",
        "docs/REPOSITORY_STRUCTURE.md",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")


class RepositoryLayoutBootstrapTests(unittest.TestCase):
    def test_legacy_paths_resolve_exactly_without_fallback(self):
        root = Path("fixture-root")
        for old, current in LEGACY_REPOSITORY_PATHS.items():
            self.assertEqual(repository_path(root, old), root / current)
        self.assertEqual(repository_path(root, "missing.csv"), root / "missing.csv")

    def test_bootstrap_installs_the_project_in_the_active_kernel(self):
        source = build_bootstrap_cell(("magic_lotto", "numpy"), ("data/input.csv",))
        self.assertIn("sys.executable, \"-m\", \"pip\", \"install\", \"-e\", \".[notebook]\"", source)
        self.assertIn("os.chdir(ROOT)", source)
        self.assertNotIn("sys.path.insert", source)

    def test_missing_required_path_fails_before_notebook_analysis(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            make_checkout(root)
            with self.assertRaisesRegex(FileNotFoundError, "missing.csv"):
                validate_notebook_environment(root, (), ("missing.csv",), False)

    def test_local_notebook_setup_reuses_checkout_without_path_injection(self):
        with TemporaryDirectory() as temp:
            checkout = Path(temp) / "checkout"
            make_checkout(checkout)
            (checkout / "data").mkdir()
            (checkout / "data/input.csv").write_text("synthetic\n", encoding="utf-8")
            notebook_dir = checkout / "notebooks"
            notebook_dir.mkdir()
            code = build_bootstrap_cell(("pathlib",), ("data/input.csv",), str(Path(temp) / "unused"))
            source_import = builtins.__import__
            commands = []

            def fake_run(args, **kwargs):
                args = list(args)
                commands.append(args)
                if args[1:4] == ["-m", "pip", "install"]:
                    return CompletedProcess(args, 0, "", "")
                return CompletedProcess(args, 1, "", "not a Git checkout")

            def local_import(name, *args, **kwargs):
                if name == "google.colab":
                    raise ModuleNotFoundError("No module named 'google.colab'", name="google.colab")
                return source_import(name, *args, **kwargs)

            prior_cwd = Path.cwd()
            prior_path = list(sys.path)
            prior_bytecode = sys.dont_write_bytecode
            try:
                os.chdir(notebook_dir)
                with patch.dict(os.environ, {"MAGIC_LOTTO_REF": "", "MAGIC_LOTTO_ROOT": ""}, clear=False), patch(
                    "builtins.__import__", side_effect=local_import
                ), patch("subprocess.run", side_effect=fake_run):
                    namespace = {}
                    exec(code, namespace, namespace)
                    self.assertEqual(Path(namespace["ROOT"]), checkout.resolve())
                    self.assertEqual(Path.cwd(), checkout.resolve())
                    exec(code, namespace, namespace)
                    self.assertEqual(Path(namespace["ROOT"]), checkout.resolve())
                self.assertFalse(any(command[:2] == ["git", "clone"] for command in commands))
                self.assertFalse(any(str(checkout.resolve()) in entry for entry in sys.path))
            finally:
                os.chdir(prior_cwd)
                sys.path[:] = prior_path
                sys.dont_write_bytecode = prior_bytecode

    def test_local_root_override_supports_kernels_started_outside_the_checkout(self):
        with TemporaryDirectory() as temp:
            base = Path(temp)
            checkout = base / "checkout"
            outside = base / "notebook-location"
            make_checkout(checkout)
            (checkout / "data").mkdir()
            (checkout / "data/input.csv").write_text("synthetic\n", encoding="utf-8")
            outside.mkdir()
            commands = []

            def fake_run(args, **kwargs):
                args = list(args)
                commands.append(args)
                if args[1:4] == ["-m", "pip", "install"]:
                    return CompletedProcess(args, 0, "", "")
                return CompletedProcess(args, 1, "", "not a Git checkout")

            source_import = builtins.__import__

            def local_import(name, *args, **kwargs):
                if name == "google.colab":
                    raise ModuleNotFoundError("No module named 'google.colab'", name="google.colab")
                return source_import(name, *args, **kwargs)

            prior_cwd = Path.cwd()
            prior_path = list(sys.path)
            prior_bytecode = sys.dont_write_bytecode
            try:
                os.chdir(outside)
                with patch.dict(os.environ, {"MAGIC_LOTTO_ROOT": str(checkout), "MAGIC_LOTTO_REF": ""}, clear=False), patch(
                    "builtins.__import__", side_effect=local_import
                ), patch("subprocess.run", side_effect=fake_run):
                    namespace = {}
                    exec(build_bootstrap_cell(("pathlib",), ("data/input.csv",)), namespace, namespace)
                self.assertEqual(Path(namespace["ROOT"]), checkout.resolve())
                self.assertEqual(Path.cwd(), checkout.resolve())
                self.assertFalse(any(command[:2] == ["git", "clone"] for command in commands))
            finally:
                os.chdir(prior_cwd)
                sys.path[:] = prior_path
                sys.dont_write_bytecode = prior_bytecode

    def test_colab_clones_requested_branch_once_and_never_resets(self):
        branch = "JEO/synthetic-colab-check"
        commit = "1234567890abcdef1234567890abcdef12345678"
        with TemporaryDirectory() as temp:
            base = Path(temp)
            start = base / "start"
            target = base / "content" / "Magic_Lotto"
            start.mkdir()
            commands = []
            clone_count = 0

            def fake_run(args, **kwargs):
                nonlocal clone_count
                args = list(args)
                commands.append(args)
                if args[:3] == ["git", "check-ref-format", "--branch"]:
                    return CompletedProcess(args, 0, "", "")
                if args[:2] == ["git", "clone"]:
                    clone_count += 1
                    make_checkout(Path(args[-1]))
                    return CompletedProcess(args, 0, "", "")
                if args[1:4] == ["-m", "pip", "install"]:
                    return CompletedProcess(args, 0, "", "")
                if args[:4] == ["git", "-C", str(target.resolve()), "rev-parse"]:
                    if args[4:] == ["--abbrev-ref", "HEAD"]:
                        return CompletedProcess(args, 0, branch + "\n", "")
                    return CompletedProcess(args, 0, commit + "\n", "")
                return CompletedProcess(args, 1, "", "unexpected command")

            google = types.ModuleType("google")
            google.__path__ = []
            colab = types.ModuleType("google.colab")
            google.colab = colab
            code = build_bootstrap_cell(("pathlib",), content_root=target)
            prior_cwd = Path.cwd()
            prior_path = list(sys.path)
            prior_bytecode = sys.dont_write_bytecode
            try:
                os.chdir(start)
                with patch.dict(sys.modules, {"google": google, "google.colab": colab}), patch.dict(
                    os.environ, {"MAGIC_LOTTO_REF": branch, "MAGIC_LOTTO_ROOT": ""}, clear=False
                ), patch("subprocess.run", side_effect=fake_run):
                    namespace = {}
                    exec(code, namespace, namespace)
                    self.assertEqual(Path(namespace["ROOT"]), target.resolve())
                    exec(code, namespace, namespace)
                self.assertEqual(clone_count, 1)
                self.assertTrue(any(command[:2] == ["git", "clone"] and branch in command for command in commands))
                self.assertFalse(any(command[1:2] in (["reset"], ["checkout"], ["clean"]) for command in commands))
            finally:
                os.chdir(prior_cwd)
                sys.path[:] = prior_path
                sys.dont_write_bytecode = prior_bytecode

    def test_requested_branch_mismatch_fails_without_switching_existing_checkout(self):
        with TemporaryDirectory() as temp:
            checkout = Path(temp) / "checkout"
            make_checkout(checkout)
            commands = []

            def fake_run(args, **kwargs):
                args = list(args)
                commands.append(args)
                if args[1:4] == ["-m", "pip", "install"]:
                    return CompletedProcess(args, 0, "", "")
                if args[4:] == ["--abbrev-ref", "HEAD"]:
                    return CompletedProcess(args, 0, "main\n", "")
                if args[4:] == ["HEAD"]:
                    return CompletedProcess(args, 0, "a" * 40 + "\n", "")
                return CompletedProcess(args, 1, "", "unexpected command")

            google = types.ModuleType("google")
            google.__path__ = []
            colab = types.ModuleType("google.colab")
            google.colab = colab
            code = build_bootstrap_cell(("pathlib",), content_root=Path(temp) / "content" / "Magic_Lotto")
            prior_cwd = Path.cwd()
            prior_path = list(sys.path)
            prior_bytecode = sys.dont_write_bytecode
            try:
                os.chdir(checkout)
                with patch.dict(sys.modules, {"google": google, "google.colab": colab}), patch.dict(
                    os.environ, {"MAGIC_LOTTO_REF": "feature/test", "MAGIC_LOTTO_ROOT": ""}, clear=False
                ), patch("subprocess.run", side_effect=fake_run):
                    with self.assertRaisesRegex(RuntimeError, "requested 'feature/test'"):
                        namespace = {}
                        exec(code, namespace, namespace)
                self.assertFalse(any(command[:2] == ["git", "clone"] for command in commands))
                self.assertFalse(any(command[3:4] in (["reset"], ["checkout"], ["clean"]) for command in commands))
            finally:
                os.chdir(prior_cwd)
                sys.path[:] = prior_path
                sys.dont_write_bytecode = prior_bytecode

    def test_all_notebooks_have_valid_bootstrap_cells_and_current_paths(self):
        import nbformat

        paths = sorted((ROOT / "notebooks").glob("*.ipynb"))
        self.assertEqual({path.name for path in paths}, NOTEBOOK_NAMES)
        self.assertEqual(len(paths), 6)
        for path in paths:
            notebook = nbformat.read(path, as_version=4)
            nbformat.validate(notebook)
            self.assertEqual(notebook.metadata.kernelspec.name, "python3", path.name)
            self.assertNotIn("version", notebook.metadata.language_info, path.name)
            code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
            self.assertTrue(code_cells, path.name)
            self.assertIn("MAGIC_LOTTO_BOOTSTRAP_V1", code_cells[0].source, path.name)
            bootstrap = ast.parse(code_cells[0].source)
            required_paths = next(
                ast.literal_eval(node.value)
                for node in bootstrap.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "REQUIRED_PATHS" for target in node.targets)
            )
            required_imports = next(
                ast.literal_eval(node.value)
                for node in bootstrap.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "REQUIRED_IMPORTS" for target in node.targets)
            )
            self.assertIn("magic_lotto", required_imports, path.name)
            for relative_path in required_paths:
                self.assertFalse(Path(relative_path).is_absolute(), f"{path.name}: {relative_path}")
                self.assertTrue((ROOT / relative_path).is_file(), f"{path.name}: missing {relative_path}")
            for cell in code_cells:
                source = cell.source
                self.assertNotRegex(source, r"(?<!\w)[A-Za-z]:\\", path.name)
                self.assertNotIn("sys.path.insert", source, path.name)
                if not any(line.lstrip().startswith(("%", "!")) for line in source.splitlines()):
                    ast.parse(source)
                if cell is not code_cells[0]:
                    self.assertNotRegex(source, r"ROOT\s*=\s*Path\.cwd", path.name)

    def test_notebook_generators_use_the_shared_setup_builder(self):
        for name in (
            "phase4_feature_engineering.py",
            "phase5a_ml_validation.py",
            "phase5r_predictive_information.py",
        ):
            source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("build_bootstrap_cell(", source, name)


if __name__ == "__main__":
    unittest.main()
