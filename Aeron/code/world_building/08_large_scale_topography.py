#!/usr/bin/env python3
"""Deterministic large-scale topography generation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    from .world_building_support import load_pipeline_module, materialize_layer_states
    from .world_building_surface import (
        PlanetSurface,
        boundary_records,
        clamp_unit_interval as clamp_unit_interval_array,
        clear_frame_directory,
        diffuse_scalar,
        frame_output_dir,
        frame_sample_indices,
        gradient_magnitude,
        load_planet_surface,
        neighbor_mean,
        planet_surface_from_plate_surface_model,
        save_planet_surface,
        subdivide_lat_lon_surface,
        subdivided_surface_grid_resolution,
        surface_json_payload,
        surface_state_output_path,
        terrain_class_from_fields,
        visualization_output_path,
    )
except ImportError:
    from world_building_support import load_pipeline_module, materialize_layer_states  # type: ignore
    from world_building_surface import (  # type: ignore
        PlanetSurface,
        boundary_records,
        clamp_unit_interval as clamp_unit_interval_array,
        clear_frame_directory,
        diffuse_scalar,
        frame_output_dir,
        frame_sample_indices,
        gradient_magnitude,
        load_planet_surface,
        neighbor_mean,
        planet_surface_from_plate_surface_model,
        save_planet_surface,
        subdivide_lat_lon_surface,
        subdivided_surface_grid_resolution,
        surface_json_payload,
        surface_state_output_path,
        terrain_class_from_fields,
        visualization_output_path,
    )

plate_system = load_pipeline_module(__package__, __file__, "07_plate_system")
planet = load_pipeline_module(__package__, __file__, "01_planet")
surface_temperature = load_pipeline_module(__package__, __file__, "05_surface_temperature")

getcontext().prec = 50

VALIDATION_STEP_YEARS = 100_000_000
FRAME_DIRECTORY_NAME = "08_topography"


@dataclass(frozen=True)
class TopographyFeatureTemplate:
    feature_id: str
    feature_type: str
    source_region_id: str
    driver_kind: str
    tectonic_driver: str


@dataclass(frozen=True)
class TopographyFeatureState:
    feature_id: str
    feature_type: str
    source_region_id: str
    source_region_status: str
    maturity_state: str
    tectonic_driver: str
    relief_m: Decimal
    area_fraction: Decimal
    area_km2: Decimal


@dataclass(frozen=True)
class LargeScaleTopographyState:
    step_index: int
    age_years: int
    radius_km: Decimal
    tectonic_regime: str
    proto_continent_fraction: Decimal
    ocean_basin_fraction: Decimal
    highest_relief_m: Decimal
    deepest_basin_m: Decimal
    relief_contrast_m: Decimal
    topography_state: str
    feature_count: int
    features: tuple[TopographyFeatureState, ...]
    world_class: str


FEATURE_TEMPLATES = (
    TopographyFeatureTemplate(
        feature_id="boreal_proto_continent",
        feature_type="proto_continent",
        source_region_id="boreal_keel_region",
        driver_kind="continent",
        tectonic_driver="collision_and_recycling",
    ),
    TopographyFeatureTemplate(
        feature_id="austral_proto_continent",
        feature_type="proto_continent",
        source_region_id="austral_collision_region",
        driver_kind="minor_continent",
        tectonic_driver="collision_and_accretion",
    ),
    TopographyFeatureTemplate(
        feature_id="boreal_highlands",
        feature_type="highlands",
        source_region_id="boreal_keel_region",
        driver_kind="highland",
        tectonic_driver="crustal_thickening",
    ),
    TopographyFeatureTemplate(
        feature_id="western_pelagic_basin",
        feature_type="ocean_basin",
        source_region_id="west_equatorial_rift_region",
        driver_kind="basin",
        tectonic_driver="spreading_and_subsidence",
    ),
    TopographyFeatureTemplate(
        feature_id="southern_pelagic_basin",
        feature_type="ocean_basin",
        source_region_id="southern_spreading_region",
        driver_kind="basin",
        tectonic_driver="spreading_and_subsidence",
    ),
    TopographyFeatureTemplate(
        feature_id="western_spreading_ridge",
        feature_type="ridge",
        source_region_id="west_equatorial_rift_region",
        driver_kind="ridge",
        tectonic_driver="spreading",
    ),
    TopographyFeatureTemplate(
        feature_id="southern_spreading_ridge",
        feature_type="ridge",
        source_region_id="southern_spreading_region",
        driver_kind="ridge",
        tectonic_driver="spreading",
    ),
    TopographyFeatureTemplate(
        feature_id="boreal_volcanic_arc",
        feature_type="volcanic_arc",
        source_region_id="boreal_keel_region",
        driver_kind="arc",
        tectonic_driver="recycling",
    ),
    TopographyFeatureTemplate(
        feature_id="austral_uplift_belt",
        feature_type="uplift",
        source_region_id="austral_collision_region",
        driver_kind="uplift",
        tectonic_driver="collision",
    ),
    TopographyFeatureTemplate(
        feature_id="eastern_rift_system",
        feature_type="rift",
        source_region_id="east_equatorial_shear_region",
        driver_kind="rift",
        tectonic_driver="transform_and_extension",
    ),
    TopographyFeatureTemplate(
        feature_id="pelagic_lowland_troughs",
        feature_type="lowlands",
        source_region_id="pelagic_transform_region",
        driver_kind="lowland",
        tectonic_driver="transform_and_basin_subsidence",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's large-scale topography by ticking the plate-system "
            "layer and deriving first-order planetary relief features."
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
        default=plate_system.DEFAULT_SURFACE_GRID_RESOLUTION,
        help=(
            "Coarse surface grid resolution as <longitude>x<latitude> cells for "
            "the inherited plate geometry. Default: "
            f"{plate_system.DEFAULT_SURFACE_GRID_RESOLUTION}."
        ),
    )
    return parser.parse_args()


def clamp_unit_interval(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")
    if value > Decimal("1"):
        return Decimal("1")
    return value


def region_lookup_at(
    state: plate_system.PlateSystemState,
) -> dict[str, plate_system.PlateRegionState]:
    return {region.region_id: region for region in state.plate_regions}


def active_plate_factor_at(state: plate_system.PlateSystemState) -> Decimal:
    return Decimal(state.active_plate_count) / Decimal(len(plate_system.REGION_TEMPLATES))


def spreading_factor_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(state.spreading_rate_cm_per_yr / Decimal("3.2"))


def collision_factor_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(state.collision_rate_cm_per_yr / Decimal("2.4"))


def recycling_factor_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(state.recycling_rate_cm_per_yr / Decimal("2.6"))


def transform_factor_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(state.transform_rate_cm_per_yr / Decimal("1.6"))


def speed_factor_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(state.mean_plate_speed_cm_per_yr / Decimal("6.2"))


def positive_balance_factor_at(state: plate_system.PlateSystemState) -> Decimal:
    if state.net_crust_balance_km2_per_yr <= Decimal("0"):
        return Decimal("0")
    return clamp_unit_interval(state.net_crust_balance_km2_per_yr / Decimal("0.3"))


def continent_growth_index_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.45") * collision_factor_at(state))
        + (Decimal("0.30") * recycling_factor_at(state))
        + (Decimal("0.15") * active_plate_factor_at(state))
        + (Decimal("0.10") * positive_balance_factor_at(state))
    )


def basin_growth_index_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.55") * spreading_factor_at(state))
        + (Decimal("0.25") * transform_factor_at(state))
        + (Decimal("0.20") * active_plate_factor_at(state))
    )


def ridge_index_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.75") * spreading_factor_at(state))
        + (Decimal("0.25") * speed_factor_at(state))
    )


def arc_index_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.60") * recycling_factor_at(state))
        + (Decimal("0.40") * collision_factor_at(state))
    )


def uplift_index_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.70") * collision_factor_at(state))
        + (Decimal("0.30") * recycling_factor_at(state))
    )


def rift_index_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.60") * spreading_factor_at(state))
        + (Decimal("0.40") * transform_factor_at(state))
    )


def highland_index_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.55") * continent_growth_index_at(state))
        + (Decimal("0.45") * uplift_index_at(state))
    )


def lowland_index_at(state: plate_system.PlateSystemState) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.60") * basin_growth_index_at(state))
        + (Decimal("0.40") * rift_index_at(state))
    )


def feature_index_at(
    state: plate_system.PlateSystemState, driver_kind: str
) -> Decimal:
    if driver_kind == "continent":
        return continent_growth_index_at(state)
    if driver_kind == "minor_continent":
        return continent_growth_index_at(state)
    if driver_kind == "basin":
        return basin_growth_index_at(state)
    if driver_kind == "ridge":
        return ridge_index_at(state)
    if driver_kind == "arc":
        return arc_index_at(state)
    if driver_kind == "uplift":
        return uplift_index_at(state)
    if driver_kind == "rift":
        return rift_index_at(state)
    if driver_kind == "highland":
        return highland_index_at(state)
    return lowland_index_at(state)


def maturity_state_at(region_status: str) -> str:
    if region_status == "overturn_domain":
        return "embryonic"
    if region_status == "proto_plate_region":
        return "developing"
    return "established"


def area_fraction_at(driver_kind: str, feature_index: Decimal) -> Decimal:
    if driver_kind == "continent":
        return Decimal("0.02") + (Decimal("0.10") * feature_index)
    if driver_kind == "minor_continent":
        return Decimal("0.012") + (Decimal("0.060") * feature_index)
    if driver_kind == "basin":
        return Decimal("0.08") + (Decimal("0.18") * feature_index)
    if driver_kind == "ridge":
        return Decimal("0.004") + (Decimal("0.012") * feature_index)
    if driver_kind == "arc":
        return Decimal("0.006") + (Decimal("0.014") * feature_index)
    if driver_kind == "uplift":
        return Decimal("0.010") + (Decimal("0.030") * feature_index)
    if driver_kind == "rift":
        return Decimal("0.005") + (Decimal("0.020") * feature_index)
    if driver_kind == "highland":
        return Decimal("0.010") + (Decimal("0.050") * feature_index)
    return Decimal("0.030") + (Decimal("0.080") * feature_index)


def relief_m_at(driver_kind: str, feature_index: Decimal) -> Decimal:
    if driver_kind == "continent":
        return Decimal("400") + (Decimal("2600") * feature_index)
    if driver_kind == "minor_continent":
        return Decimal("250") + (Decimal("1800") * feature_index)
    if driver_kind == "basin":
        return -(Decimal("1200") + (Decimal("2800") * feature_index))
    if driver_kind == "ridge":
        return Decimal("500") + (Decimal("1800") * feature_index)
    if driver_kind == "arc":
        return Decimal("800") + (Decimal("2200") * feature_index)
    if driver_kind == "uplift":
        return Decimal("700") + (Decimal("2600") * feature_index)
    if driver_kind == "rift":
        return -(Decimal("400") + (Decimal("1600") * feature_index))
    if driver_kind == "highland":
        return Decimal("600") + (Decimal("2400") * feature_index)
    return -(Decimal("250") + (Decimal("900") * feature_index))


def topography_features_at(
    state: plate_system.PlateSystemState,
) -> tuple[TopographyFeatureState, ...]:
    regions = region_lookup_at(state)
    surface_area_km2 = plate_system.surface_area_km2_at(state.radius_km)
    features: list[TopographyFeatureState] = []

    for template in FEATURE_TEMPLATES:
        source_region = regions.get(template.source_region_id)
        if source_region is None:
            continue

        feature_index = feature_index_at(state, template.driver_kind)
        area_fraction = area_fraction_at(template.driver_kind, feature_index)
        features.append(
            TopographyFeatureState(
                feature_id=template.feature_id,
                feature_type=template.feature_type,
                source_region_id=template.source_region_id,
                source_region_status=source_region.status,
                maturity_state=maturity_state_at(source_region.status),
                tectonic_driver=template.tectonic_driver,
                relief_m=relief_m_at(template.driver_kind, feature_index),
                area_fraction=area_fraction,
                area_km2=surface_area_km2 * area_fraction,
            )
        )

    return tuple(features)


def proto_continent_fraction_at(features: tuple[TopographyFeatureState, ...]) -> Decimal:
    return sum(
        (
            feature.area_fraction
            for feature in features
            if feature.feature_type == "proto_continent"
        ),
        start=Decimal("0"),
    )


def ocean_basin_fraction_at(features: tuple[TopographyFeatureState, ...]) -> Decimal:
    return sum(
        (
            feature.area_fraction
            for feature in features
            if feature.feature_type == "ocean_basin"
        ),
        start=Decimal("0"),
    )


def highest_relief_m_at(features: tuple[TopographyFeatureState, ...]) -> Decimal:
    return max((feature.relief_m for feature in features if feature.relief_m > 0), default=Decimal("0"))


def deepest_basin_m_at(features: tuple[TopographyFeatureState, ...]) -> Decimal:
    return max(
        (-feature.relief_m for feature in features if feature.relief_m < 0),
        default=Decimal("0"),
    )


def topography_state_at(
    state: plate_system.PlateSystemState,
    proto_continent_fraction: Decimal,
    ocean_basin_fraction: Decimal,
) -> str:
    if state.tectonic_regime == "episodic_overturn":
        return "overturn_relief_world"
    if state.tectonic_regime == "stagnant_lid":
        return "segmented_relief_world"
    if proto_continent_fraction >= Decimal("0.08") and ocean_basin_fraction >= Decimal("0.30"):
        return "structured_barren_world"
    return "emergent_relief_world"


def large_scale_topography_state_from_plate_system_state(
    base_state: plate_system.PlateSystemState,
) -> LargeScaleTopographyState:
    features = topography_features_at(base_state)
    proto_continent_fraction = proto_continent_fraction_at(features)
    ocean_basin_fraction = ocean_basin_fraction_at(features)
    highest_relief_m = highest_relief_m_at(features)
    deepest_basin_m = deepest_basin_m_at(features)
    return LargeScaleTopographyState(
        step_index=base_state.step_index,
        age_years=base_state.age_years,
        radius_km=base_state.radius_km,
        tectonic_regime=base_state.tectonic_regime,
        proto_continent_fraction=proto_continent_fraction,
        ocean_basin_fraction=ocean_basin_fraction,
        highest_relief_m=highest_relief_m,
        deepest_basin_m=deepest_basin_m,
        relief_contrast_m=highest_relief_m + deepest_basin_m,
        topography_state=topography_state_at(
            base_state, proto_continent_fraction, ocean_basin_fraction
        ),
        feature_count=len(features),
        features=features,
        world_class=base_state.world_class,
    )


def topography_surface_artifact_key(resolution: tuple[int, int]) -> str:
    return (
        "topography_surface:"
        f"{plate_system.surface_grid_resolution_label(resolution)}"
    )


def boundary_type_mask(surface: PlanetSurface, boundary_type: str) -> np.ndarray:
    mask = np.zeros(surface.region_ids.shape[0], dtype=float)
    for edge_index, edge_kind in enumerate(surface.edge_boundary_type):
        if str(edge_kind) != boundary_type:
            continue
        region_a_index = int(surface.edge_region_indices[edge_index, 0])
        region_b_index = int(surface.edge_region_indices[edge_index, 1])
        interaction = float(surface.edge_interaction_index[edge_index])
        mask[region_a_index] = max(mask[region_a_index], interaction)
        mask[region_b_index] = max(mask[region_b_index], interaction)
    return mask


def temperature_field_for_surface(
    surface: PlanetSurface, temperature_state: surface_temperature.SurfaceTemperatureState
) -> np.ndarray:
    return np.asarray(
        [
            float(
                surface_temperature.zonal_temperature_c_at(
                    temperature_state, float(latitude_degrees)
                )
            )
            for latitude_degrees in surface.center_latitude_degrees
        ],
        dtype=float,
    )


def crust_type_field_for_surface(surface: PlanetSurface) -> np.ndarray:
    crust_type: list[str] = []
    for index in range(surface.region_ids.shape[0]):
        rigidity = float(surface.lithosphere_rigidity[index])
        recycling = float(surface.recycling_tendency[index])
        creation = float(surface.crust_creation_tendency[index])
        destruction = float(surface.crust_destruction_tendency[index])
        rift = float(surface.proto_rift_likelihood[index])
        if rigidity >= 0.60 and recycling >= 0.45 and destruction >= creation:
            crust_type.append("proto_continental")
        elif creation >= destruction or rift >= 0.55:
            crust_type.append("juvenile_oceanic")
        else:
            crust_type.append("hybrid_primordial")
    return np.asarray(crust_type)


def unscaled_elevation_field(
    surface: PlanetSurface, topography_state: LargeScaleTopographyState
) -> np.ndarray:
    crust_type = crust_type_field_for_surface(surface)
    base_elevation = np.zeros(surface.region_ids.shape[0], dtype=float)
    for index, crust_name in enumerate(crust_type):
        if crust_name == "proto_continental":
            base_elevation[index] = 850.0 + (
                1100.0 * float(surface.lithosphere_rigidity[index])
            )
        elif crust_name == "juvenile_oceanic":
            base_elevation[index] = -600.0 - (
                1300.0 * float(surface.crust_creation_tendency[index])
            )
        else:
            base_elevation[index] = -80.0 + (
                500.0 * float(surface.recycling_tendency[index])
            )

    base_elevation += (
        550.0 * surface.upwelling_tendency
        - 450.0 * surface.proto_rift_likelihood
        - 350.0 * surface.crust_destruction_tendency
        + 300.0 * surface.crust_creation_tendency
    )

    convergent_mask = boundary_type_mask(surface, "convergent")
    spreading_mask = boundary_type_mask(surface, "spreading")
    transform_mask = boundary_type_mask(surface, "transform")
    indeterminate_mask = boundary_type_mask(surface, "indeterminate")
    base_elevation += 2800.0 * convergent_mask
    base_elevation -= 1700.0 * spreading_mask
    base_elevation += 260.0 * transform_mask
    base_elevation -= 120.0 * indeterminate_mask

    broad_relief = diffuse_scalar(
        (
            900.0 * surface.recycling_tendency
            - 700.0 * surface.upwelling_tendency
            + 500.0 * surface.thermal_stress
        ),
        surface.neighbor_indices,
        iterations=8,
        alpha=0.32,
    )
    base_elevation = (0.65 * base_elevation) + (0.35 * broad_relief)

    continent_amplifier = 0.70 + (
        2.0 * float(topography_state.proto_continent_fraction)
    )
    basin_amplifier = 0.85 + (1.6 * float(topography_state.ocean_basin_fraction))

    positive_mask = base_elevation > 0.0
    negative_mask = base_elevation < 0.0
    if np.any(positive_mask):
        current_positive = float(np.max(base_elevation[positive_mask]))
        target_positive = max(500.0, float(topography_state.highest_relief_m)) * continent_amplifier
        base_elevation[positive_mask] *= target_positive / max(current_positive, 1.0)
    if np.any(negative_mask):
        current_negative = float(np.max(-base_elevation[negative_mask]))
        target_negative = max(500.0, float(topography_state.deepest_basin_m)) * basin_amplifier
        base_elevation[negative_mask] *= target_negative / max(current_negative, 1.0)

    smoothed = diffuse_scalar(
        base_elevation, surface.neighbor_indices, iterations=4, alpha=0.18
    )
    return (0.78 * base_elevation) + (0.22 * smoothed)


def basin_index_field(surface: PlanetSurface, elevation: np.ndarray) -> np.ndarray:
    local_mean = neighbor_mean(elevation, surface.neighbor_indices)
    basin_score = local_mean - elevation
    basin_score += 450.0 * surface.proto_rift_likelihood
    basin_score += 300.0 * (surface.crust_creation_tendency - surface.crust_destruction_tendency)
    return clamp_unit_interval_array(np.asarray((basin_score - basin_score.min()) / max(1.0, basin_score.max() - basin_score.min()), dtype=float))


def build_topography_surface(
    plate_surface: PlanetSurface,
    topography_state: LargeScaleTopographyState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
) -> PlanetSurface:
    surface = subdivide_lat_lon_surface(plate_surface)
    surface.crust_type = crust_type_field_for_surface(surface)
    surface.elevation = unscaled_elevation_field(surface, topography_state)
    surface.temperature = temperature_field_for_surface(surface, temperature_state)
    surface.temperature -= np.maximum(surface.elevation, 0.0) * 0.0062
    surface.temperature += 7.0 * (
        surface.upwelling_tendency - surface.recycling_tendency
    )
    surface.basin_index = basin_index_field(surface, surface.elevation)
    uplift_bonus = clamp_unit_interval_array(
        np.maximum(surface.elevation, 0.0) / max(1.0, float(np.max(np.maximum(surface.elevation, 0.0))))
    )
    basin_bonus = clamp_unit_interval_array(
        np.maximum(-surface.elevation, 0.0) / max(1.0, float(np.max(np.maximum(-surface.elevation, 0.0))))
    )
    surface.uplift_tendency = clamp_unit_interval_array(
        (0.72 * surface.uplift_tendency) + (0.28 * uplift_bonus)
    )
    surface.basin_tendency = clamp_unit_interval_array(
        (0.58 * surface.basin_tendency)
        + (0.24 * surface.basin_index)
        + (0.18 * basin_bonus)
    )
    surface.terrain_class = terrain_class_from_fields(
        surface.elevation,
        surface.boundary_influence_type,
        surface.basin_tendency,
        surface.uplift_tendency,
    )
    surface.metadata.update(
        {
            "source_layer": "08_large_scale_topography.py",
            "mesh_level": surface.mesh_level,
            "terrain_surface_grid_resolution": (
                f"{surface.longitude_cells}x{surface.latitude_cells}"
            ),
            "topography_state": topography_state.topography_state,
            "highest_relief_m": float(topography_state.highest_relief_m),
            "deepest_basin_m": float(topography_state.deepest_basin_m),
            "proto_continent_fraction": float(topography_state.proto_continent_fraction),
            "ocean_basin_fraction": float(topography_state.ocean_basin_fraction),
        }
    )
    return surface


def build_plate_surface_for_index(
    proto_state: plate_system.proto_tectonics.ProtoTectonicsState,
    plate_state: plate_system.PlateSystemState,
    resolution: tuple[int, int],
) -> PlanetSurface:
    surface_model = plate_system.build_plate_surface_model(
        proto_state, plate_state, resolution
    )
    return planet_surface_from_plate_surface_model(
        surface_model,
        step_index=plate_state.step_index,
        age_years=plate_state.age_years,
        radius_km=float(plate_state.radius_km),
    )


def topography_surface_for_index(
    index: int,
    proto_states: tuple[plate_system.proto_tectonics.ProtoTectonicsState, ...],
    plate_states: tuple[plate_system.PlateSystemState, ...],
    topography_states: tuple[LargeScaleTopographyState, ...],
    temperature_states: tuple[surface_temperature.SurfaceTemperatureState, ...],
    resolution: tuple[int, int],
    cache: dict[int, PlanetSurface],
) -> PlanetSurface:
    if index not in cache:
        plate_surface = build_plate_surface_for_index(
            proto_states[index], plate_states[index], resolution
        )
        cache[index] = build_topography_surface(
            plate_surface, topography_states[index], temperature_states[index]
        )
    return cache[index]


def topography_present_output_path(current_file: str) -> Path:
    return visualization_output_path(current_file, "__topography_present.png")


def write_topography_map_png(
    surface: PlanetSurface,
    output_path: Path,
    *,
    title: str,
    subtitle: str,
) -> Path:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.lines import Line2D
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ImportError(
            "Topography visualization requires matplotlib. Install dependencies "
            "with `python3 -m pip install -r requirements.txt`."
        ) from exc

    figure, axis = plt.subplots(figsize=(16.6, 9.2), facecolor="#f6f1e8")
    axis.set_facecolor("#fffdf8")
    grid = surface.elevation.reshape(surface.latitude_cells, surface.longitude_cells)
    image = axis.imshow(
        grid,
        origin="lower",
        extent=(-180, 180, -90, 90),
        aspect="auto",
        cmap="terrain",
        interpolation="nearest",
    )
    colorbar = figure.colorbar(image, ax=axis, pad=0.02, fraction=0.04)
    colorbar.set_label("Elevation (m)", color="#1f2937")
    colorbar.ax.tick_params(colors="#6b7280")

    boundary_palette = {
        "spreading": "#2f6fed",
        "convergent": "#c4333b",
        "transform": "#f0a202",
        "indeterminate": "#7c7c7c",
    }
    for boundary in boundary_records(surface):
        region_a_index = np.where(surface.region_ids == boundary["region_a_id"])[0][0]
        region_b_index = np.where(surface.region_ids == boundary["region_b_id"])[0][0]
        axis.plot(
            [
                float(surface.center_longitude_degrees[region_a_index]),
                float(surface.center_longitude_degrees[region_b_index]),
            ],
            [
                float(surface.center_latitude_degrees[region_a_index]),
                float(surface.center_latitude_degrees[region_b_index]),
            ],
            color=boundary_palette.get(boundary["boundary_type"], "#7c7c7c"),
            linewidth=1.1,
            alpha=0.7,
            zorder=3,
        )

    axis.set_title(title, fontsize=18, color="#1f2937", loc="left", pad=14)
    axis.text(
        0.0,
        1.01,
        subtitle,
        transform=axis.transAxes,
        ha="left",
        va="bottom",
        fontsize=10.5,
        color="#6b7280",
    )
    axis.set_xlabel("Longitude (degrees)", color="#1f2937", fontsize=11)
    axis.set_ylabel("Latitude (degrees)", color="#1f2937", fontsize=11)
    axis.set_xticks([-180, -120, -60, 0, 60, 120, 180])
    axis.set_yticks([-90, -60, -30, 0, 30, 60, 90])
    axis.tick_params(colors="#6b7280")
    axis.grid(color="#d7d2c8", linewidth=0.5, alpha=0.20)
    for spine in axis.spines.values():
        spine.set_color("#d7d2c8")

    legend_handles = [
        Line2D([0], [0], color="#2f6fed", lw=2.2, label="Spreading boundary"),
        Line2D([0], [0], color="#c4333b", lw=2.2, label="Convergent boundary"),
        Line2D([0], [0], color="#f0a202", lw=2.2, label="Transform boundary"),
    ]
    legend = axis.legend(
        handles=legend_handles,
        title="Boundary Types",
        loc="center left",
        bbox_to_anchor=(1.01, 0.78),
        frameon=True,
    )
    legend.get_frame().set_facecolor("#fffdf8")
    legend.get_frame().set_edgecolor("#d7d2c8")

    figure.subplots_adjust(left=0.07, right=0.82, top=0.90, bottom=0.10)
    figure.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return output_path


def write_topography_artifacts(
    proto_states: tuple[plate_system.proto_tectonics.ProtoTectonicsState, ...],
    plate_states: tuple[plate_system.PlateSystemState, ...],
    topography_states: tuple[LargeScaleTopographyState, ...],
    temperature_states: tuple[surface_temperature.SurfaceTemperatureState, ...],
    resolution: tuple[int, int],
    current_file: str,
    cache: dict[int, PlanetSurface],
) -> Path | None:
    if not topography_states:
        return None

    present_surface = topography_surface_for_index(
        len(topography_states) - 1,
        proto_states,
        plate_states,
        topography_states,
        temperature_states,
        resolution,
        cache,
    )
    state_path = save_planet_surface(
        present_surface,
        surface_state_output_path(
            current_file,
            present_surface.longitude_cells,
            present_surface.latitude_cells,
        ),
    )
    write_topography_map_png(
        present_surface,
        topography_present_output_path(current_file),
        title="08 Large-Scale Topography: Present-Day Elevation",
        subtitle=(
            f"Equirectangular projection, "
            f"{present_surface.longitude_cells}x{present_surface.latitude_cells} "
            "shared surface cells colored by deterministic elevation."
        ),
    )

    frames_dir = clear_frame_directory(frame_output_dir(
        current_file,
        FRAME_DIRECTORY_NAME,
        present_surface.longitude_cells,
        present_surface.latitude_cells,
    ))
    for index in frame_sample_indices(len(topography_states)):
        frame_surface = topography_surface_for_index(
            index,
            proto_states,
            plate_states,
            topography_states,
            temperature_states,
            resolution,
            cache,
        )
        write_topography_map_png(
            frame_surface,
            frames_dir / f"frame_{frame_surface.step_index:04d}.png",
            title="08 Large-Scale Topography",
            subtitle=(
                f"Timestep {frame_surface.step_index}, age "
                f"{frame_surface.age_years / 1_000_000.0:.1f} Myr."
            ),
        )
    return state_path


def build_topography_surface_extra(
    tectonic_surface: PlanetSurface,
    surface: PlanetSurface,
    *,
    state_path: Path,
    current_file: str,
) -> dict[str, object]:
    frames_dir = frame_output_dir(
        current_file,
        FRAME_DIRECTORY_NAME,
        surface.longitude_cells,
        surface.latitude_cells,
    )
    return {
        "tectonic_mesh": surface_json_payload(
            tectonic_surface,
            state_path=surface_state_output_path(
                plate_system.__file__,
                tectonic_surface.longitude_cells,
                tectonic_surface.latitude_cells,
            ),
        ),
        "terrain_mesh": surface_json_payload(
            surface,
            state_path=state_path,
            frame_directory=frames_dir,
        ),
        "surface_geometry": surface_json_payload(
            surface,
            state_path=state_path,
            frame_directory=frames_dir,
        ),
        "surface_hierarchy": {
            "authoritative_tectonic_mesh_resolution": (
                f"{tectonic_surface.longitude_cells}x{tectonic_surface.latitude_cells}"
            ),
            "refined_terrain_mesh_resolution": (
                f"{surface.longitude_cells}x{surface.latitude_cells}"
            ),
            "subdivision_rule": "deterministic_lat_lon_quadrisection",
            "child_order": ["south_west", "south_east", "north_west", "north_east"],
            "terrain_cells_per_tectonic_cell": 4,
        },
        "surface_summary": {
            "mean_elevation_m": float(np.mean(surface.elevation)),
            "max_elevation_m": float(np.max(surface.elevation)),
            "min_elevation_m": float(np.min(surface.elevation)),
            "mean_temperature_c": float(np.mean(surface.temperature)),
            "mean_slope_index": float(np.mean(gradient_magnitude(surface, surface.elevation))),
        },
    }


def simulate(
    criteria: planet.SimulationCriteria,
    surface_grid_resolution: tuple[int, int] | None = None,
) -> Iterable[LargeScaleTopographyState]:
    resolution = surface_grid_resolution or plate_system.parse_surface_grid_resolution(
        plate_system.DEFAULT_SURFACE_GRID_RESOLUTION
    )
    proto_states = tuple(plate_system.proto_tectonics.simulate(criteria, resolution))
    plate_states = tuple(plate_system.simulate(criteria, resolution))
    temperature_states = tuple(surface_temperature.simulate(criteria))

    def build_states() -> Iterable[LargeScaleTopographyState]:
        for base_state in plate_states:
            yield large_scale_topography_state_from_plate_system_state(base_state)

    surface_cache: dict[int, PlanetSurface] = {}

    def extra_builder(
        states: tuple[LargeScaleTopographyState, ...],
    ) -> dict[str, object] | None:
        if not states:
            return None
        present_tectonic_surface = build_plate_surface_for_index(
            proto_states[-1], plate_states[-1], resolution
        )
        present_surface = topography_surface_for_index(
            len(states) - 1,
            proto_states,
            plate_states,
            states,
            temperature_states,
            resolution,
            surface_cache,
        )
        state_path = surface_state_output_path(
            __file__,
            present_surface.longitude_cells,
            present_surface.latitude_cells,
        )
        return build_topography_surface_extra(
            present_tectonic_surface,
            present_surface,
            state_path=state_path,
            current_file=__file__,
        )

    return materialize_layer_states(
        __file__,
        criteria,
        build_states,
        extra_builder=extra_builder,
        artifact_key=topography_surface_artifact_key(resolution),
        artifact_writer=lambda states: write_topography_artifacts(
            proto_states,
            plate_states,
            states,
            temperature_states,
            resolution,
            __file__,
            surface_cache,
        ),
    )


def first_structured_topography_state(
    states: Iterable[LargeScaleTopographyState],
) -> LargeScaleTopographyState | None:
    for state in states:
        if state.topography_state == "structured_barren_world":
            return state
    return None


def validate_model(
    surface_grid_resolution: tuple[int, int] | None = None,
) -> None:
    resolution = surface_grid_resolution or plate_system.parse_surface_grid_resolution(
        plate_system.DEFAULT_SURFACE_GRID_RESOLUTION
    )
    plate_system.validate_model()
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria, resolution))
    initial_state = states[0]
    present_state = states[-1]
    first_structured_state = first_structured_topography_state(states)
    present_feature_types = {feature.feature_type for feature in present_state.features}
    terrain_resolution = subdivided_surface_grid_resolution(resolution)
    surface_path = surface_state_output_path(
        __file__, terrain_resolution[0], terrain_resolution[1]
    )
    surface = load_planet_surface(surface_path)
    required_types = {
        "proto_continent",
        "ocean_basin",
        "ridge",
        "volcanic_arc",
        "uplift",
        "rift",
        "highlands",
        "lowlands",
    }

    if initial_state.relief_contrast_m <= Decimal("0"):
        raise ValueError("Initial large-scale relief contrast must be positive.")
    if present_state.proto_continent_fraction <= Decimal("0.05"):
        raise ValueError("Present-day Aeron should sustain a proto-continental fraction.")
    if present_state.ocean_basin_fraction <= Decimal("0.20"):
        raise ValueError("Present-day Aeron should sustain major ocean basins.")
    if present_state.highest_relief_m <= Decimal("1500"):
        raise ValueError("Present-day relief should include major uplifts or highlands.")
    if present_state.deepest_basin_m <= Decimal("2000"):
        raise ValueError("Present-day relief should include deep first-order basins.")
    if required_types - present_feature_types:
        raise ValueError("Present-day topography must include all first-order relief classes.")
    if sum(1 for feature in present_state.features if feature.feature_type == "proto_continent") < 2:
        raise ValueError("Present-day topography should include plural proto-continents.")
    if first_structured_state is None:
        raise ValueError("Structured barren-world relief must emerge within the span.")
    if surface.region_ids.shape[0] != 4 * resolution[0] * resolution[1]:
        raise ValueError("Topography surface must deterministically subdivide the tectonic mesh.")
    if surface.mesh_level != "terrain_mesh":
        raise ValueError("Topography surface must be persisted as the refined terrain mesh.")
    if int(np.sum(surface.parent_cell_id == surface.root_tectonic_cell_id)) != surface.region_ids.shape[0]:
        raise ValueError("First refinement level should preserve direct tectonic ancestry.")
    if float(np.max(surface.elevation)) <= 1500.0:
        raise ValueError("Present-day topography surface should contain major uplifts.")
    if float(np.min(surface.elevation)) >= -1800.0:
        raise ValueError("Present-day topography surface should contain deep basins.")
    if float(np.mean(surface.basin_index)) <= 0.20:
        raise ValueError("Present-day topography surface should expose basin structure.")


def print_input_criteria(
    criteria: planet.SimulationCriteria, surface_grid_resolution: tuple[int, int]
) -> None:
    lon_cells, lat_cells = surface_grid_resolution
    fields = [
        ("layer_name", "large_scale_topography_generation"),
        ("plate_system_source", "07_plate_system.py"),
        ("proto_tectonics_source", "06_proto_tectonics.py"),
        ("surface_temperature_source", "05_surface_temperature.py"),
        ("early_atmosphere_source", "04_early_atmosphere.py"),
        ("primary_crust_source", "03_primary_crust.py"),
        ("interior_source", "02_interior.py"),
        ("planet_source", "01_planet.py"),
        ("coupled_plate_system_layer", "true"),
        ("coupled_proto_tectonic_layer", "true"),
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
        ("shared_surface_geometry", "true"),
        ("surface_grid_resolution", f"{lon_cells}x{lat_cells}"),
        ("surface_state_contract", "PlanetSurface"),
        ("province_model", "fixed_template_relief_features"),
        ("relief_model", "tectonic_rate_scaled_first_order_relief"),
        ("erosion_model", "neighbor_diffusion_only"),
        (
            "dynamic_fields",
            "proto_continent_fraction, ocean_basin_fraction, "
            "highest_relief_m, deepest_basin_m, relief_contrast_m, "
            "topography_state, feature_count, elevation field, temperature field",
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print("INPUT CRITERIA")
    print("==============")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")
    print()


def print_table(
    criteria: planet.SimulationCriteria, surface_grid_resolution: tuple[int, int]
) -> None:
    headers = (
        ("step", 8),
        ("age_myr", 12),
        ("regime", 18),
        ("topography", 24),
        ("features", 9),
        ("proto_f", 9),
        ("basin_f", 9),
        ("high_m", 9),
        ("deep_m", 9),
        ("contrast", 10),
    )

    header_line = " ".join(f"{label:>{width}}" for label, width in headers)
    divider_line = " ".join("-" * width for _, width in headers)
    print(header_line)
    print(divider_line)

    for state in simulate(criteria, surface_grid_resolution):
        age_myr = planet.format_decimal(
            Decimal(state.age_years) / planet.YEARS_PER_MYR, 3
        )
        print(
            f"{state.step_index:>8d} "
            f"{age_myr:>12} "
            f"{state.tectonic_regime:>18} "
            f"{state.topography_state:>24} "
            f"{state.feature_count:>9d} "
            f"{planet.format_decimal(state.proto_continent_fraction, 3):>9} "
            f"{planet.format_decimal(state.ocean_basin_fraction, 3):>9} "
            f"{planet.format_decimal(state.highest_relief_m, 3):>9} "
            f"{planet.format_decimal(state.deepest_basin_m, 3):>9} "
            f"{planet.format_decimal(state.relief_contrast_m, 3):>10}"
        )


def print_present_day_summary(
    criteria: planet.SimulationCriteria, surface_grid_resolution: tuple[int, int]
) -> None:
    states = list(simulate(criteria, surface_grid_resolution))
    final_state = states[-1]
    first_structured_state = first_structured_topography_state(states)
    terrain_resolution = subdivided_surface_grid_resolution(surface_grid_resolution)
    surface = load_planet_surface(
        surface_state_output_path(
            __file__, terrain_resolution[0], terrain_resolution[1]
        )
    )

    assert first_structured_state is not None

    fields = [
        ("world_class", final_state.world_class),
        ("tectonic_regime", final_state.tectonic_regime),
        ("topography_state", final_state.topography_state),
        (
            "proto_continent_fraction",
            planet.format_decimal(final_state.proto_continent_fraction, 6),
        ),
        (
            "ocean_basin_fraction",
            planet.format_decimal(final_state.ocean_basin_fraction, 6),
        ),
        ("highest_relief_m", planet.format_decimal(final_state.highest_relief_m, 6)),
        ("deepest_basin_m", planet.format_decimal(final_state.deepest_basin_m, 6)),
        ("relief_contrast_m", planet.format_decimal(final_state.relief_contrast_m, 6)),
        ("feature_count", str(final_state.feature_count)),
        ("surface_region_count", str(surface.region_ids.shape[0])),
        ("surface_face_count", str(surface.faces.shape[0])),
        ("surface_mesh_level", surface.mesh_level),
        ("surface_subdivision_level", str(surface.subdivision_level)),
        ("surface_state_path", str(surface_state_output_path(
            __file__, terrain_resolution[0], terrain_resolution[1]
        ))),
        ("first_structured_relief_step", str(first_structured_state.step_index)),
        (
            "first_structured_relief_age_myr",
            planet.format_decimal(
                Decimal(first_structured_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT LARGE-SCALE TOPOGRAPHY SUMMARY")
    print("=====================================")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")

    print()
    print("PRESENT TOPOGRAPHIC FEATURES")
    print("============================")
    headers = (
        ("feature", 28),
        ("type", 16),
        ("maturity", 12),
        ("driver", 28),
        ("relief_m", 10),
        ("area_f", 8),
        ("area_km2", 14),
    )
    header_line = " ".join(f"{label:>{width}}" for label, width in headers)
    divider_line = " ".join("-" * width for _, width in headers)
    print(header_line)
    print(divider_line)
    for feature in final_state.features:
        print(
            f"{feature.feature_id:>28} "
            f"{feature.feature_type:>16} "
            f"{feature.maturity_state:>12} "
            f"{feature.tectonic_driver:>28} "
            f"{planet.format_decimal(feature.relief_m, 3):>10} "
            f"{planet.format_decimal(feature.area_fraction, 3):>8} "
            f"{planet.format_decimal(feature.area_km2, 3):>14}"
        )


def main() -> int:
    args = parse_args()
    try:
        criteria = planet.build_criteria(args.step_years)
        surface_grid_resolution = plate_system.parse_surface_grid_resolution(
            args.surface_grid_resolution
        )
        validate_model(surface_grid_resolution)
    except ValueError as exc:
        raise SystemExit(str(exc))

    print_input_criteria(criteria, surface_grid_resolution)
    print_table(criteria, surface_grid_resolution)
    print_present_day_summary(criteria, surface_grid_resolution)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
