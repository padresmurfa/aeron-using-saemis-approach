#!/usr/bin/env python3
"""Deterministic proto-tectonic regime simulation for Aeron."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Callable, Iterable, Sequence

try:
    from .world_building_paths import step_output_path
    from .world_building_support import load_pipeline_module, materialize_layer_states
except ImportError:
    from world_building_paths import step_output_path  # type: ignore
    from world_building_support import load_pipeline_module, materialize_layer_states  # type: ignore

planet = load_pipeline_module(__package__, __file__, "01_planet")
surface_temperature = load_pipeline_module(
    __package__, __file__, "05_surface_temperature"
)

getcontext().prec = 50

TEMP_RIGIDITY_THRESHOLD_C = Decimal("220")
THERMAL_STRESS_SATURATION_C = Decimal("30")
VALIDATION_STEP_YEARS = 100_000_000
DEFAULT_SURFACE_GRID_RESOLUTION = "72x36"
SURFACE_GRID_MODEL = "coarse_lat_lon_cell_field"

CRUST_STABILITY_SCORES = {
    "disrupted": Decimal("0.05"),
    "fragile": Decimal("0.35"),
    "stressed": Decimal("0.70"),
    "stable": Decimal("0.95"),
}

LATITUDINAL_CONTRAST_SCORES = {
    "low": Decimal("0.35"),
    "moderate": Decimal("0.65"),
    "high": Decimal("0.85"),
}

SURFACE_LIQUID_MOBILITY_SCORES = {
    "absent": Decimal("0.05"),
    "transient": Decimal("0.45"),
    "frozen": Decimal("0.20"),
    "stable": Decimal("0.85"),
}

LATITUDINAL_CONTRAST_AMPLITUDES = {
    "low": 0.08,
    "moderate": 0.16,
    "high": 0.24,
}

ZONE_WAVE_COUNTS = {
    "global_foundering_scars": 3,
    "cooling_fracture_belts": 4,
    "shield_breaks": 5,
    "mobile_belts": 6,
    "proto_rift_corridors": 4,
    "failed_rifts": 3,
    "linear_spreading_ridges": 6,
    "foundering_basins": 3,
    "localized_delamination_sinks": 4,
    "hydrated_recycling_arcs": 6,
}


@dataclass(frozen=True)
class ProtoTectonicsState:
    step_index: int
    age_years: int
    radius_km: Decimal
    mean_surface_temp_c: Decimal
    equator_to_pole_delta_c: Decimal
    stable_crust_fraction: Decimal
    crust_stability_state: str
    latitudinal_contrast: str
    surface_liquid_state: str
    thermal_cycling_amplitude_c: Decimal
    thermal_cycling_state: str
    surface_temperature_regime: str
    lithosphere_rigidity_index: Decimal
    fracture_potential_index: Decimal
    plate_mobility_index: Decimal
    rigid_enough_to_fracture: str
    plates_exist: str
    tectonic_regime: str
    major_fracture_zones: str
    spreading_zones: str
    recycling_zones: str
    world_class: str


@dataclass(frozen=True)
class ProtoTectonicCell:
    cell_id: str
    latitude_index: int
    longitude_index: int
    latitude_degrees: float
    longitude_degrees: float
    lithosphere_rigidity_index: float
    thermal_stress_index: float
    fracture_susceptibility_index: float
    proto_rift_tendency_index: float
    upwelling_influence_index: float
    recycling_tendency_index: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's proto-tectonic regime by ticking the surface "
            "temperature layer and deriving first-order fracture and plate behavior."
        )
    )
    parser.add_argument(
        "--step-years",
        type=int,
        default=1_000_000,
        help=(
            "Fixed iteration step in years. Must evenly divide the full "
            "5.4 billion year simulation span. Default: %(default)s."
        ),
    )
    parser.add_argument(
        "--surface-grid-resolution",
        default=DEFAULT_SURFACE_GRID_RESOLUTION,
        help=(
            "Coarse surface grid resolution as <longitude>x<latitude> cells for "
            "the proto-tectonic field map. Default: "
            f"{DEFAULT_SURFACE_GRID_RESOLUTION}."
        ),
    )
    return parser.parse_args()


def clamp_unit_interval(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")
    if value > Decimal("1"):
        return Decimal("1")
    return value


def clamp_unit_float(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def parse_surface_grid_resolution(spec: str) -> tuple[int, int]:
    normalized = spec.lower().strip()
    if "x" not in normalized:
        raise ValueError(
            "Surface grid resolution must be formatted as <longitude>x<latitude>, "
            f"for example {DEFAULT_SURFACE_GRID_RESOLUTION}."
        )
    lon_text, lat_text = normalized.split("x", maxsplit=1)
    try:
        lon_cells = int(lon_text)
        lat_cells = int(lat_text)
    except ValueError as exc:
        raise ValueError(
            "Surface grid resolution values must be whole numbers, for example "
            f"{DEFAULT_SURFACE_GRID_RESOLUTION}."
        ) from exc
    if lon_cells <= 0 or lat_cells <= 0:
        raise ValueError("Surface grid resolution must use positive cell counts.")
    return lon_cells, lat_cells


def surface_grid_output_path(current_file: str) -> Path:
    return step_output_path(current_file, "surface_fields.png")


def surface_grid_resolution_label(resolution: tuple[int, int]) -> str:
    lon_cells, lat_cells = resolution
    return f"{lon_cells}x{lat_cells}"


def surface_grid_artifact_key(resolution: tuple[int, int]) -> str:
    return f"surface_grid:{surface_grid_resolution_label(resolution)}"


def temperature_rigidity_score_at(mean_surface_temp_c: Decimal) -> Decimal:
    return clamp_unit_interval(
        (TEMP_RIGIDITY_THRESHOLD_C - mean_surface_temp_c) / TEMP_RIGIDITY_THRESHOLD_C
    )


def crust_stability_score_at(crust_stability_state: str) -> Decimal:
    return CRUST_STABILITY_SCORES[crust_stability_state]


def latitudinal_contrast_score_at(latitudinal_contrast: str) -> Decimal:
    return LATITUDINAL_CONTRAST_SCORES[latitudinal_contrast]


def surface_liquid_mobility_score_at(surface_liquid_state: str) -> Decimal:
    return SURFACE_LIQUID_MOBILITY_SCORES[surface_liquid_state]


def thermal_stress_score_at(thermal_cycling_amplitude_c: Decimal) -> Decimal:
    return clamp_unit_interval(
        thermal_cycling_amplitude_c / THERMAL_STRESS_SATURATION_C
    )


def lithosphere_rigidity_index_at(
    state: surface_temperature.SurfaceTemperatureState,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.45") * state.stable_crust_fraction)
        + (
            Decimal("0.35")
            * temperature_rigidity_score_at(state.mean_surface_temp_c)
        )
        + (
            Decimal("0.20")
            * crust_stability_score_at(state.crust_stability_state)
        )
    )


def fracture_potential_index_at(
    state: surface_temperature.SurfaceTemperatureState,
    lithosphere_rigidity_index: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.40") * lithosphere_rigidity_index)
        + (
            Decimal("0.35")
            * thermal_stress_score_at(state.thermal_cycling_amplitude_c)
        )
        + (
            Decimal("0.25")
            * latitudinal_contrast_score_at(state.latitudinal_contrast)
        )
    )


def plate_mobility_index_at(
    state: surface_temperature.SurfaceTemperatureState,
    lithosphere_rigidity_index: Decimal,
    fracture_potential_index: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.35") * lithosphere_rigidity_index)
        + (Decimal("0.30") * fracture_potential_index)
        + (
            Decimal("0.20")
            * surface_liquid_mobility_score_at(state.surface_liquid_state)
        )
        + (
            Decimal("0.15")
            * temperature_rigidity_score_at(state.mean_surface_temp_c)
        )
    )


def rigid_enough_to_fracture_at(
    lithosphere_rigidity_index: Decimal, fracture_potential_index: Decimal
) -> str:
    if (
        lithosphere_rigidity_index >= Decimal("0.50")
        and fracture_potential_index >= Decimal("0.45")
    ):
        return "yes"
    return "no"


def tectonic_regime_at(
    state: surface_temperature.SurfaceTemperatureState,
    lithosphere_rigidity_index: Decimal,
    fracture_potential_index: Decimal,
    plate_mobility_index: Decimal,
) -> str:
    if state.surface_temperature_regime == "hot_volcanic_rock":
        return "episodic_overturn"
    if (
        state.crust_stability_state in {"disrupted", "fragile"}
        and state.thermal_cycling_state in {"moderate", "high", "extreme"}
    ):
        return "episodic_overturn"
    if (
        lithosphere_rigidity_index >= Decimal("0.70")
        and fracture_potential_index >= Decimal("0.55")
        and plate_mobility_index >= Decimal("0.68")
        and state.stable_crust_fraction >= Decimal("0.60")
        and state.surface_liquid_state == "stable"
    ):
        return "plate_like"
    return "stagnant_lid"


def plates_exist_at(tectonic_regime: str) -> str:
    return "yes" if tectonic_regime == "plate_like" else "no"


def zone_prefix_at(latitudinal_contrast: str) -> str:
    if latitudinal_contrast == "high":
        return "equatorial_and_subpolar"
    if latitudinal_contrast == "moderate":
        return "equatorial_to_midlatitude"
    return "distributed_global"


def major_fracture_zones_at(
    state: surface_temperature.SurfaceTemperatureState, tectonic_regime: str
) -> str:
    prefix = zone_prefix_at(state.latitudinal_contrast)
    if tectonic_regime == "episodic_overturn":
        if state.surface_temperature_regime == "hot_volcanic_rock":
            return "global_foundering_scars"
        return f"{prefix}_cooling_fracture_belts"
    if tectonic_regime == "stagnant_lid":
        return f"{prefix}_shield_breaks"
    return f"{prefix}_mobile_belts"


def spreading_zones_at(
    state: surface_temperature.SurfaceTemperatureState, tectonic_regime: str
) -> str:
    prefix = zone_prefix_at(state.latitudinal_contrast)
    if tectonic_regime == "episodic_overturn":
        return f"{prefix}_proto_rift_corridors"
    if tectonic_regime == "stagnant_lid":
        return f"{prefix}_isolated_failed_rifts"
    return f"{prefix}_linear_spreading_ridges"


def recycling_zones_at(
    state: surface_temperature.SurfaceTemperatureState, tectonic_regime: str
) -> str:
    prefix = zone_prefix_at(state.latitudinal_contrast)
    if tectonic_regime == "episodic_overturn":
        return f"{prefix}_foundering_basins"
    if tectonic_regime == "stagnant_lid":
        return f"{prefix}_localized_delamination_sinks"
    return f"{prefix}_hydrated_recycling_arcs"


def proto_tectonics_state_from_surface_temperature_state(
    base_state: surface_temperature.SurfaceTemperatureState,
) -> ProtoTectonicsState:
    lithosphere_rigidity_index = lithosphere_rigidity_index_at(base_state)
    fracture_potential_index = fracture_potential_index_at(
        base_state, lithosphere_rigidity_index
    )
    plate_mobility_index = plate_mobility_index_at(
        base_state, lithosphere_rigidity_index, fracture_potential_index
    )
    tectonic_regime = tectonic_regime_at(
        base_state,
        lithosphere_rigidity_index,
        fracture_potential_index,
        plate_mobility_index,
    )
    return ProtoTectonicsState(
        step_index=base_state.step_index,
        age_years=base_state.age_years,
        radius_km=base_state.radius_km,
        mean_surface_temp_c=base_state.mean_surface_temp_c,
        equator_to_pole_delta_c=base_state.equator_to_pole_delta_c,
        stable_crust_fraction=base_state.stable_crust_fraction,
        crust_stability_state=base_state.crust_stability_state,
        latitudinal_contrast=base_state.latitudinal_contrast,
        surface_liquid_state=base_state.surface_liquid_state,
        thermal_cycling_amplitude_c=base_state.thermal_cycling_amplitude_c,
        thermal_cycling_state=base_state.thermal_cycling_state,
        surface_temperature_regime=base_state.surface_temperature_regime,
        lithosphere_rigidity_index=lithosphere_rigidity_index,
        fracture_potential_index=fracture_potential_index,
        plate_mobility_index=plate_mobility_index,
        rigid_enough_to_fracture=rigid_enough_to_fracture_at(
            lithosphere_rigidity_index, fracture_potential_index
        ),
        plates_exist=plates_exist_at(tectonic_regime),
        tectonic_regime=tectonic_regime,
        major_fracture_zones=major_fracture_zones_at(base_state, tectonic_regime),
        spreading_zones=spreading_zones_at(base_state, tectonic_regime),
        recycling_zones=recycling_zones_at(base_state, tectonic_regime),
        world_class=base_state.world_class,
    )


def latitude_focus_weight(zone_prefix: str, latitude_degrees: float) -> float:
    absolute_latitude = abs(latitude_degrees)
    equatorial = math.exp(-((absolute_latitude - 10.0) / 18.0) ** 2)
    midlatitude = math.exp(-((absolute_latitude - 35.0) / 16.0) ** 2)
    subpolar = math.exp(-((absolute_latitude - 62.0) / 12.0) ** 2)

    if zone_prefix == "equatorial_and_subpolar":
        return clamp_unit_float((0.55 * equatorial) + (0.65 * subpolar))
    if zone_prefix == "equatorial_to_midlatitude":
        return clamp_unit_float((0.60 * equatorial) + (0.50 * midlatitude))
    return clamp_unit_float(0.52 + (0.35 * math.cos(math.radians(latitude_degrees)) ** 2))


def zone_suffix(zone_label: str) -> str:
    for suffix in ZONE_WAVE_COUNTS:
        if zone_label.endswith(suffix):
            return suffix
    return "mobile_belts"


def longitudinal_wave(zone_label: str, latitude_degrees: float, longitude_degrees: float) -> float:
    wave_count = ZONE_WAVE_COUNTS[zone_suffix(zone_label)]
    phase = math.radians(latitude_degrees * 0.9)
    return 0.5 * (math.sin((wave_count * math.radians(longitude_degrees)) + phase) + 1.0)


def surface_grid_coordinates(resolution: tuple[int, int]) -> tuple[list[float], list[float]]:
    lon_cells, lat_cells = resolution
    longitudes = [
        -180.0 + ((index + 0.5) * 360.0 / lon_cells) for index in range(lon_cells)
    ]
    latitudes = [
        -90.0 + ((index + 0.5) * 180.0 / lat_cells) for index in range(lat_cells)
    ]
    return longitudes, latitudes


def build_proto_tectonic_surface_cells(
    state: ProtoTectonicsState, resolution: tuple[int, int]
) -> tuple[ProtoTectonicCell, ...]:
    """Build a coarse deterministic surface cell field for proto-tectonics.

    This is the first layer that owns honest coarse surface structure. The cell
    fields are derived from the layer's real global indices and named zone
    patterns: latitudinal contrast sets the broad belt geometry, while the
    fracture/spreading/recycling labels choose deterministic harmonic alignment
    along longitude. The result is a reusable coarse substrate, not a claim of
    final plate geometry.
    """

    longitudes, latitudes = surface_grid_coordinates(resolution)
    zone_prefix = zone_prefix_at(state.latitudinal_contrast)
    global_rigidity = float(state.lithosphere_rigidity_index)
    global_fracture = float(state.fracture_potential_index)
    global_mobility = float(state.plate_mobility_index)
    global_thermal_stress = float(thermal_stress_score_at(state.thermal_cycling_amplitude_c))
    liquid_mobility = float(surface_liquid_mobility_score_at(state.surface_liquid_state))
    contrast_amplitude = LATITUDINAL_CONTRAST_AMPLITUDES[state.latitudinal_contrast]

    cells: list[ProtoTectonicCell] = []
    for latitude_index, latitude in enumerate(latitudes):
        polar_bias = abs(math.sin(math.radians(latitude)))
        latitude_focus = latitude_focus_weight(zone_prefix, latitude)
        for longitude_index, longitude in enumerate(longitudes):
            fracture_wave = longitudinal_wave(
                state.major_fracture_zones, latitude, longitude
            )
            spreading_wave = longitudinal_wave(state.spreading_zones, latitude, longitude)
            recycling_wave = longitudinal_wave(state.recycling_zones, latitude, longitude)

            upwelling_focus = clamp_unit_float(
                (0.55 * latitude_focus)
                + (0.45 * spreading_wave)
            )
            upwelling_influence = clamp_unit_float(
                ((0.50 * (1.0 - global_rigidity)) + (0.50 * global_mobility))
                * (0.62 + (0.38 * upwelling_focus))
            )

            lithosphere_rigidity = clamp_unit_float(
                global_rigidity
                + (contrast_amplitude * 0.45 * polar_bias)
                - (0.22 * upwelling_influence)
            )

            thermal_stress = clamp_unit_float(
                (global_thermal_stress * (0.72 + (0.28 * latitude_focus)))
                + (contrast_amplitude * (0.25 + (0.75 * polar_bias)))
                - (0.08 * liquid_mobility)
            )

            fracture_susceptibility = clamp_unit_float(
                (0.58 * global_fracture)
                + (0.20 * thermal_stress)
                + (0.14 * latitude_focus)
                + (0.08 * fracture_wave)
                - (0.10 * max(0.0, lithosphere_rigidity - 0.82))
            )

            proto_rift_tendency = clamp_unit_float(
                ((0.55 * global_fracture) + (0.45 * global_mobility))
                * (0.58 + (0.42 * spreading_wave * latitude_focus))
            )

            recycling_tendency = clamp_unit_float(
                ((0.48 * global_mobility) + (0.30 * lithosphere_rigidity) + (0.22 * liquid_mobility))
                * (0.56 + (0.44 * recycling_wave * latitude_focus))
            )

            cells.append(
                ProtoTectonicCell(
                    cell_id=f"lat_{latitude_index:02d}_lon_{longitude_index:03d}",
                    latitude_index=latitude_index,
                    longitude_index=longitude_index,
                    latitude_degrees=latitude,
                    longitude_degrees=longitude,
                    lithosphere_rigidity_index=lithosphere_rigidity,
                    thermal_stress_index=thermal_stress,
                    fracture_susceptibility_index=fracture_susceptibility,
                    proto_rift_tendency_index=proto_rift_tendency,
                    upwelling_influence_index=upwelling_influence,
                    recycling_tendency_index=recycling_tendency,
                )
            )

    return tuple(cells)


def surface_field_statistics(
    cells: Sequence[ProtoTectonicCell],
    getter: Callable[[ProtoTectonicCell], float],
) -> dict[str, float]:
    values = [getter(cell) for cell in cells]
    if not values:
        return {"min": 0.0, "mean": 0.0, "max": 0.0}
    return {
        "min": min(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def build_surface_grid_extra(
    states: Sequence[ProtoTectonicsState],
    resolution: tuple[int, int],
) -> dict[str, object]:
    lon_cells, lat_cells = resolution
    if not states:
        return {
            "surface_grid": {
                "model": SURFACE_GRID_MODEL,
                "geometry": "spherical_lat_lon_cells",
                "resolution": {
                    "longitude_cells": lon_cells,
                    "latitude_cells": lat_cells,
                    "cell_count": 0,
                },
                "cells": [],
            }
        }

    final_state = states[-1]
    cells = build_proto_tectonic_surface_cells(final_state, resolution)
    return {
        "surface_grid": {
            "model": SURFACE_GRID_MODEL,
            "geometry": "spherical_lat_lon_cells",
            "resolution": {
                "longitude_cells": lon_cells,
                "latitude_cells": lat_cells,
                "cell_count": len(cells),
            },
            "present_day_regime": final_state.tectonic_regime,
            "named_zone_patterns": {
                "major_fracture_zones": final_state.major_fracture_zones,
                "spreading_zones": final_state.spreading_zones,
                "recycling_zones": final_state.recycling_zones,
            },
            "cell_fields": [
                "lithosphere_rigidity_index",
                "thermal_stress_index",
                "fracture_susceptibility_index",
                "proto_rift_tendency_index",
                "upwelling_influence_index",
                "recycling_tendency_index",
            ],
            "field_statistics": {
                "lithosphere_rigidity_index": surface_field_statistics(
                    cells, lambda cell: cell.lithosphere_rigidity_index
                ),
                "thermal_stress_index": surface_field_statistics(
                    cells, lambda cell: cell.thermal_stress_index
                ),
                "fracture_susceptibility_index": surface_field_statistics(
                    cells, lambda cell: cell.fracture_susceptibility_index
                ),
                "proto_rift_tendency_index": surface_field_statistics(
                    cells, lambda cell: cell.proto_rift_tendency_index
                ),
                "upwelling_influence_index": surface_field_statistics(
                    cells, lambda cell: cell.upwelling_influence_index
                ),
                "recycling_tendency_index": surface_field_statistics(
                    cells, lambda cell: cell.recycling_tendency_index
                ),
            },
            "cells": cells,
        }
    }


def field_grid(
    cells: Sequence[ProtoTectonicCell],
    resolution: tuple[int, int],
    getter: Callable[[ProtoTectonicCell], float],
) -> list[list[float]]:
    lon_cells, lat_cells = resolution
    grid = [[0.0 for _ in range(lon_cells)] for _ in range(lat_cells)]
    for cell in cells:
        grid[cell.latitude_index][cell.longitude_index] = getter(cell)
    return grid


def simulate(
    criteria: planet.SimulationCriteria,
    surface_grid_resolution: tuple[int, int] | None = None,
) -> Iterable[ProtoTectonicsState]:
    resolution = surface_grid_resolution or parse_surface_grid_resolution(
        DEFAULT_SURFACE_GRID_RESOLUTION
    )

    def build_states() -> Iterable[ProtoTectonicsState]:
        for base_state in surface_temperature.simulate(criteria):
            yield proto_tectonics_state_from_surface_temperature_state(base_state)

    return materialize_layer_states(
        __file__,
        criteria,
        build_states,
        extra_builder=lambda states: build_surface_grid_extra(states, resolution),
        artifact_key=surface_grid_artifact_key(resolution),
    )


def first_fracture_capable_state(
    states: Iterable[ProtoTectonicsState],
) -> ProtoTectonicsState | None:
    for state in states:
        if state.rigid_enough_to_fracture == "yes":
            return state
    return None


def first_plate_like_state(
    states: Iterable[ProtoTectonicsState],
) -> ProtoTectonicsState | None:
    for state in states:
        if state.tectonic_regime == "plate_like":
            return state
    return None


def write_surface_field_map_png(
    state: ProtoTectonicsState,
    current_file: str,
    resolution: tuple[int, int],
) -> Path:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.colors import Normalize
    except ImportError as exc:  # pragma: no cover - import-time dependency guard
        raise ImportError(
            "Proto-tectonic surface field visualization requires matplotlib. "
            "Install dependencies with `python3 -m pip install -r requirements.txt`."
        ) from exc

    cells = build_proto_tectonic_surface_cells(state, resolution)
    field_specs = (
        (
            "Lithosphere Rigidity",
            lambda cell: cell.lithosphere_rigidity_index,
        ),
        (
            "Thermal Stress",
            lambda cell: cell.thermal_stress_index,
        ),
        (
            "Fracture Susceptibility",
            lambda cell: cell.fracture_susceptibility_index,
        ),
        (
            "Proto-Rift Tendency",
            lambda cell: cell.proto_rift_tendency_index,
        ),
        (
            "Upwelling Influence",
            lambda cell: cell.upwelling_influence_index,
        ),
        (
            "Recycling Tendency",
            lambda cell: cell.recycling_tendency_index,
        ),
    )

    fig, axes = plt.subplots(2, 3, figsize=(15.2, 8.9), facecolor="#f6f1e8")
    axes_flat = list(axes.flat)
    cmap = plt.get_cmap("viridis")
    norm = Normalize(vmin=0.0, vmax=1.0)
    extent = (-180, 180, -90, 90)

    image = None
    for axis, (title, getter) in zip(axes_flat, field_specs):
        grid = field_grid(cells, resolution, getter)
        axis.set_facecolor("#fffdf8")
        image = axis.imshow(
            grid,
            origin="lower",
            extent=extent,
            aspect="auto",
            cmap=cmap,
            norm=norm,
            interpolation="nearest",
        )
        axis.set_title(title, color="#1f2937", fontsize=11.5, pad=8)
        axis.set_xticks([-180, -90, 0, 90, 180])
        axis.set_yticks([-90, -45, 0, 45, 90])
        axis.tick_params(colors="#6b7280", labelsize=9)
        axis.grid(color="#d7d2c8", linewidth=0.5, alpha=0.22)
        for spine in axis.spines.values():
            spine.set_color("#d7d2c8")

    for axis in axes[1, :]:
        axis.set_xlabel("Longitude (degrees)", color="#1f2937", fontsize=10.5)
    for axis in axes[:, 0]:
        axis.set_ylabel("Latitude (degrees)", color="#1f2937", fontsize=10.5)

    assert image is not None
    colorbar = fig.colorbar(
        image,
        ax=axes_flat,
        orientation="vertical",
        fraction=0.03,
        pad=0.02,
    )
    colorbar.set_label("Relative Field Strength", color="#1f2937")
    colorbar.ax.tick_params(colors="#6b7280")

    lon_cells, lat_cells = resolution
    fig.suptitle(
        "06 Proto-Tectonics: Coarse Surface Cell Fields",
        x=0.075,
        y=0.985,
        ha="left",
        color="#1f2937",
        fontsize=19,
    )
    fig.text(
        0.075,
        0.945,
        (
            f"Present-state deterministic {lon_cells}x{lat_cells} cell grid. "
            f"Regime: {state.tectonic_regime.replace('_', ' ').title()}."
        ),
        ha="left",
        va="top",
        fontsize=11,
        color="#6b7280",
    )
    fig.text(
        0.075,
        0.02,
        (
            "This is the first honest coarse surface geometry in the pipeline. "
            "Cell fields are derived from the layer's real global indices plus "
            "named fracture, spreading, and recycling zone patterns. They are "
            "not yet discrete plate polygons."
        ),
        ha="left",
        va="bottom",
        fontsize=10,
        color="#6b7280",
    )
    fig.subplots_adjust(left=0.06, right=0.92, top=0.89, bottom=0.12, wspace=0.18, hspace=0.28)

    output_path = surface_grid_output_path(current_file)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output_path


def validate_model() -> None:
    surface_temperature.validate_model()
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria))
    initial_state = states[0]
    present_state = states[-1]
    first_fracture_state = first_fracture_capable_state(states)
    first_plate_state = first_plate_like_state(states)

    if initial_state.tectonic_regime != "episodic_overturn":
        raise ValueError("Proto-tectonics should begin in episodic overturn.")
    if first_fracture_state is None:
        raise ValueError("The lithosphere must become rigid enough to fracture.")
    if present_state.rigid_enough_to_fracture != "yes":
        raise ValueError("Present-day Aeron should be rigid enough to fracture.")
    if first_plate_state is None:
        raise ValueError("Plate-like behavior must emerge within the simulation span.")
    if present_state.tectonic_regime != "plate_like":
        raise ValueError("Present-day Aeron should land in a plate-like regime.")


def print_input_criteria(
    criteria: planet.SimulationCriteria, surface_grid_resolution: tuple[int, int]
) -> None:
    lon_cells, lat_cells = surface_grid_resolution
    fields = [
        ("layer_name", "proto_tectonic_regime"),
        ("surface_temperature_source", "05_surface_temperature.py"),
        ("early_atmosphere_source", "04_early_atmosphere.py"),
        ("primary_crust_source", "03_primary_crust.py"),
        ("interior_source", "02_interior.py"),
        ("planet_source", "01_planet.py"),
        ("coupled_surface_temperature_layer", "true"),
        ("coupled_atmosphere_layer", "true"),
        ("coupled_primary_crust_layer", "true"),
        ("coupled_interior_layer", "true"),
        ("coupled_bulk_layer", "true"),
        ("deterministic", "true"),
        ("total_duration_years", str(criteria.total_duration_years)),
        (
            "total_duration_gyr",
            planet.format_decimal(
                Decimal(criteria.total_duration_years) / planet.YEARS_PER_GYR, 6
            ),
        ),
        ("step_years", str(criteria.step_years)),
        (
            "step_myr",
            planet.format_decimal(Decimal(criteria.step_years) / planet.YEARS_PER_MYR, 6),
        ),
        ("rigidity_model", "stable_crust_plus_temperature_plus_crust_state"),
        ("fracture_model", "rigidity_plus_thermal_stress_plus_latitudinal_contrast"),
        ("regime_model", "episodic_overturn_to_stagnant_lid_to_plate_like"),
        ("zone_model", "latitudinal_belt_patterns"),
        ("surface_grid_model", SURFACE_GRID_MODEL),
        ("surface_grid_geometry", "spherical_lat_lon_cells"),
        ("surface_grid_resolution", f"{lon_cells}x{lat_cells}"),
        ("surface_cell_fields", "rigidity, thermal_stress, fracture, proto_rift, upwelling, recycling"),
        (
            "dynamic_fields",
            "equator_to_pole_delta_c, latitudinal_contrast, "
            "surface_temperature_regime, lithosphere_rigidity_index, "
            "fracture_potential_index, plate_mobility_index, "
            "rigid_enough_to_fracture, plates_exist, tectonic_regime, "
            "major_fracture_zones, spreading_zones, recycling_zones",
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print("INPUT CRITERIA")
    print("==============")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")
    print()


def print_table(states: Sequence[ProtoTectonicsState]) -> None:
    headers = (
        ("step", 8),
        ("age_myr", 12),
        ("temp_c", 10),
        ("liquids", 10),
        ("crust", 10),
        ("rigid_ix", 9),
        ("fract_ix", 9),
        ("mob_ix", 8),
        ("fracture", 9),
        ("plates", 8),
        ("regime", 18),
        ("major_fractures", 30),
        ("spreading_zones", 32),
        ("recycling_zones", 34),
    )

    header_line = " ".join(f"{label:>{width}}" for label, width in headers)
    divider_line = " ".join("-" * width for _, width in headers)
    print(header_line)
    print(divider_line)

    for state in states:
        age_myr = planet.format_decimal(
            Decimal(state.age_years) / planet.YEARS_PER_MYR, 3
        )
        print(
            f"{state.step_index:>8d} "
            f"{age_myr:>12} "
            f"{planet.format_decimal(state.mean_surface_temp_c, 3):>10} "
            f"{state.surface_liquid_state:>10} "
            f"{state.crust_stability_state:>10} "
            f"{planet.format_decimal(state.lithosphere_rigidity_index, 3):>9} "
            f"{planet.format_decimal(state.fracture_potential_index, 3):>9} "
            f"{planet.format_decimal(state.plate_mobility_index, 3):>8} "
            f"{state.rigid_enough_to_fracture:>9} "
            f"{state.plates_exist:>8} "
            f"{state.tectonic_regime:>18} "
            f"{state.major_fracture_zones:>30} "
            f"{state.spreading_zones:>32} "
            f"{state.recycling_zones:>34}"
        )


def print_present_day_summary(
    states: Sequence[ProtoTectonicsState],
    surface_grid_resolution: tuple[int, int],
) -> None:
    final_state = states[-1]
    first_fracture_state = first_fracture_capable_state(states)
    first_plate_state = first_plate_like_state(states)
    surface_cells = build_proto_tectonic_surface_cells(
        final_state, surface_grid_resolution
    )

    assert first_fracture_state is not None
    assert first_plate_state is not None

    fields = [
        ("world_class", final_state.world_class),
        (
            "lithosphere_rigidity_index",
            planet.format_decimal(final_state.lithosphere_rigidity_index, 6),
        ),
        (
            "fracture_potential_index",
            planet.format_decimal(final_state.fracture_potential_index, 6),
        ),
        (
            "plate_mobility_index",
            planet.format_decimal(final_state.plate_mobility_index, 6),
        ),
        ("rigid_enough_to_fracture", final_state.rigid_enough_to_fracture),
        ("plates_exist", final_state.plates_exist),
        ("tectonic_regime", final_state.tectonic_regime),
        ("major_fracture_zones", final_state.major_fracture_zones),
        ("spreading_zones", final_state.spreading_zones),
        ("recycling_zones", final_state.recycling_zones),
        ("surface_grid_model", SURFACE_GRID_MODEL),
        ("surface_grid_geometry", "spherical_lat_lon_cells"),
        (
            "surface_grid_resolution",
            surface_grid_resolution_label(surface_grid_resolution),
        ),
        ("surface_cell_count", str(len(surface_cells))),
        ("first_fracture_step", str(first_fracture_state.step_index)),
        (
            "first_fracture_age_myr",
            planet.format_decimal(
                Decimal(first_fracture_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
        ("first_plate_like_step", str(first_plate_state.step_index)),
        (
            "first_plate_like_age_myr",
            planet.format_decimal(
                Decimal(first_plate_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT PROTO-TECTONIC SUMMARY")
    print("==============================")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")


def main() -> int:
    args = parse_args()
    try:
        criteria = planet.build_criteria(args.step_years)
        surface_grid_resolution = parse_surface_grid_resolution(
            args.surface_grid_resolution
        )
        validate_model()
    except ValueError as exc:
        raise SystemExit(str(exc))

    states = simulate(criteria, surface_grid_resolution)
    if not states:
        raise SystemExit("Proto-tectonics simulation produced no timestep states.")

    print_input_criteria(criteria, surface_grid_resolution)
    print_table(states)
    print_present_day_summary(states, surface_grid_resolution)

    try:
        write_surface_field_map_png(states[-1], __file__, surface_grid_resolution)
    except (ImportError, OSError, ValueError) as exc:
        raise SystemExit(
            f"Failed to write proto-tectonic surface field visualization: {exc}"
        ) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
