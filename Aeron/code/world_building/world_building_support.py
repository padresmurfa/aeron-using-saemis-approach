"""Shared support for the ordered world-building pipeline."""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import fields, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    from .world_building_paths import step_output_path
    from .world_building_visualizations import write_default_layer_visualizations
except ImportError:
    from world_building_paths import step_output_path  # type: ignore
    from world_building_visualizations import write_default_layer_visualizations  # type: ignore


_STATE_CACHE: dict[tuple[str, str], tuple[Any, ...]] = {}
_ARTIFACT_CACHE: set[tuple[str, str, str]] = set()


def load_pipeline_module(
    package_name: str | None, current_file: str, module_name: str
) -> Any:
    if package_name:
        return importlib.import_module(f"{package_name}.{module_name}")

    script_dir = Path(current_file).resolve().parent
    script_dir_str = str(script_dir)
    if script_dir_str not in sys.path:
        sys.path.insert(0, script_dir_str)
    return importlib.import_module(module_name)


def serialize_for_json(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: serialize_for_json(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): serialize_for_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_for_json(item) for item in value]
    return value


def data_output_path(current_file: str) -> Path:
    return step_output_path(current_file, "output.json")


def write_layer_results_json(
    current_file: str,
    criteria: Any,
    states: Iterable[Any],
    *,
    extra: dict[str, Any] | None = None,
) -> Path:
    state_list = list(states)
    output_path = data_output_path(current_file)

    payload = {
        "script_name": Path(current_file).name,
        "json_name": output_path.name,
        "criteria": serialize_for_json(criteria),
        "state_count": len(state_list),
        "initial_state": serialize_for_json(state_list[0]) if state_list else None,
        "present_day_state": serialize_for_json(state_list[-1]) if state_list else None,
        "states": serialize_for_json(state_list),
    }
    if extra:
        payload["extra"] = serialize_for_json(extra)

    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def criteria_cache_key(criteria: Any) -> str:
    total_duration_years = getattr(criteria, "total_duration_years", "unknown")
    step_years = getattr(criteria, "step_years", "unknown")
    return f"{total_duration_years}:{step_years}"


def materialize_layer_states(
    current_file: str,
    criteria: Any,
    build_states: Callable[[], Iterable[Any]],
    *,
    extra_builder: Callable[[tuple[Any, ...]], dict[str, Any] | None] | None = None,
    artifact_key: str | None = None,
    artifact_writer: Callable[[tuple[Any, ...]], None] | None = None,
) -> tuple[Any, ...]:
    resolved_path = str(Path(current_file).resolve())
    cache_key = (
        resolved_path,
        criteria_cache_key(criteria),
        artifact_key or "",
    )
    if cache_key in _STATE_CACHE:
        state_tuple = _STATE_CACHE[cache_key]
    else:
        state_tuple = tuple(build_states())
        _STATE_CACHE[cache_key] = state_tuple

    artifact_cache_key = (
        resolved_path,
        criteria_cache_key(criteria),
        artifact_key or "",
    )
    if artifact_cache_key not in _ARTIFACT_CACHE:
        extra = extra_builder(state_tuple) if extra_builder else None
        write_layer_results_json(current_file, criteria, state_tuple, extra=extra)
        write_default_layer_visualizations(current_file, state_tuple)
        if artifact_writer is not None:
            artifact_writer(state_tuple)
        _ARTIFACT_CACHE.add(artifact_cache_key)

    return state_tuple
