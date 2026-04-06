#!/usr/bin/env python3
"""Deterministic volcanic and impact resurfacing simulation for Aeron."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    from .world_building_support import load_pipeline_module, materialize_layer_states
    from .world_building_surface import (
        PlanetSurface,
        clear_frame_directory,
        deep_copy_surface,
        diffuse_scalar,
        frame_output_dir,
        frame_sample_indices,
        load_planet_surface,
        normalized,
        save_planet_surface,
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
        clear_frame_directory,
        deep_copy_surface,
        diffuse_scalar,
        frame_output_dir,
        frame_sample_indices,
        load_planet_surface,
        normalized,
        save_planet_surface,
        subdivided_surface_grid_resolution,
        surface_json_payload,
        surface_state_output_path,
        terrain_class_from_fields,
        visualization_output_path,
    )

large_scale_topography = load_pipeline_module(
    __package__, __file__, "08_large_scale_topography"
)
planet = load_pipeline_module(__package__, __file__, "01_planet")

getcontext().prec = 50

VALIDATION_STEP_YEARS = 100_000_000
FRAME_DIRECTORY_NAME = "09_resurfacing"


@dataclass(frozen=True)
class ResurfacingFeatureTemplate:
    feature_id: str
    feature_type: str
    source_feature_id: str
    driver_kind: str
    source_relation: str


@dataclass(frozen=True)
class ResurfacingFeatureState:
    feature_id: str
    feature_type: str
    source_feature_id: str
    source_feature_type: str
    activity_state: str
    activity_index: Decimal
    area_fraction: Decimal
    area_km2: Decimal
    preserved_fraction: Decimal


@dataclass(frozen=True)
class VolcanicImpactResurfacingState:
    step_index: int
    age_years: int
    radius_km: Decimal
    tectonic_regime: str
    hotspot_count: int
    hotspot_activity_index: Decimal
    flood_basalt_event_count: int
    flood_basalt_intensity_index: Decimal
    volcanic_province_fraction: Decimal
    major_crater_rate_per_gyr: Decimal
    crater_persistence_fraction: Decimal
    resurfacing_fraction_per_gyr: Decimal
    resurfacing_rate_km2_per_yr: Decimal
    old_crust_survival_fraction: Decimal
    scar_state: str
    feature_count: int
    features: tuple[ResurfacingFeatureState, ...]
    world_class: str


FEATURE_TEMPLATES = (
    ResurfacingFeatureTemplate(
        feature_id="western_hotspot_track",
        feature_type="hotspot_track",
        source_feature_id="western_spreading_ridge",
        driver_kind="hotspot",
        source_relation="ridge_plume_interaction",
    ),
    ResurfacingFeatureTemplate(
        feature_id="austral_hotspot_swell",
        feature_type="hotspot_track",
        source_feature_id="austral_uplift_belt",
        driver_kind="hotspot",
        source_relation="uplift_plume_interaction",
    ),
    ResurfacingFeatureTemplate(
        feature_id="pelagic_hotspot_track",
        feature_type="hotspot_track",
        source_feature_id="pelagic_lowland_troughs",
        driver_kind="hotspot",
        source_relation="oceanic_plume_track",
    ),
    ResurfacingFeatureTemplate(
        feature_id="boreal_flood_traps",
        feature_type="flood_basalt_province",
        source_feature_id="boreal_proto_continent",
        driver_kind="flood_basalt",
        source_relation="continental_traps",
    ),
    ResurfacingFeatureTemplate(
        feature_id="equatorial_flood_traps",
        feature_type="flood_basalt_province",
        source_feature_id="eastern_rift_system",
        driver_kind="flood_basalt",
        source_relation="rift_fed_traps",
    ),
    ResurfacingFeatureTemplate(
        feature_id="austral_flood_traps",
        feature_type="flood_basalt_province",
        source_feature_id="austral_proto_continent",
        driver_kind="flood_basalt",
        source_relation="accretionary_traps",
    ),
    ResurfacingFeatureTemplate(
        feature_id="boreal_arc_volcanic_province",
        feature_type="volcanic_province",
        source_feature_id="boreal_volcanic_arc",
        driver_kind="volcanic_province",
        source_relation="arc_volcanism",
    ),
    ResurfacingFeatureTemplate(
        feature_id="western_ridge_volcanic_province",
        feature_type="volcanic_province",
        source_feature_id="western_spreading_ridge",
        driver_kind="volcanic_province",
        source_relation="ridge_volcanism",
    ),
    ResurfacingFeatureTemplate(
        feature_id="southern_ridge_volcanic_province",
        feature_type="volcanic_province",
        source_feature_id="southern_spreading_ridge",
        driver_kind="volcanic_province",
        source_relation="ridge_volcanism",
    ),
    ResurfacingFeatureTemplate(
        feature_id="western_basin_crater_field",
        feature_type="crater_field",
        source_feature_id="western_pelagic_basin",
        driver_kind="crater_field",
        source_relation="basin_preservation",
    ),
    ResurfacingFeatureTemplate(
        feature_id="southern_basin_crater_field",
        feature_type="crater_field",
        source_feature_id="southern_pelagic_basin",
        driver_kind="crater_field",
        source_relation="basin_preservation",
    ),
    ResurfacingFeatureTemplate(
        feature_id="austral_impact_scars",
        feature_type="crater_field",
        source_feature_id="austral_proto_continent",
        driver_kind="crater_field",
        source_relation="continental_preservation",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's volcanic and impact resurfacing by ticking the "
            "large-scale topography layer and deriving surface scarring and reworking."
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
        default=large_scale_topography.plate_system.DEFAULT_SURFACE_GRID_RESOLUTION,
        help=(
            "Coarse surface grid resolution as <longitude>x<latitude> cells for "
            "the inherited shared geometry. Default: "
            f"{large_scale_topography.plate_system.DEFAULT_SURFACE_GRID_RESOLUTION}."
        ),
    )
    return parser.parse_args()


def clamp_unit_interval(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")
    if value > Decimal("1"):
        return Decimal("1")
    return value


def feature_lookup_at(
    state: large_scale_topography.LargeScaleTopographyState,
) -> dict[str, large_scale_topography.TopographyFeatureState]:
    return {feature.feature_id: feature for feature in state.features}


def source_area_factor_at(source_feature_type: str, area_fraction: Decimal) -> Decimal:
    if source_feature_type == "proto_continent":
        scale = Decimal("0.12")
    elif source_feature_type == "ocean_basin":
        scale = Decimal("0.26")
    elif source_feature_type == "ridge":
        scale = Decimal("0.02")
    elif source_feature_type == "volcanic_arc":
        scale = Decimal("0.025")
    elif source_feature_type == "uplift":
        scale = Decimal("0.04")
    elif source_feature_type == "rift":
        scale = Decimal("0.03")
    elif source_feature_type == "highlands":
        scale = Decimal("0.06")
    else:
        scale = Decimal("0.12")
    return clamp_unit_interval(area_fraction / scale)


def area_total_at(
    state: large_scale_topography.LargeScaleTopographyState, feature_type: str
) -> Decimal:
    return sum(
        (feature.area_fraction for feature in state.features if feature.feature_type == feature_type),
        start=Decimal("0"),
    )


def age_fraction_at(age_years: int) -> Decimal:
    return planet.age_fraction_at(age_years)


def hotspot_regime_factor_at(tectonic_regime: str) -> Decimal:
    if tectonic_regime == "episodic_overturn":
        return Decimal("0.95")
    if tectonic_regime == "stagnant_lid":
        return Decimal("0.55")
    return Decimal("0.75")


def survival_regime_factor_at(tectonic_regime: str) -> Decimal:
    if tectonic_regime == "episodic_overturn":
        return Decimal("0.45")
    if tectonic_regime == "stagnant_lid":
        return Decimal("0.75")
    return Decimal("1.0")


def crater_regime_factor_at(tectonic_regime: str) -> Decimal:
    if tectonic_regime == "episodic_overturn":
        return Decimal("0.55")
    if tectonic_regime == "stagnant_lid":
        return Decimal("0.80")
    return Decimal("1.0")


def ridge_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(area_total_at(state, "ridge") / Decimal("0.04"))


def rift_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(area_total_at(state, "rift") / Decimal("0.03"))


def arc_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(area_total_at(state, "volcanic_arc") / Decimal("0.03"))


def uplift_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(area_total_at(state, "uplift") / Decimal("0.05"))


def basin_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(state.ocean_basin_fraction / Decimal("0.55"))


def continent_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(state.proto_continent_fraction / Decimal("0.20"))


def highland_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(area_total_at(state, "highlands") / Decimal("0.08"))


def hotspot_activity_index_at(
    state: large_scale_topography.LargeScaleTopographyState,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.35") * ridge_factor_at(state))
        + (Decimal("0.25") * rift_factor_at(state))
        + (Decimal("0.20") * arc_factor_at(state))
        + (Decimal("0.20") * hotspot_regime_factor_at(state.tectonic_regime))
    )


def early_pulse_factor_at(age_years: int) -> Decimal:
    return Decimal("0.25") + (Decimal("0.75") * (age_fraction_at(age_years) * Decimal("-1.8")).exp())


def flood_basalt_intensity_index_at(
    state: large_scale_topography.LargeScaleTopographyState,
    hotspot_activity_index: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.40") * hotspot_activity_index)
        + (Decimal("0.25") * rift_factor_at(state))
        + (Decimal("0.20") * uplift_factor_at(state))
        + (Decimal("0.15") * early_pulse_factor_at(state.age_years))
    )


def volcanic_province_index_at(
    state: large_scale_topography.LargeScaleTopographyState,
    hotspot_activity_index: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.35") * ridge_factor_at(state))
        + (Decimal("0.30") * arc_factor_at(state))
        + (Decimal("0.20") * hotspot_activity_index)
        + (Decimal("0.15") * rift_factor_at(state))
    )


def impact_flux_index_at(age_years: int) -> Decimal:
    return clamp_unit_interval(
        Decimal("0.15") + (Decimal("0.85") * (age_fraction_at(age_years) * Decimal("-2.8")).exp())
    )


def resurfacing_pressure_at(
    hotspot_activity_index: Decimal,
    flood_basalt_intensity_index: Decimal,
    volcanic_province_index: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.40") * hotspot_activity_index)
        + (Decimal("0.35") * flood_basalt_intensity_index)
        + (Decimal("0.25") * volcanic_province_index)
    )


def major_crater_rate_per_gyr_at(age_years: int) -> Decimal:
    return Decimal("6") + (Decimal("36") * impact_flux_index_at(age_years))


def crater_persistence_fraction_at(
    state: large_scale_topography.LargeScaleTopographyState,
    resurfacing_pressure: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        crater_regime_factor_at(state.tectonic_regime)
        * (
            Decimal("0.10")
            + (Decimal("0.35") * basin_factor_at(state))
            + (Decimal("0.10") * highland_factor_at(state))
            + (Decimal("0.45") * (Decimal("1") - resurfacing_pressure))
        )
    )


def resurfacing_fraction_per_gyr_at(resurfacing_pressure: Decimal) -> Decimal:
    return Decimal("0.15") + (Decimal("1.80") * resurfacing_pressure)


def resurfacing_rate_km2_per_yr_at(
    state: large_scale_topography.LargeScaleTopographyState,
    resurfacing_fraction_per_gyr: Decimal,
) -> Decimal:
    surface_area_km2 = Decimal("4") * planet.PI * (state.radius_km**2)
    return surface_area_km2 * resurfacing_fraction_per_gyr / planet.YEARS_PER_GYR


def old_crust_survival_fraction_at(
    state: large_scale_topography.LargeScaleTopographyState,
    resurfacing_pressure: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        survival_regime_factor_at(state.tectonic_regime)
        * (
            Decimal("0.05")
            + (Decimal("0.40") * continent_factor_at(state))
            + (Decimal("0.10") * highland_factor_at(state))
            + (Decimal("0.35") * (Decimal("1") - resurfacing_pressure))
        )
    )


def activity_state_at(feature_type: str, activity_index: Decimal, preserved_fraction: Decimal) -> str:
    if feature_type == "hotspot_track":
        if activity_index >= Decimal("0.65"):
            return "active"
        if activity_index >= Decimal("0.20"):
            return "pulsing"
        return "dormant"
    if feature_type == "flood_basalt_province":
        if activity_index >= Decimal("0.70"):
            return "active"
        if activity_index >= Decimal("0.30"):
            return "episodic"
        return "dormant"
    if feature_type == "volcanic_province":
        if activity_index >= Decimal("0.60"):
            return "persistent"
        if activity_index >= Decimal("0.35"):
            return "growing"
        return "embryonic"
    if preserved_fraction >= Decimal("0.60"):
        return "preserved"
    if preserved_fraction >= Decimal("0.30"):
        return "partial"
    return "erased"


def feature_area_fraction_at(
    feature_type: str,
    source_area_fraction: Decimal,
    activity_index: Decimal,
    preserved_fraction: Decimal,
) -> Decimal:
    if feature_type == "hotspot_track":
        return source_area_fraction * (Decimal("0.10") + (Decimal("0.20") * activity_index))
    if feature_type == "flood_basalt_province":
        return source_area_fraction * (Decimal("0.14") + (Decimal("0.30") * activity_index))
    if feature_type == "volcanic_province":
        return source_area_fraction * (Decimal("0.50") + (Decimal("0.25") * activity_index))
    return source_area_fraction * (
        Decimal("0.10")
        + (Decimal("0.25") * preserved_fraction)
        + (Decimal("0.05") * activity_index)
    )


def resurfacing_features_at(
    state: large_scale_topography.LargeScaleTopographyState,
    hotspot_activity_index: Decimal,
    flood_basalt_intensity_index: Decimal,
    volcanic_province_index: Decimal,
    crater_persistence_fraction: Decimal,
) -> tuple[ResurfacingFeatureState, ...]:
    source_features = feature_lookup_at(state)
    surface_area_km2 = Decimal("4") * planet.PI * (state.radius_km**2)
    impact_flux_index = impact_flux_index_at(state.age_years)
    features: list[ResurfacingFeatureState] = []

    for template in FEATURE_TEMPLATES:
        source_feature = source_features.get(template.source_feature_id)
        if source_feature is None:
            continue

        local_support = source_area_factor_at(
            source_feature.feature_type, source_feature.area_fraction
        )
        if template.driver_kind == "hotspot":
            activity_index = clamp_unit_interval(
                hotspot_activity_index * (Decimal("0.65") + (Decimal("0.35") * local_support))
            )
            preserved_fraction = Decimal("0")
        elif template.driver_kind == "flood_basalt":
            activity_index = clamp_unit_interval(
                flood_basalt_intensity_index * (Decimal("0.60") + (Decimal("0.40") * local_support))
            )
            preserved_fraction = Decimal("0")
        elif template.driver_kind == "volcanic_province":
            activity_index = clamp_unit_interval(
                volcanic_province_index * (Decimal("0.65") + (Decimal("0.35") * local_support))
            )
            preserved_fraction = Decimal("0")
        else:
            activity_index = clamp_unit_interval(
                impact_flux_index * (Decimal("0.55") + (Decimal("0.45") * local_support))
            )
            preserved_fraction = clamp_unit_interval(
                crater_persistence_fraction * (Decimal("0.60") + (Decimal("0.40") * local_support))
            )

        area_fraction = feature_area_fraction_at(
            template.feature_type,
            source_feature.area_fraction,
            activity_index,
            preserved_fraction,
        )
        features.append(
            ResurfacingFeatureState(
                feature_id=template.feature_id,
                feature_type=template.feature_type,
                source_feature_id=template.source_feature_id,
                source_feature_type=source_feature.feature_type,
                activity_state=activity_state_at(
                    template.feature_type, activity_index, preserved_fraction
                ),
                activity_index=activity_index,
                area_fraction=area_fraction,
                area_km2=surface_area_km2 * area_fraction,
                preserved_fraction=preserved_fraction,
            )
        )

    return tuple(features)


def hotspot_count_at(features: tuple[ResurfacingFeatureState, ...]) -> int:
    return sum(
        1
        for feature in features
        if feature.feature_type == "hotspot_track"
        and feature.activity_state in {"active", "pulsing"}
    )


def flood_basalt_event_count_at(features: tuple[ResurfacingFeatureState, ...]) -> int:
    return sum(
        1
        for feature in features
        if feature.feature_type == "flood_basalt_province"
        and feature.activity_state in {"active", "episodic"}
    )


def volcanic_province_fraction_at(
    features: tuple[ResurfacingFeatureState, ...]
) -> Decimal:
    return sum(
        (
            feature.area_fraction
            for feature in features
            if feature.feature_type in {
                "hotspot_track",
                "flood_basalt_province",
                "volcanic_province",
            }
        ),
        start=Decimal("0"),
    )


def scar_state_at(
    old_crust_survival_fraction: Decimal,
    crater_persistence_fraction: Decimal,
    resurfacing_fraction_per_gyr: Decimal,
) -> str:
    if (
        old_crust_survival_fraction >= Decimal("0.50")
        and crater_persistence_fraction >= Decimal("0.45")
    ):
        return "ancient_scarred_world"
    if resurfacing_fraction_per_gyr >= Decimal("1.20"):
        return "heavily_resurfaced_world"
    return "transitionally_scarred_world"


def volcanic_impact_resurfacing_state_from_topography_state(
    base_state: large_scale_topography.LargeScaleTopographyState,
) -> VolcanicImpactResurfacingState:
    hotspot_activity_index = hotspot_activity_index_at(base_state)
    flood_basalt_intensity_index = flood_basalt_intensity_index_at(
        base_state, hotspot_activity_index
    )
    volcanic_province_index = volcanic_province_index_at(
        base_state, hotspot_activity_index
    )
    resurfacing_pressure = resurfacing_pressure_at(
        hotspot_activity_index,
        flood_basalt_intensity_index,
        volcanic_province_index,
    )
    crater_persistence_fraction = crater_persistence_fraction_at(
        base_state, resurfacing_pressure
    )
    resurfacing_fraction_per_gyr = resurfacing_fraction_per_gyr_at(resurfacing_pressure)
    features = resurfacing_features_at(
        base_state,
        hotspot_activity_index,
        flood_basalt_intensity_index,
        volcanic_province_index,
        crater_persistence_fraction,
    )
    return VolcanicImpactResurfacingState(
        step_index=base_state.step_index,
        age_years=base_state.age_years,
        radius_km=base_state.radius_km,
        tectonic_regime=base_state.tectonic_regime,
        hotspot_count=hotspot_count_at(features),
        hotspot_activity_index=hotspot_activity_index,
        flood_basalt_event_count=flood_basalt_event_count_at(features),
        flood_basalt_intensity_index=flood_basalt_intensity_index,
        volcanic_province_fraction=volcanic_province_fraction_at(features),
        major_crater_rate_per_gyr=major_crater_rate_per_gyr_at(base_state.age_years),
        crater_persistence_fraction=crater_persistence_fraction,
        resurfacing_fraction_per_gyr=resurfacing_fraction_per_gyr,
        resurfacing_rate_km2_per_yr=resurfacing_rate_km2_per_yr_at(
            base_state, resurfacing_fraction_per_gyr
        ),
        old_crust_survival_fraction=old_crust_survival_fraction_at(
            base_state, resurfacing_pressure
        ),
        scar_state=scar_state_at(
            old_crust_survival_fraction_at(base_state, resurfacing_pressure),
            crater_persistence_fraction,
            resurfacing_fraction_per_gyr,
        ),
        feature_count=len(features),
        features=features,
        world_class=base_state.world_class,
    )


def resurfacing_surface_artifact_key(resolution: tuple[int, int]) -> str:
    return (
        "resurfacing_surface:"
        f"{large_scale_topography.plate_system.surface_grid_resolution_label(resolution)}"
    )


def resurfacing_present_output_path(current_file: str) -> Path:
    return visualization_output_path(current_file, "__resurfacing_present.png")


def gaussian_blob_on_grid(
    surface: PlanetSurface, center_index: int, radius_cells: float
) -> np.ndarray:
    latitude_center = int(surface.latitude_index[center_index])
    longitude_center = int(surface.longitude_index[center_index])
    latitude_delta = surface.latitude_index.astype(float) - float(latitude_center)
    longitude_delta = np.abs(
        surface.longitude_index.astype(float) - float(longitude_center)
    )
    longitude_delta = np.minimum(
        longitude_delta, float(surface.longitude_cells) - longitude_delta
    )
    distance = np.sqrt((latitude_delta**2) + (longitude_delta**2))
    return np.exp(-0.5 * ((distance / max(radius_cells, 0.6)) ** 2))


def surface_kernel_scale(surface: PlanetSurface) -> float:
    return float(2 ** max(0, int(surface.subdivision_level)))


def stable_top_indices(
    score: np.ndarray, *, count: int, minimum_spacing: float, surface: PlanetSurface
) -> list[int]:
    ordered_indices = np.argsort(-score)
    chosen: list[int] = []
    for candidate_index in ordered_indices:
        latitude = int(surface.latitude_index[candidate_index])
        longitude = int(surface.longitude_index[candidate_index])
        is_far_enough = True
        for chosen_index in chosen:
            chosen_latitude = int(surface.latitude_index[chosen_index])
            chosen_longitude = int(surface.longitude_index[chosen_index])
            latitude_distance = abs(latitude - chosen_latitude)
            longitude_distance = abs(longitude - chosen_longitude)
            longitude_distance = min(
                longitude_distance,
                int(surface.longitude_cells) - longitude_distance,
            )
            distance = math.sqrt(
                (float(latitude_distance) ** 2) + (float(longitude_distance) ** 2)
            )
            if distance < minimum_spacing:
                is_far_enough = False
                break
        if is_far_enough:
            chosen.append(int(candidate_index))
        if len(chosen) >= count:
            break
    return chosen


def hotspot_centers_for_surface(
    surface: PlanetSurface, state: VolcanicImpactResurfacingState, seed: int
) -> list[int]:
    kernel_scale = surface_kernel_scale(surface)
    rng = np.random.default_rng(seed)
    score = (
        (0.40 * surface.upwelling_tendency)
        + (0.25 * surface.crust_creation_tendency)
        + (0.15 * normalized(np.maximum(-surface.elevation, 0.0)))
        + (
            0.20
            * np.isin(
                surface.boundary_role,
                np.asarray(["spreading_boundary", "ambiguous"]),
            ).astype(float)
        )
    )
    score += rng.random(score.shape[0]) * 0.05
    count = max(1, state.hotspot_count + state.flood_basalt_event_count)
    return stable_top_indices(
        score, count=count, minimum_spacing=5.0 * kernel_scale, surface=surface
    )


def impact_centers_for_surface(
    surface: PlanetSurface, state: VolcanicImpactResurfacingState, seed: int
) -> list[int]:
    kernel_scale = surface_kernel_scale(surface)
    rng = np.random.default_rng(seed)
    score = (
        (0.45 * normalized(np.maximum(-surface.elevation, 0.0)))
        + (0.25 * normalized(surface.basin_index))
        + (0.20 * (1.0 - normalized(surface.volcanic_hotspot)))
        + (0.10 * normalized(surface.regolith_depth + 1.0))
    )
    score += rng.random(score.shape[0]) * 0.08
    count = max(2, int(round(float(state.major_crater_rate_per_gyr) / 10.0)))
    return stable_top_indices(
        score, count=count, minimum_spacing=4.0 * kernel_scale, surface=surface
    )


def build_resurfacing_surface(
    topography_surface: PlanetSurface, state: VolcanicImpactResurfacingState
) -> PlanetSurface:
    surface = deep_copy_surface(topography_surface)
    kernel_scale = surface_kernel_scale(surface)
    hotspot_seed = 9_700_003 + (state.step_index * 23)
    impact_seed = 11_300_027 + (state.step_index * 29)
    hotspot_centers = hotspot_centers_for_surface(surface, state, hotspot_seed)

    hotspot_field = np.zeros(surface.region_ids.shape[0], dtype=float)
    for center_index in hotspot_centers:
        hotspot_field += gaussian_blob_on_grid(
            surface,
            center_index,
            radius_cells=kernel_scale * (2.8 + (2.2 * float(state.hotspot_activity_index))),
        )
    hotspot_field = np.clip(hotspot_field, 0.0, None)
    hotspot_field = normalized(hotspot_field)

    broad_hotspot_field = np.zeros(surface.region_ids.shape[0], dtype=float)
    for center_index in hotspot_centers[: max(1, state.flood_basalt_event_count)]:
        broad_hotspot_field += gaussian_blob_on_grid(
            surface,
            center_index,
            radius_cells=kernel_scale * (5.0 + (2.0 * float(state.flood_basalt_intensity_index))),
        )
    broad_hotspot_field = normalized(np.clip(broad_hotspot_field, 0.0, None))

    surface.volcanic_hotspot = np.clip(
        (0.72 * hotspot_field) + (0.28 * broad_hotspot_field), 0.0, 1.0
    )
    surface.elevation += surface.volcanic_hotspot * (
        350.0
        + (1300.0 * float(state.hotspot_activity_index))
        + (700.0 * float(state.flood_basalt_intensity_index))
    )
    surface.regolith_depth *= 1.0 - (0.92 * surface.volcanic_hotspot)
    surface.temperature += 35.0 * surface.volcanic_hotspot

    impact_centers = impact_centers_for_surface(surface, state, impact_seed)
    impact_field = np.zeros(surface.region_ids.shape[0], dtype=float)
    crater_elevation_delta = np.zeros(surface.region_ids.shape[0], dtype=float)
    for crater_rank, center_index in enumerate(impact_centers):
        radius_cells = kernel_scale * (1.8 + (0.35 * (crater_rank % 4)))
        blob = gaussian_blob_on_grid(surface, center_index, radius_cells)
        rim_blob = gaussian_blob_on_grid(surface, center_index, radius_cells * 1.7)
        crater_depth = (
            150.0
            + (800.0 * float(state.crater_persistence_fraction))
            + (420.0 * (crater_rank / max(1, len(impact_centers))))
        )
        rim_height = 0.35 * crater_depth
        crater_profile = (-crater_depth * blob) + (rim_height * rim_blob)
        crater_elevation_delta += crater_profile
        impact_field = np.maximum(impact_field, blob)

    surface.impact_intensity = np.clip(impact_field, 0.0, 1.0)
    surface.elevation += crater_elevation_delta
    surface.elevation = diffuse_scalar(
        surface.elevation, surface.neighbor_indices, iterations=2, alpha=0.12
    )
    surface.lava_coverage = np.clip(
        np.maximum(surface.lava_coverage, surface.volcanic_hotspot), 0.0, 1.0
    )
    surface.resurfacing_fraction = np.clip(
        (0.60 * surface.volcanic_hotspot) + (0.40 * surface.impact_intensity), 0.0, 1.0
    )
    surface.surface_age_proxy = np.clip(
        (surface.surface_age_proxy * (1.0 - (0.62 * surface.resurfacing_fraction)))
        + (0.28 * surface.impact_intensity),
        0.0,
        1.0,
    )
    surface.crater_density = np.clip(
        (0.68 * surface.impact_intensity) + (0.32 * surface.surface_age_proxy),
        0.0,
        1.0,
    )
    surface.basin_index = np.clip(
        surface.basin_index + (0.35 * surface.impact_intensity), 0.0, 1.0
    )
    surface.terrain_class = terrain_class_from_fields(
        surface.elevation,
        surface.boundary_influence_type,
        surface.basin_tendency,
        surface.uplift_tendency,
    )
    surface.metadata.update(
        {
            "source_layer": "09_volcanic_impact_resurfacing.py",
            "hotspot_center_region_ids": [
                str(surface.region_ids[index]) for index in hotspot_centers
            ],
            "impact_center_region_ids": [
                str(surface.region_ids[index]) for index in impact_centers
            ],
            "hotspot_seed": hotspot_seed,
            "impact_seed": impact_seed,
            "volcanic_province_fraction": float(state.volcanic_province_fraction),
            "crater_persistence_fraction": float(state.crater_persistence_fraction),
        }
    )
    return surface


def resurfacing_surface_for_index(
    index: int,
    proto_states: tuple[large_scale_topography.plate_system.proto_tectonics.ProtoTectonicsState, ...],
    plate_states: tuple[large_scale_topography.plate_system.PlateSystemState, ...],
    topography_states: tuple[large_scale_topography.LargeScaleTopographyState, ...],
    temperature_states: tuple[large_scale_topography.surface_temperature.SurfaceTemperatureState, ...],
    resurfacing_states: tuple[VolcanicImpactResurfacingState, ...],
    resolution: tuple[int, int],
    cache: dict[int, PlanetSurface],
) -> PlanetSurface:
    if index not in cache:
        base_surface = large_scale_topography.topography_surface_for_index(
            index,
            proto_states,
            plate_states,
            topography_states,
            temperature_states,
            resolution,
            {},
        )
        cache[index] = build_resurfacing_surface(base_surface, resurfacing_states[index])
    return cache[index]


def write_resurfacing_map_png(
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
            "Resurfacing visualization requires matplotlib. Install dependencies "
            "with `python3 -m pip install -r requirements.txt`."
        ) from exc

    figure, axis = plt.subplots(figsize=(16.6, 9.2), facecolor="#f6f1e8")
    axis.set_facecolor("#fffdf8")
    elevation_grid = surface.elevation.reshape(
        surface.latitude_cells, surface.longitude_cells
    )
    image = axis.imshow(
        elevation_grid,
        origin="lower",
        extent=(-180, 180, -90, 90),
        aspect="auto",
        cmap="terrain",
        interpolation="nearest",
    )
    colorbar = figure.colorbar(image, ax=axis, pad=0.02, fraction=0.04)
    colorbar.set_label("Elevation (m)", color="#1f2937")
    colorbar.ax.tick_params(colors="#6b7280")

    hotspot_grid = surface.volcanic_hotspot.reshape(
        surface.latitude_cells, surface.longitude_cells
    )
    axis.contour(
        hotspot_grid,
        levels=[0.35, 0.55, 0.75],
        colors=["#ffb703", "#fb8500", "#d62828"],
        linewidths=[1.0, 1.2, 1.5],
        origin="lower",
        extent=(-180, 180, -90, 90),
        zorder=3,
    )

    impact_indices = np.where(surface.impact_intensity >= 0.55)[0]
    axis.scatter(
        surface.center_longitude_degrees[impact_indices],
        surface.center_latitude_degrees[impact_indices],
        s=18,
        facecolors="none",
        edgecolors="#f8fafc",
        linewidths=0.8,
        zorder=4,
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
    axis.grid(color="#d7d2c8", linewidth=0.5, alpha=0.18)
    for spine in axis.spines.values():
        spine.set_color("#d7d2c8")

    legend_handles = [
        Line2D([0], [0], color="#fb8500", lw=2.0, label="Volcanic hotspot contours"),
        Line2D(
            [0],
            [0],
            marker="o",
            color="#f8fafc",
            markerfacecolor="none",
            lw=0.0,
            markersize=6,
            label="Impact sites",
        ),
    ]
    legend = axis.legend(
        handles=legend_handles,
        title="Resurfacing",
        loc="center left",
        bbox_to_anchor=(1.01, 0.82),
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


def write_resurfacing_artifacts(
    proto_states: tuple[large_scale_topography.plate_system.proto_tectonics.ProtoTectonicsState, ...],
    plate_states: tuple[large_scale_topography.plate_system.PlateSystemState, ...],
    topography_states: tuple[large_scale_topography.LargeScaleTopographyState, ...],
    temperature_states: tuple[large_scale_topography.surface_temperature.SurfaceTemperatureState, ...],
    resurfacing_states: tuple[VolcanicImpactResurfacingState, ...],
    resolution: tuple[int, int],
    current_file: str,
    cache: dict[int, PlanetSurface],
) -> Path | None:
    if not resurfacing_states:
        return None

    present_surface = resurfacing_surface_for_index(
        len(resurfacing_states) - 1,
        proto_states,
        plate_states,
        topography_states,
        temperature_states,
        resurfacing_states,
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
    write_resurfacing_map_png(
        present_surface,
        resurfacing_present_output_path(current_file),
        title="09 Volcanic / Impact Resurfacing: Present-Day Surface",
        subtitle=(
            f"Equirectangular projection, "
            f"{present_surface.longitude_cells}x{present_surface.latitude_cells} "
            "shared surface cells with volcanic and impact overlays."
        ),
    )
    frames_dir = clear_frame_directory(frame_output_dir(
        current_file,
        FRAME_DIRECTORY_NAME,
        present_surface.longitude_cells,
        present_surface.latitude_cells,
    ))
    for index in frame_sample_indices(len(resurfacing_states)):
        frame_surface = resurfacing_surface_for_index(
            index,
            proto_states,
            plate_states,
            topography_states,
            temperature_states,
            resurfacing_states,
            resolution,
            cache,
        )
        write_resurfacing_map_png(
            frame_surface,
            frames_dir / f"frame_{frame_surface.step_index:04d}.png",
            title="09 Volcanic / Impact Resurfacing",
            subtitle=(
                f"Timestep {frame_surface.step_index}, age "
                f"{frame_surface.age_years / 1_000_000.0:.1f} Myr."
            ),
        )
    return state_path


def build_resurfacing_surface_extra(
    surface: PlanetSurface,
    *,
    current_file: str,
    state_path: Path,
    tectonic_resolution: tuple[int, int],
) -> dict[str, object]:
    terrain_payload = surface_json_payload(
        surface,
        state_path=state_path,
        frame_directory=frame_output_dir(
            current_file,
            FRAME_DIRECTORY_NAME,
            surface.longitude_cells,
            surface.latitude_cells,
        ),
    )
    return {
        "tectonic_mesh_reference": {
            "state_path": str(
                surface_state_output_path(
                    large_scale_topography.plate_system.__file__,
                    tectonic_resolution[0],
                    tectonic_resolution[1],
                )
            ),
            "surface_grid_resolution": (
                f"{tectonic_resolution[0]}x{tectonic_resolution[1]}"
            ),
            "mesh_level": "tectonic_mesh",
        },
        "terrain_mesh": terrain_payload,
        "surface_geometry": terrain_payload,
        "surface_summary": {
            "mean_elevation_m": float(np.mean(surface.elevation)),
            "volcanic_hotspot_fraction": float(np.mean(surface.volcanic_hotspot >= 0.40)),
            "impact_cell_fraction": float(np.mean(surface.impact_intensity >= 0.40)),
            "mean_surface_temperature_c": float(np.mean(surface.temperature)),
        },
    }


def simulate(
    criteria: planet.SimulationCriteria,
    surface_grid_resolution: tuple[int, int] | None = None,
) -> Iterable[VolcanicImpactResurfacingState]:
    resolution = surface_grid_resolution or large_scale_topography.plate_system.parse_surface_grid_resolution(
        large_scale_topography.plate_system.DEFAULT_SURFACE_GRID_RESOLUTION
    )
    proto_states = tuple(large_scale_topography.plate_system.proto_tectonics.simulate(criteria, resolution))
    plate_states = tuple(large_scale_topography.plate_system.simulate(criteria, resolution))
    topography_states = tuple(large_scale_topography.simulate(criteria, resolution))
    temperature_states = tuple(large_scale_topography.surface_temperature.simulate(criteria))

    def build_states() -> Iterable[VolcanicImpactResurfacingState]:
        for base_state in topography_states:
            yield volcanic_impact_resurfacing_state_from_topography_state(base_state)

    surface_cache: dict[int, PlanetSurface] = {}

    def extra_builder(
        states: tuple[VolcanicImpactResurfacingState, ...],
    ) -> dict[str, object] | None:
        if not states:
            return None
        present_surface = resurfacing_surface_for_index(
            len(states) - 1,
            proto_states,
            plate_states,
            topography_states,
            temperature_states,
            states,
            resolution,
            surface_cache,
        )
        state_path = surface_state_output_path(
            __file__,
            present_surface.longitude_cells,
            present_surface.latitude_cells,
        )
        return build_resurfacing_surface_extra(
            present_surface,
            current_file=__file__,
            state_path=state_path,
            tectonic_resolution=resolution,
        )

    return materialize_layer_states(
        __file__,
        criteria,
        build_states,
        extra_builder=extra_builder,
        artifact_key=resurfacing_surface_artifact_key(resolution),
        artifact_writer=lambda states: write_resurfacing_artifacts(
            proto_states,
            plate_states,
            topography_states,
            temperature_states,
            states,
            resolution,
            __file__,
            surface_cache,
        ),
    )


def first_ancient_scarred_state(
    states: Iterable[VolcanicImpactResurfacingState],
) -> VolcanicImpactResurfacingState | None:
    for state in states:
        if state.scar_state == "ancient_scarred_world":
            return state
    return None


def validate_model(
    surface_grid_resolution: tuple[int, int] | None = None,
) -> None:
    resolution = surface_grid_resolution or large_scale_topography.plate_system.parse_surface_grid_resolution(
        large_scale_topography.plate_system.DEFAULT_SURFACE_GRID_RESOLUTION
    )
    large_scale_topography.validate_model(resolution)
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria, resolution))
    initial_state = states[0]
    present_state = states[-1]
    first_scarred_state = first_ancient_scarred_state(states)
    present_feature_types = {feature.feature_type for feature in present_state.features}
    terrain_resolution = subdivided_surface_grid_resolution(resolution)
    surface = load_planet_surface(
        surface_state_output_path(
            __file__, terrain_resolution[0], terrain_resolution[1]
        )
    )

    if initial_state.hotspot_count < 1:
        raise ValueError("Early resurfacing should include at least one hotspot track.")
    if present_state.flood_basalt_event_count < 1:
        raise ValueError("Present-day resurfacing should retain episodic flood basalts.")
    if present_state.volcanic_province_fraction <= Decimal("0.10"):
        raise ValueError("Present-day Aeron should sustain major volcanic provinces.")
    if present_state.crater_persistence_fraction <= Decimal("0.40"):
        raise ValueError("Present-day Aeron should preserve substantial crater fields.")
    if present_state.old_crust_survival_fraction <= Decimal("0.35"):
        raise ValueError("Present-day Aeron should preserve significant old crust.")
    if present_state.resurfacing_rate_km2_per_yr <= Decimal("0.5"):
        raise ValueError("Present-day resurfacing rate should remain geologically active.")
    if {"hotspot_track", "flood_basalt_province", "volcanic_province", "crater_field"} - present_feature_types:
        raise ValueError("Present-day resurfacing must include all requested feature classes.")
    if first_scarred_state is None:
        raise ValueError("An ancient scarred-world state must emerge within the span.")
    if surface.mesh_level != "terrain_mesh":
        raise ValueError("Resurfacing must continue on the refined terrain mesh.")
    if float(np.mean(surface.volcanic_hotspot >= 0.40)) <= 0.01:
        raise ValueError("Present-day resurfacing surface should expose volcanic hotspots.")
    if float(np.mean(surface.impact_intensity >= 0.35)) <= 0.01:
        raise ValueError("Present-day resurfacing surface should preserve crater fields.")


def print_input_criteria(
    criteria: planet.SimulationCriteria, surface_grid_resolution: tuple[int, int]
) -> None:
    lon_cells, lat_cells = surface_grid_resolution
    fields = [
        ("layer_name", "volcanic_and_impact_resurfacing"),
        ("large_scale_topography_source", "08_large_scale_topography.py"),
        ("plate_system_source", "07_plate_system.py"),
        ("proto_tectonics_source", "06_proto_tectonics.py"),
        ("surface_temperature_source", "05_surface_temperature.py"),
        ("early_atmosphere_source", "04_early_atmosphere.py"),
        ("primary_crust_source", "03_primary_crust.py"),
        ("interior_source", "02_interior.py"),
        ("planet_source", "01_planet.py"),
        ("coupled_topography_layer", "true"),
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
            planet.format_decimal(
                Decimal(criteria.step_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
        ("shared_surface_geometry", "true"),
        ("surface_grid_resolution", f"{lon_cells}x{lat_cells}"),
        ("surface_state_contract", "PlanetSurface"),
        ("volcanic_model", "hotspot_plus_flood_basalt_plus_province_scaling"),
        ("impact_model", "time_decay_plus_persistence_by_reworking"),
        ("resurfacing_model", "fractional_surface_reworking"),
        (
            "dynamic_fields",
            "hotspot_count, hotspot_activity_index, flood_basalt_event_count, "
            "flood_basalt_intensity_index, volcanic_province_fraction, "
            "major_crater_rate_per_gyr, crater_persistence_fraction, "
            "resurfacing_fraction_per_gyr, resurfacing_rate_km2_per_yr, "
            "old_crust_survival_fraction, scar_state",
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
        ("hotspots", 9),
        ("floods", 8),
        ("volc_f", 9),
        ("crater_gyr", 11),
        ("persist_f", 10),
        ("resurf_gyr", 10),
        ("resurf_km2", 11),
        ("old_f", 8),
        ("scar_state", 27),
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
            f"{state.hotspot_count:>9d} "
            f"{state.flood_basalt_event_count:>8d} "
            f"{planet.format_decimal(state.volcanic_province_fraction, 3):>9} "
            f"{planet.format_decimal(state.major_crater_rate_per_gyr, 3):>11} "
            f"{planet.format_decimal(state.crater_persistence_fraction, 3):>10} "
            f"{planet.format_decimal(state.resurfacing_fraction_per_gyr, 6):>10} "
            f"{planet.format_decimal(state.resurfacing_rate_km2_per_yr, 3):>11} "
            f"{planet.format_decimal(state.old_crust_survival_fraction, 3):>8} "
            f"{state.scar_state:>27}"
        )


def print_present_day_summary(
    criteria: planet.SimulationCriteria, surface_grid_resolution: tuple[int, int]
) -> None:
    states = list(simulate(criteria, surface_grid_resolution))
    final_state = states[-1]
    first_scarred_state = first_ancient_scarred_state(states)
    terrain_resolution = subdivided_surface_grid_resolution(surface_grid_resolution)
    surface = load_planet_surface(
        surface_state_output_path(
            __file__, terrain_resolution[0], terrain_resolution[1]
        )
    )

    assert first_scarred_state is not None

    fields = [
        ("world_class", final_state.world_class),
        ("tectonic_regime", final_state.tectonic_regime),
        ("hotspot_count", str(final_state.hotspot_count)),
        (
            "hotspot_activity_index",
            planet.format_decimal(final_state.hotspot_activity_index, 6),
        ),
        ("flood_basalt_event_count", str(final_state.flood_basalt_event_count)),
        (
            "flood_basalt_intensity_index",
            planet.format_decimal(final_state.flood_basalt_intensity_index, 6),
        ),
        (
            "volcanic_province_fraction",
            planet.format_decimal(final_state.volcanic_province_fraction, 6),
        ),
        (
            "major_crater_rate_per_gyr",
            planet.format_decimal(final_state.major_crater_rate_per_gyr, 6),
        ),
        (
            "crater_persistence_fraction",
            planet.format_decimal(final_state.crater_persistence_fraction, 6),
        ),
        (
            "resurfacing_fraction_per_gyr",
            planet.format_decimal(final_state.resurfacing_fraction_per_gyr, 6),
        ),
        (
            "resurfacing_rate_km2_per_yr",
            planet.format_decimal(final_state.resurfacing_rate_km2_per_yr, 6),
        ),
        (
            "old_crust_survival_fraction",
            planet.format_decimal(final_state.old_crust_survival_fraction, 6),
        ),
        ("scar_state", final_state.scar_state),
        ("surface_region_count", str(surface.region_ids.shape[0])),
        ("surface_mesh_level", surface.mesh_level),
        ("surface_state_path", str(surface_state_output_path(
            __file__, terrain_resolution[0], terrain_resolution[1]
        ))),
        ("first_ancient_scarred_step", str(first_scarred_state.step_index)),
        (
            "first_ancient_scarred_age_myr",
            planet.format_decimal(
                Decimal(first_scarred_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT RESURFACING SUMMARY")
    print("===========================")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")

    print()
    print("PRESENT RESURFACING FEATURES")
    print("============================")
    headers = (
        ("feature", 30),
        ("type", 22),
        ("state", 12),
        ("activity", 9),
        ("area_f", 8),
        ("area_km2", 14),
        ("preserved", 10),
    )
    header_line = " ".join(f"{label:>{width}}" for label, width in headers)
    divider_line = " ".join("-" * width for _, width in headers)
    print(header_line)
    print(divider_line)
    for feature in final_state.features:
        print(
            f"{feature.feature_id:>30} "
            f"{feature.feature_type:>22} "
            f"{feature.activity_state:>12} "
            f"{planet.format_decimal(feature.activity_index, 3):>9} "
            f"{planet.format_decimal(feature.area_fraction, 3):>8} "
            f"{planet.format_decimal(feature.area_km2, 3):>14} "
            f"{planet.format_decimal(feature.preserved_fraction, 3):>10}"
        )


def main() -> int:
    args = parse_args()
    try:
        criteria = planet.build_criteria(args.step_years)
        surface_grid_resolution = large_scale_topography.plate_system.parse_surface_grid_resolution(
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
