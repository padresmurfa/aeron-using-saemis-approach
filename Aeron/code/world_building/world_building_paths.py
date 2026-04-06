"""Shared output-path helpers for world-building artifacts."""

from __future__ import annotations

from pathlib import Path


def mapping_root_dir(current_file: str) -> Path:
    script_path = Path(current_file).resolve()
    output_dir = script_path.parents[2] / "mapping"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def step_output_dir(current_file: str) -> Path:
    output_dir = mapping_root_dir(current_file) / Path(current_file).stem
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def canonical_artifact_name(
    current_file: str,
    name: str,
    *,
    default_extension: str | None = None,
) -> str:
    artifact_name = Path(name).name
    step_name = Path(current_file).stem

    prefixed_name = f"{step_name}__"
    if artifact_name.startswith(prefixed_name):
        artifact_name = artifact_name[len(prefixed_name) :]
    elif artifact_name.startswith("__"):
        artifact_name = artifact_name[2:]

    if default_extension and not artifact_name.endswith(default_extension):
        artifact_name = f"{artifact_name}{default_extension}"
    return artifact_name


def step_output_path(
    current_file: str,
    name: str,
    *,
    default_extension: str | None = None,
) -> Path:
    return step_output_dir(current_file) / canonical_artifact_name(
        current_file,
        name,
        default_extension=default_extension,
    )
