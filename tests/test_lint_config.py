"""The ruff config has to keep up with app/core/section_manifest.py.

A file added to SECTION_FILES is exec'd into the shared namespace, so ruff will
report its injected globals as F821 and boot_dependencies' imports as F401. If
nobody teaches pyproject.toml about the new file, the lint job goes red for
reasons that are not defects.
"""

from pathlib import PurePosixPath

import pytest

from app.core.section_manifest import PROJECT_ROOT, SECTION_FILES

try:  # tomllib landed in 3.11; the dev box still runs 3.10
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - depends on interpreter
    tomllib = pytest.importorskip("tomli", reason="need a TOML parser")

# Reported by the loader's design, not by the code's quality.
STRUCTURAL_RULES = {"F821", "F401", "E402"}


def _per_file_ignores() -> dict[str, list[str]]:
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as handle:
        config = tomllib.load(handle)
    return config["tool"]["ruff"]["lint"]["per-file-ignores"]


def _relative_section_paths() -> list[PurePosixPath]:
    return [
        PurePosixPath(path.resolve().relative_to(PROJECT_ROOT).as_posix())
        for path in SECTION_FILES
    ]


@pytest.mark.parametrize("section_path", _relative_section_paths(), ids=str)
def test_every_section_file_is_covered(section_path: PurePosixPath) -> None:
    ignores = _per_file_ignores()
    matched = [
        rules
        for pattern, rules in ignores.items()
        if section_path.match(pattern)
    ]
    assert matched, (
        f"{section_path} is exec'd by runtime_loader but no per-file-ignores "
        "entry in pyproject.toml covers it"
    )
    covered = {rule for rules in matched for rule in rules}
    assert covered >= STRUCTURAL_RULES, (
        f"{section_path} is missing {sorted(STRUCTURAL_RULES - covered)}"
    )


def test_no_ignore_entry_points_at_a_missing_file() -> None:
    """A path that stopped being a section file should lose its entry too."""
    section_paths = _relative_section_paths()
    for pattern in _per_file_ignores():
        if "*" in pattern:
            continue
        assert PurePosixPath(pattern) in section_paths, (
            f"{pattern} has a per-file-ignores entry but is not in SECTION_FILES"
        )
