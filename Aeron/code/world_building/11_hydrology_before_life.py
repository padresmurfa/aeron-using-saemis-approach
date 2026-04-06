#!/usr/bin/env python3
"""Deterministic hydrology-before-life simulation for Aeron."""

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
        accumulate_flow,
        clear_frame_directory,
        deep_copy_surface,
        frame_output_dir,
        frame_sample_indices,
        load_planet_surface,
        normalized,
        save_planet_surface,
        subdivided_surface_grid_resolution,
        surface_json_payload,
        surface_state_output_path,
        visualization_output_path,
    )
except ImportError:
    from world_building_support import load_pipeline_module, materialize_layer_states  # type: ignore
    from world_building_surface import (  # type: ignore
        PlanetSurface,
        accumulate_flow,
        clear_frame_directory,
        deep_copy_surface,
        frame_output_dir,
        frame_sample_indices,
        load_planet_surface,
        normalized,
        save_planet_surface,
        subdivided_surface_grid_resolution,
        surface_json_payload,
        surface_state_output_path,
        visualization_output_path,
    )

basic_regolith_weathering = load_pipeline_module(
    __package__, __file__, "10_basic_regolith_weathering"
)
early_atmosphere = load_pipeline_module(__package__, __file__, "04_early_atmosphere")
large_scale_topography = load_pipeline_module(
    __package__, __file__, "08_large_scale_topography"
)
planet = load_pipeline_module(__package__, __file__, "01_planet")
surface_temperature = load_pipeline_module(
    __package__, __file__, "05_surface_temperature"
)

getcontext().prec = 50

VALIDATION_STEP_YEARS = 100_000_000
FRAME_DIRECTORY_NAME = "11_hydrology"


@dataclass(frozen=True)
class HydrologyFeatureTemplate:
    feature_id: str
    hydro_type: str
    source_feature_id: str
    driver_kind: str
    source_relation: str


@dataclass(frozen=True)
class HydrologyFeatureState:
    feature_id: str
    hydro_type: str
    source_feature_id: str
    source_feature_type: str
    hydrology_state: str
    activity_index: Decimal
    area_fraction: Decimal
    area_km2: Decimal
    water_fraction: Decimal
    ice_fraction: Decimal
    fill_fraction: Decimal


@dataclass(frozen=True)
class HydrologyBeforeLifeState:
    step_index: int
    age_years: int
    radius_km: Decimal
    surface_environment: str
    surface_temperature_regime: str
    tectonic_regime: str
    stable_ocean_fraction: Decimal
    inland_sea_fraction: Decimal
    glacier_fraction: Decimal
    glacier_zone_count: int
    runoff_pathway_count: int
    basin_filling_fraction: Decimal
    hydrology_state: str
    feature_count: int
    features: tuple[HydrologyFeatureState, ...]
    world_class: str


FEATURE_TEMPLATES = (
    HydrologyFeatureTemplate(
        feature_id="western_pelagic_ocean",
        hydro_type="ocean",
        source_feature_id="western_pelagic_basin",
        driver_kind="ocean",
        source_relation="basin_waterbody",
    ),
    HydrologyFeatureTemplate(
        feature_id="southern_pelagic_ocean",
        hydro_type="ocean",
        source_feature_id="southern_pelagic_basin",
        driver_kind="ocean",
        source_relation="basin_waterbody",
    ),
    HydrologyFeatureTemplate(
        feature_id="eastern_rift_inland_sea",
        hydro_type="inland_sea",
        source_feature_id="eastern_rift_system",
        driver_kind="inland_sea",
        source_relation="rift_basin_pooling",
    ),
    HydrologyFeatureTemplate(
        feature_id="pelagic_lowland_inland_sea",
        hydro_type="inland_sea",
        source_feature_id="pelagic_lowland_troughs",
        driver_kind="inland_sea",
        source_relation="lowland_pooling",
    ),
    HydrologyFeatureTemplate(
        feature_id="boreal_highland_glacier_zone",
        hydro_type="glacier_zone",
        source_feature_id="boreal_highlands",
        driver_kind="glacier_zone",
        source_relation="highland_cryosphere",
    ),
    HydrologyFeatureTemplate(
        feature_id="austral_uplift_glacier_zone",
        hydro_type="glacier_zone",
        source_feature_id="austral_uplift_belt",
        driver_kind="glacier_zone",
        source_relation="uplift_cryosphere",
    ),
    HydrologyFeatureTemplate(
        feature_id="boreal_runoff_network",
        hydro_type="runoff_pathway",
        source_feature_id="boreal_proto_continent",
        driver_kind="runoff_pathway",
        source_relation="continental_drainage",
    ),
    HydrologyFeatureTemplate(
        feature_id="austral_runoff_network",
        hydro_type="runoff_pathway",
        source_feature_id="austral_proto_continent",
        driver_kind="runoff_pathway",
        source_relation="continental_drainage",
    ),
    HydrologyFeatureTemplate(
        feature_id="highland_runoff_fans",
        hydro_type="runoff_pathway",
        source_feature_id="boreal_highlands",
        driver_kind="runoff_pathway",
        source_relation="high_relief_runoff",
    ),
    HydrologyFeatureTemplate(
        feature_id="western_basin_fill",
        hydro_type="basin_fill",
        source_feature_id="western_pelagic_basin",
        driver_kind="basin_fill",
        source_relation="sediment_and_water_fill",
    ),
    HydrologyFeatureTemplate(
        feature_id="southern_basin_fill",
        hydro_type="basin_fill",
        source_feature_id="southern_pelagic_basin",
        driver_kind="basin_fill",
        source_relation="sediment_and_water_fill",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's hydrology-before-life layer by ticking the basic "
            "regolith/weathering layer and deriving coarse prebiotic seas, runoff, "
            "glaciation, and basin filling from it."
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
        default=basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.DEFAULT_SURFACE_GRID_RESOLUTION,
        help=(
            "Coarse surface grid resolution as <longitude>x<latitude> cells for "
            "the inherited shared geometry. Default: "
            f"{basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.DEFAULT_SURFACE_GRID_RESOLUTION}."
        ),
    )
    return parser.parse_args()


def clamp_unit_interval(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")
    if value > Decimal("1"):
        return Decimal("1")
    return value


def topography_feature_lookup_at(
    state: large_scale_topography.LargeScaleTopographyState,
) -> dict[str, large_scale_topography.TopographyFeatureState]:
    return {feature.feature_id: feature for feature in state.features}


def area_total_at(
    state: large_scale_topography.LargeScaleTopographyState, feature_type: str
) -> Decimal:
    return sum(
        (feature.area_fraction for feature in state.features if feature.feature_type == feature_type),
        start=Decimal("0"),
    )


def basin_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(state.ocean_basin_fraction / Decimal("0.55"))


def deep_basin_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(state.deepest_basin_m / Decimal("4000"))


def continent_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(state.proto_continent_fraction / Decimal("0.20"))


def relief_factor_at(state: large_scale_topography.LargeScaleTopographyState) -> Decimal:
    return clamp_unit_interval(state.relief_contrast_m / Decimal("7000"))


def highland_support_factor_at(
    state: large_scale_topography.LargeScaleTopographyState,
) -> Decimal:
    return clamp_unit_interval(
        (area_total_at(state, "highlands") + area_total_at(state, "uplift")) / Decimal("0.10")
    )


def lowland_rift_support_factor_at(
    state: large_scale_topography.LargeScaleTopographyState,
) -> Decimal:
    return clamp_unit_interval(
        (area_total_at(state, "lowlands") + area_total_at(state, "rift")) / Decimal("0.12")
    )


def liquid_phase_factor_at(surface_liquid_state: str) -> Decimal:
    if surface_liquid_state == "stable":
        return Decimal("1.0")
    if surface_liquid_state == "transient":
        return Decimal("0.45")
    if surface_liquid_state == "frozen":
        return Decimal("0.15")
    return Decimal("0.0")


def water_supply_index_at(
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
    regolith_state: basic_regolith_weathering.BasicRegolithWeatheringState,
) -> Decimal:
    return clamp_unit_interval(
        basic_regolith_weathering.solid_surface_factor_at(atmosphere_state.surface_environment)
        * (
            (Decimal("0.40") * basic_regolith_weathering.moisture_factor_at(atmosphere_state, temperature_state))
            + (Decimal("0.20") * basic_regolith_weathering.pressure_factor_at(atmosphere_state.atmospheric_pressure_bar))
            + (Decimal("0.20") * basic_regolith_weathering.surface_liquid_support_at(temperature_state.surface_liquid_state))
            + (Decimal("0.20") * regolith_state.regolith_coverage_fraction)
        )
    )


def ocean_stability_index_at(
    topography_state: large_scale_topography.LargeScaleTopographyState,
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
    regolith_state: basic_regolith_weathering.BasicRegolithWeatheringState,
) -> Decimal:
    liquid_phase = liquid_phase_factor_at(temperature_state.surface_liquid_state)
    if liquid_phase == Decimal("0"):
        return Decimal("0")
    water_supply = water_supply_index_at(atmosphere_state, temperature_state, regolith_state)
    return liquid_phase * clamp_unit_interval(
        (Decimal("0.35") * basin_factor_at(topography_state))
        + (Decimal("0.20") * deep_basin_factor_at(topography_state))
        + (Decimal("0.20") * water_supply)
        + (Decimal("0.15") * basic_regolith_weathering.pressure_factor_at(atmosphere_state.atmospheric_pressure_bar))
        + (Decimal("0.10") * regolith_state.regolith_coverage_fraction)
    )


def runoff_support_index_at(
    topography_state: large_scale_topography.LargeScaleTopographyState,
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.35") * basic_regolith_weathering.moisture_factor_at(atmosphere_state, temperature_state))
        + (Decimal("0.25") * relief_factor_at(topography_state))
        + (Decimal("0.20") * continent_factor_at(topography_state))
        + (Decimal("0.20") * basic_regolith_weathering.surface_liquid_support_at(temperature_state.surface_liquid_state))
    )


def inland_sea_index_at(
    topography_state: large_scale_topography.LargeScaleTopographyState,
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
    regolith_state: basic_regolith_weathering.BasicRegolithWeatheringState,
) -> Decimal:
    liquid_phase = liquid_phase_factor_at(temperature_state.surface_liquid_state)
    if liquid_phase == Decimal("0"):
        return Decimal("0")
    water_supply = water_supply_index_at(atmosphere_state, temperature_state, regolith_state)
    runoff_support = runoff_support_index_at(topography_state, atmosphere_state, temperature_state)
    return liquid_phase * clamp_unit_interval(
        (Decimal("0.35") * water_supply)
        + (Decimal("0.25") * lowland_rift_support_factor_at(topography_state))
        + (Decimal("0.20") * runoff_support)
        + (Decimal("0.20") * deep_basin_factor_at(topography_state))
    )


def local_cryosphere_temp_c_at(
    source_relief_m: Decimal,
    temperature_state: surface_temperature.SurfaceTemperatureState,
) -> Decimal:
    polar_proxy_temp_c = temperature_state.mean_surface_temp_c - (
        temperature_state.equator_to_pole_delta_c * Decimal("0.90")
    )
    elevation_cooling_c = (abs(source_relief_m) / Decimal("1000")) * Decimal("6.8")
    seasonal_bonus_c = Decimal("4") if planet.AXIAL_TILT_STATE == "seasonal" else Decimal("0")
    return polar_proxy_temp_c - elevation_cooling_c - seasonal_bonus_c


def glacier_index_for_feature_at(
    source_feature: large_scale_topography.TopographyFeatureState,
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
) -> Decimal:
    if temperature_state.surface_liquid_state not in {"stable", "transient", "frozen"}:
        return Decimal("0")
    local_cryosphere_temp_c = local_cryosphere_temp_c_at(
        source_feature.relief_m, temperature_state
    )
    freeze_factor = clamp_unit_interval(
        (Decimal("8") - local_cryosphere_temp_c) / Decimal("22")
    )
    local_support = clamp_unit_interval(source_feature.area_fraction / Decimal("0.06"))
    return clamp_unit_interval(
        (Decimal("0.45") * freeze_factor)
        + (Decimal("0.30") * basic_regolith_weathering.moisture_factor_at(atmosphere_state, temperature_state))
        + (Decimal("0.25") * local_support)
    )


def basin_fill_index_at(
    topography_state: large_scale_topography.LargeScaleTopographyState,
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
    regolith_state: basic_regolith_weathering.BasicRegolithWeatheringState,
) -> Decimal:
    liquid_phase = liquid_phase_factor_at(temperature_state.surface_liquid_state)
    if liquid_phase == Decimal("0"):
        return Decimal("0")
    return clamp_unit_interval(
        liquid_phase
        * (
            (Decimal("0.40") * regolith_state.sediment_accumulation_fraction)
            + (Decimal("0.25") * runoff_support_index_at(topography_state, atmosphere_state, temperature_state))
            + (Decimal("0.20") * ocean_stability_index_at(topography_state, atmosphere_state, temperature_state, regolith_state))
            + (Decimal("0.15") * deep_basin_factor_at(topography_state))
        )
    )


def source_area_factor_at(
    source_feature: large_scale_topography.TopographyFeatureState,
) -> Decimal:
    return clamp_unit_interval(source_feature.area_fraction / Decimal("0.10"))


def hydrology_state_for_feature_at(
    hydro_type: str,
    activity_index: Decimal,
    water_fraction: Decimal,
    ice_fraction: Decimal,
    fill_fraction: Decimal,
) -> str:
    if hydro_type == "ocean":
        if water_fraction >= Decimal("0.60"):
            return "stable"
        if water_fraction >= Decimal("0.25"):
            return "seasonal"
        return "dry"
    if hydro_type == "inland_sea":
        if water_fraction >= Decimal("0.50"):
            return "persistent"
        if water_fraction >= Decimal("0.20"):
            return "episodic"
        return "dry"
    if hydro_type == "glacier_zone":
        if ice_fraction >= Decimal("0.55"):
            return "perennial"
        if ice_fraction >= Decimal("0.25"):
            return "seasonal"
        return "bare"
    if hydro_type == "runoff_pathway":
        if activity_index >= Decimal("0.60"):
            return "integrated"
        if activity_index >= Decimal("0.30"):
            return "channelized"
        return "inactive"
    if fill_fraction >= Decimal("0.65"):
        return "aggrading"
    if fill_fraction >= Decimal("0.30"):
        return "partly_filled"
    return "open"


def hydrology_features_at(
    topography_state: large_scale_topography.LargeScaleTopographyState,
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
    regolith_state: basic_regolith_weathering.BasicRegolithWeatheringState,
) -> tuple[HydrologyFeatureState, ...]:
    source_features = topography_feature_lookup_at(topography_state)
    surface_area_km2 = Decimal("4") * planet.PI * (topography_state.radius_km**2)
    ocean_stability_index = ocean_stability_index_at(
        topography_state, atmosphere_state, temperature_state, regolith_state
    )
    inland_sea_index = inland_sea_index_at(
        topography_state, atmosphere_state, temperature_state, regolith_state
    )
    runoff_support = runoff_support_index_at(
        topography_state, atmosphere_state, temperature_state
    )
    basin_fill_index = basin_fill_index_at(
        topography_state, atmosphere_state, temperature_state, regolith_state
    )
    features: list[HydrologyFeatureState] = []

    for template in FEATURE_TEMPLATES:
        source_feature = source_features.get(template.source_feature_id)
        if source_feature is None:
            continue

        local_support = source_area_factor_at(source_feature)

        if template.driver_kind == "ocean":
            activity_index = clamp_unit_interval(
                ocean_stability_index * (Decimal("0.70") + (Decimal("0.30") * local_support))
            )
            water_fraction = activity_index
            ice_fraction = Decimal("0")
            fill_fraction = Decimal("0")
            area_fraction = source_feature.area_fraction * (
                Decimal("0.50") + (Decimal("0.40") * activity_index)
            )
        elif template.driver_kind == "inland_sea":
            activity_index = clamp_unit_interval(
                inland_sea_index * (Decimal("0.60") + (Decimal("0.40") * local_support))
            )
            water_fraction = activity_index
            ice_fraction = Decimal("0")
            fill_fraction = Decimal("0")
            area_fraction = source_feature.area_fraction * (
                Decimal("0.16") + (Decimal("0.30") * activity_index)
            )
        elif template.driver_kind == "glacier_zone":
            activity_index = glacier_index_for_feature_at(
                source_feature, atmosphere_state, temperature_state
            )
            water_fraction = Decimal("0")
            ice_fraction = activity_index
            fill_fraction = Decimal("0")
            area_fraction = source_feature.area_fraction * (
                Decimal("0.10") + (Decimal("0.45") * activity_index)
            )
        elif template.driver_kind == "runoff_pathway":
            activity_index = clamp_unit_interval(
                runoff_support * (Decimal("0.65") + (Decimal("0.35") * local_support))
            )
            water_fraction = activity_index
            ice_fraction = Decimal("0")
            fill_fraction = Decimal("0")
            area_fraction = source_feature.area_fraction * (
                Decimal("0.10") + (Decimal("0.18") * activity_index)
            )
        else:
            activity_index = clamp_unit_interval(
                basin_fill_index * (Decimal("0.65") + (Decimal("0.35") * local_support))
            )
            water_fraction = ocean_stability_index * (
                Decimal("0.55") + (Decimal("0.25") * local_support)
            )
            ice_fraction = Decimal("0")
            fill_fraction = activity_index
            area_fraction = source_feature.area_fraction

        features.append(
            HydrologyFeatureState(
                feature_id=template.feature_id,
                hydro_type=template.hydro_type,
                source_feature_id=template.source_feature_id,
                source_feature_type=source_feature.feature_type,
                hydrology_state=hydrology_state_for_feature_at(
                    template.hydro_type,
                    activity_index,
                    water_fraction,
                    ice_fraction,
                    fill_fraction,
                ),
                activity_index=activity_index,
                area_fraction=area_fraction,
                area_km2=surface_area_km2 * area_fraction,
                water_fraction=water_fraction,
                ice_fraction=ice_fraction,
                fill_fraction=fill_fraction,
            )
        )

    return tuple(features)


def stable_ocean_fraction_at(features: tuple[HydrologyFeatureState, ...]) -> Decimal:
    return sum(
        (
            feature.area_fraction * feature.water_fraction
            for feature in features
            if feature.hydro_type == "ocean"
        ),
        start=Decimal("0"),
    )


def inland_sea_fraction_at(features: tuple[HydrologyFeatureState, ...]) -> Decimal:
    return sum(
        (
            feature.area_fraction * feature.water_fraction
            for feature in features
            if feature.hydro_type == "inland_sea"
        ),
        start=Decimal("0"),
    )


def glacier_fraction_at(features: tuple[HydrologyFeatureState, ...]) -> Decimal:
    return sum(
        (
            feature.area_fraction * feature.ice_fraction
            for feature in features
            if feature.hydro_type == "glacier_zone"
        ),
        start=Decimal("0"),
    )


def glacier_zone_count_at(features: tuple[HydrologyFeatureState, ...]) -> int:
    return sum(
        1
        for feature in features
        if feature.hydro_type == "glacier_zone"
        and feature.hydrology_state in {"perennial", "seasonal"}
    )


def runoff_pathway_count_at(features: tuple[HydrologyFeatureState, ...]) -> int:
    return sum(
        1
        for feature in features
        if feature.hydro_type == "runoff_pathway"
        and feature.hydrology_state in {"integrated", "channelized"}
    )


def basin_filling_fraction_at(features: tuple[HydrologyFeatureState, ...]) -> Decimal:
    basin_features = [feature for feature in features if feature.hydro_type == "basin_fill"]
    total_area = sum((feature.area_fraction for feature in basin_features), start=Decimal("0"))
    if total_area == Decimal("0"):
        return Decimal("0")
    return sum(
        (feature.area_fraction * feature.fill_fraction for feature in basin_features),
        start=Decimal("0"),
    ) / total_area


def hydrology_state_at(
    surface_environment: str,
    stable_ocean_fraction: Decimal,
    inland_sea_fraction: Decimal,
    glacier_fraction: Decimal,
    runoff_pathway_count: int,
) -> str:
    if surface_environment == "lava":
        return "dry_magmatic_world"
    if surface_environment == "steam" and stable_ocean_fraction < Decimal("0.03"):
        return "steam_condensate_world"
    if stable_ocean_fraction >= Decimal("0.18") and glacier_fraction >= Decimal("0.01"):
        return "rain_sea_ice_world"
    if stable_ocean_fraction >= Decimal("0.18") and runoff_pathway_count >= 2:
        return "rain_sea_world"
    if inland_sea_fraction >= Decimal("0.03"):
        return "inland_sea_barrens"
    return "fragmentary_wet_barrens"


def hydrology_before_life_state_from_inputs(
    topography_state: large_scale_topography.LargeScaleTopographyState,
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
    regolith_state: basic_regolith_weathering.BasicRegolithWeatheringState,
) -> HydrologyBeforeLifeState:
    features = hydrology_features_at(
        topography_state, atmosphere_state, temperature_state, regolith_state
    )
    stable_ocean_fraction = stable_ocean_fraction_at(features)
    inland_sea_fraction = inland_sea_fraction_at(features)
    glacier_fraction = glacier_fraction_at(features)
    runoff_pathway_count = runoff_pathway_count_at(features)
    return HydrologyBeforeLifeState(
        step_index=topography_state.step_index,
        age_years=topography_state.age_years,
        radius_km=topography_state.radius_km,
        surface_environment=atmosphere_state.surface_environment,
        surface_temperature_regime=temperature_state.surface_temperature_regime,
        tectonic_regime=topography_state.tectonic_regime,
        stable_ocean_fraction=stable_ocean_fraction,
        inland_sea_fraction=inland_sea_fraction,
        glacier_fraction=glacier_fraction,
        glacier_zone_count=glacier_zone_count_at(features),
        runoff_pathway_count=runoff_pathway_count,
        basin_filling_fraction=basin_filling_fraction_at(features),
        hydrology_state=hydrology_state_at(
            atmosphere_state.surface_environment,
            stable_ocean_fraction,
            inland_sea_fraction,
            glacier_fraction,
            runoff_pathway_count,
        ),
        feature_count=len(features),
        features=features,
        world_class=topography_state.world_class,
    )


def hydrology_surface_artifact_key(resolution: tuple[int, int]) -> str:
    return (
        "hydrology_surface:"
        f"{basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.surface_grid_resolution_label(resolution)}"
    )


def hydrology_present_output_path(current_file: str) -> Path:
    return visualization_output_path(current_file, "__hydrology_present.png")


def hydrology_surface_for_index(
    index: int,
    proto_states: tuple[basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.proto_tectonics.ProtoTectonicsState, ...],
    plate_states: tuple[basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.PlateSystemState, ...],
    topography_states: tuple[large_scale_topography.LargeScaleTopographyState, ...],
    temperature_states: tuple[surface_temperature.SurfaceTemperatureState, ...],
    resurfacing_states: tuple[basic_regolith_weathering.volcanic_impact_resurfacing.VolcanicImpactResurfacingState, ...],
    regolith_states: tuple[basic_regolith_weathering.BasicRegolithWeatheringState, ...],
    hydrology_states: tuple[HydrologyBeforeLifeState, ...],
    atmosphere_states: tuple[early_atmosphere.EarlyAtmosphereState, ...],
    resolution: tuple[int, int],
    cache: dict[int, PlanetSurface],
) -> PlanetSurface:
    if index not in cache:
        regolith_surface = basic_regolith_weathering.regolith_surface_for_index(
            index,
            proto_states,
            plate_states,
            topography_states,
            temperature_states,
            resurfacing_states,
            regolith_states,
            resolution,
            {},
        )
        cache[index] = build_hydrology_surface(
            regolith_surface,
            hydrology_states[index],
            atmosphere_states[index],
            temperature_states[index],
        )
    return cache[index]


def build_hydrology_surface(
    regolith_surface: PlanetSurface,
    hydrology_state: HydrologyBeforeLifeState,
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
) -> PlanetSurface:
    surface = deep_copy_surface(regolith_surface)
    region_count = surface.region_ids.shape[0]
    target_ocean_cells = max(
        1, int(round(region_count * float(hydrology_state.stable_ocean_fraction)))
    )
    sorted_elevation = np.sort(surface.elevation)
    sea_level = float(sorted_elevation[min(target_ocean_cells - 1, region_count - 1)])
    water_depth = np.maximum(0.0, sea_level - surface.elevation)

    precipitation_support = np.clip(
        (0.35 * normalized(surface.runoff_flux + 0.01))
        + (0.30 * normalized(surface.regolith_depth + 0.01))
        + (0.20 * normalized(surface.basin_index + 0.01))
        + (
            0.15
            * (
                1.0
                if temperature_state.surface_liquid_state in {"stable", "transient"}
                else 0.0
            )
        ),
        0.0,
        1.0,
    )
    precipitation_flux = np.clip(
        precipitation_support
        * (0.45 + (0.40 * float(hydrology_state.basin_filling_fraction)))
        * (0.75 + (0.25 * float(atmosphere_state.atmospheric_pressure_bar))),
        0.0,
        None,
    )
    runoff_flow, receivers = accumulate_flow(
        surface, surface.elevation - water_depth, precipitation_flux
    )
    runoff_norm = normalized(runoff_flow)

    inland_target_cells = max(
        1, int(round(region_count * float(hydrology_state.inland_sea_fraction)))
    )
    inland_candidates = np.argsort(
        -(
            (0.45 * surface.basin_index)
            + (0.35 * runoff_norm)
            + (0.20 * normalized(np.maximum(-surface.elevation, 0.0)))
        )
    )
    inland_assigned = 0
    for candidate_index in inland_candidates:
        if inland_assigned >= inland_target_cells:
            break
        if water_depth[candidate_index] > 0.0:
            continue
        water_depth[candidate_index] = 25.0 + (220.0 * runoff_norm[candidate_index])
        inland_assigned += 1
        for receiver_index in surface.neighbor_indices[candidate_index]:
            if receiver_index < 0 or inland_assigned >= inland_target_cells:
                continue
            if water_depth[receiver_index] > 0.0:
                continue
            water_depth[receiver_index] = 10.0 + (140.0 * runoff_norm[receiver_index])
            inland_assigned += 1

    land_mask = water_depth <= 0.0
    land_runoff_norm = np.zeros_like(runoff_norm)
    if np.any(land_mask):
        land_runoff_norm[land_mask] = normalized(runoff_flow[land_mask])
    runoff_norm = np.maximum((0.30 * runoff_norm), land_runoff_norm)

    glacier_mask = (
        (surface.temperature <= 0.0)
        & (np.abs(surface.center_latitude_degrees) >= 45.0)
        & (surface.elevation >= 250.0)
    )
    water_depth[glacier_mask] *= 0.65
    runoff_norm[glacier_mask] *= 0.35

    surface.water_depth = water_depth
    surface.runoff_flux = runoff_norm
    surface.flow_receiver_index = receivers
    surface.basin_fill = np.clip(
        (0.45 * normalized(surface.water_depth + 0.01))
        + (0.35 * normalized(runoff_flow + 0.01))
        + (0.20 * normalized(surface.basin_index + 0.01)),
        0.0,
        1.0,
    )
    surface.glacier_presence = glacier_mask.astype(float)
    surface.inland_sea = (
        ((surface.water_depth > 0.0) & (surface.water_depth < np.maximum(40.0, sea_level)))
    ).astype(float)
    surface.metadata.update(
        {
            "source_layer": "11_hydrology_before_life.py",
            "hydrology_state": hydrology_state.hydrology_state,
            "stable_ocean_fraction": float(hydrology_state.stable_ocean_fraction),
            "inland_sea_fraction": float(hydrology_state.inland_sea_fraction),
            "glacier_fraction": float(hydrology_state.glacier_fraction),
            "sea_level_m": sea_level,
            "glacier_region_ids": [
                str(surface.region_ids[index]) for index in np.where(glacier_mask)[0]
            ],
        }
    )
    return surface


def write_hydrology_map_png(
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
            "Hydrology visualization requires matplotlib. Install dependencies "
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

    water_mask = np.ma.masked_less_equal(
        surface.water_depth.reshape(surface.latitude_cells, surface.longitude_cells),
        0.0,
    )
    water_image = axis.imshow(
        water_mask,
        origin="lower",
        extent=(-180, 180, -90, 90),
        aspect="auto",
        cmap="Blues",
        interpolation="nearest",
        alpha=0.70,
    )
    water_colorbar = figure.colorbar(water_image, ax=axis, pad=0.09, fraction=0.04)
    water_colorbar.set_label("Water Depth (m)", color="#1f2937")
    water_colorbar.ax.tick_params(colors="#6b7280")

    river_indices = np.where((surface.runoff_flux >= 0.55) & (surface.water_depth <= 0.0))[0]
    axis.scatter(
        surface.center_longitude_degrees[river_indices],
        surface.center_latitude_degrees[river_indices],
        s=7,
        c="#1d4ed8",
        alpha=0.75,
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

    legend = axis.legend(
        handles=[
            Line2D([0], [0], marker="o", color="#1d4ed8", lw=0.0, markersize=6, label="Runoff cells"),
        ],
        title="Hydrology",
        loc="center left",
        bbox_to_anchor=(1.01, 0.84),
        frameon=True,
    )
    legend.get_frame().set_facecolor("#fffdf8")
    legend.get_frame().set_edgecolor("#d7d2c8")
    figure.subplots_adjust(left=0.07, right=0.84, top=0.90, bottom=0.10)
    figure.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return output_path


def write_hydrology_artifacts(
    proto_states: tuple[basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.proto_tectonics.ProtoTectonicsState, ...],
    plate_states: tuple[basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.PlateSystemState, ...],
    topography_states: tuple[large_scale_topography.LargeScaleTopographyState, ...],
    temperature_states: tuple[surface_temperature.SurfaceTemperatureState, ...],
    resurfacing_states: tuple[basic_regolith_weathering.volcanic_impact_resurfacing.VolcanicImpactResurfacingState, ...],
    regolith_states: tuple[basic_regolith_weathering.BasicRegolithWeatheringState, ...],
    hydrology_states: tuple[HydrologyBeforeLifeState, ...],
    atmosphere_states: tuple[early_atmosphere.EarlyAtmosphereState, ...],
    resolution: tuple[int, int],
    current_file: str,
    cache: dict[int, PlanetSurface],
) -> Path | None:
    if not hydrology_states:
        return None

    present_surface = hydrology_surface_for_index(
        len(hydrology_states) - 1,
        proto_states,
        plate_states,
        topography_states,
        temperature_states,
        resurfacing_states,
        regolith_states,
        hydrology_states,
        atmosphere_states,
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
    write_hydrology_map_png(
        present_surface,
        hydrology_present_output_path(current_file),
        title="11 Hydrology Before Life: Present-Day Surface Water",
        subtitle=(
            f"Equirectangular projection, "
            f"{present_surface.longitude_cells}x{present_surface.latitude_cells} "
            "shared surface cells with elevation, water depth, and runoff overlay."
        ),
    )
    frames_dir = clear_frame_directory(frame_output_dir(
        current_file,
        FRAME_DIRECTORY_NAME,
        present_surface.longitude_cells,
        present_surface.latitude_cells,
    ))
    for index in frame_sample_indices(len(hydrology_states)):
        frame_surface = hydrology_surface_for_index(
            index,
            proto_states,
            plate_states,
            topography_states,
            temperature_states,
            resurfacing_states,
            regolith_states,
            hydrology_states,
            atmosphere_states,
            resolution,
            cache,
        )
        write_hydrology_map_png(
            frame_surface,
            frames_dir / f"frame_{frame_surface.step_index:04d}.png",
            title="11 Hydrology Before Life",
            subtitle=(
                f"Timestep {frame_surface.step_index}, age "
                f"{frame_surface.age_years / 1_000_000.0:.1f} Myr."
            ),
        )
    return state_path


def build_hydrology_surface_extra(
    surface: PlanetSurface,
    *,
    current_file: str,
    state_path: Path,
    tectonic_resolution: tuple[int, int],
) -> dict[str, object]:
    water_mask = surface.water_depth > 0.0
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
                    basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.__file__,
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
            "water_covered_fraction": float(np.mean(water_mask)),
            "mean_water_depth_m": float(np.mean(surface.water_depth[water_mask])) if np.any(water_mask) else 0.0,
            "river_cell_fraction": float(np.mean((surface.runoff_flux >= 0.55) & ~water_mask)),
        },
    }


def simulate(
    criteria: planet.SimulationCriteria,
    surface_grid_resolution: tuple[int, int] | None = None,
) -> Iterable[HydrologyBeforeLifeState]:
    resolution = surface_grid_resolution or basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.parse_surface_grid_resolution(
        basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.DEFAULT_SURFACE_GRID_RESOLUTION
    )
    proto_states = tuple(basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.proto_tectonics.simulate(criteria, resolution))
    plate_states = tuple(basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.simulate(criteria, resolution))
    topography_states = tuple(large_scale_topography.simulate(criteria, resolution))
    temperature_states = tuple(surface_temperature.simulate(criteria))
    resurfacing_states = tuple(basic_regolith_weathering.volcanic_impact_resurfacing.simulate(criteria, resolution))
    regolith_states = tuple(basic_regolith_weathering.simulate(criteria, resolution))
    atmosphere_states = tuple(early_atmosphere.simulate(criteria))

    def build_states() -> Iterable[HydrologyBeforeLifeState]:
        for regolith_state, atmosphere_state, temperature_state, topography_state in zip(
            regolith_states,
            atmosphere_states,
            temperature_states,
            topography_states,
        ):
            yield hydrology_before_life_state_from_inputs(
                topography_state, atmosphere_state, temperature_state, regolith_state
            )

    surface_cache: dict[int, PlanetSurface] = {}

    def extra_builder(
        states: tuple[HydrologyBeforeLifeState, ...],
    ) -> dict[str, object] | None:
        if not states:
            return None
        present_surface = hydrology_surface_for_index(
            len(states) - 1,
            proto_states,
            plate_states,
            topography_states,
            temperature_states,
            resurfacing_states,
            regolith_states,
            states,
            atmosphere_states,
            resolution,
            surface_cache,
        )
        state_path = surface_state_output_path(
            __file__,
            present_surface.longitude_cells,
            present_surface.latitude_cells,
        )
        return build_hydrology_surface_extra(
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
        artifact_key=hydrology_surface_artifact_key(resolution),
        artifact_writer=lambda states: write_hydrology_artifacts(
            proto_states,
            plate_states,
            topography_states,
            temperature_states,
            resurfacing_states,
            regolith_states,
            states,
            atmosphere_states,
            resolution,
            __file__,
            surface_cache,
        ),
    )


def first_integrated_hydrology_state(
    states: Iterable[HydrologyBeforeLifeState],
) -> HydrologyBeforeLifeState | None:
    for state in states:
        if (
            state.stable_ocean_fraction >= Decimal("0.15")
            and state.runoff_pathway_count >= 2
        ):
            return state
    return None


def validate_model(
    surface_grid_resolution: tuple[int, int] | None = None,
) -> None:
    resolution = surface_grid_resolution or basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.parse_surface_grid_resolution(
        basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.DEFAULT_SURFACE_GRID_RESOLUTION
    )
    basic_regolith_weathering.validate_model(resolution)
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria, resolution))
    initial_state = states[0]
    present_state = states[-1]
    first_integrated_state = first_integrated_hydrology_state(states)
    present_feature_types = {feature.hydro_type for feature in present_state.features}
    terrain_resolution = subdivided_surface_grid_resolution(resolution)
    surface = load_planet_surface(
        surface_state_output_path(
            __file__, terrain_resolution[0], terrain_resolution[1]
        )
    )

    if initial_state.hydrology_state != "dry_magmatic_world":
        raise ValueError("Initial hydrology should begin as a dry magmatic world.")
    if present_state.stable_ocean_fraction <= Decimal("0.25"):
        raise ValueError("Present-day Aeron should sustain stable oceans.")
    if present_state.inland_sea_fraction <= Decimal("0.02"):
        raise ValueError("Present-day Aeron should sustain inland seas.")
    if present_state.glacier_fraction <= Decimal("0.01"):
        raise ValueError("Present-day Aeron should sustain glacier zones.")
    if present_state.glacier_zone_count < 1:
        raise ValueError("Present-day Aeron should contain at least one glacier zone.")
    if present_state.runoff_pathway_count < 2:
        raise ValueError("Present-day Aeron should sustain plural runoff pathways.")
    if present_state.basin_filling_fraction <= Decimal("0.35"):
        raise ValueError("Present-day Aeron should show meaningful basin filling.")
    if present_state.hydrology_state != "rain_sea_ice_world":
        raise ValueError("Present-day Aeron should read as a rain-sea-ice barren world.")
    if first_integrated_state is None:
        raise ValueError("Integrated prebiotic hydrology must emerge within the span.")
    if {"ocean", "inland_sea", "glacier_zone", "runoff_pathway", "basin_fill"} - present_feature_types:
        raise ValueError("Present-day hydrology must include all requested feature classes.")
    if surface.mesh_level != "terrain_mesh":
        raise ValueError("Hydrology must continue on the refined terrain mesh.")
    if float(np.mean(surface.water_depth > 0.0)) <= 0.20:
        raise ValueError("Present-day hydrology surface should sustain broad water coverage.")
    if float(np.mean(surface.runoff_flux >= 0.55)) <= 0.01:
        raise ValueError("Present-day hydrology surface should expose runoff pathways.")


def print_input_criteria(
    criteria: planet.SimulationCriteria, surface_grid_resolution: tuple[int, int]
) -> None:
    lon_cells, lat_cells = surface_grid_resolution
    fields = [
        ("layer_name", "hydrology_before_life"),
        ("regolith_source", "10_basic_regolith_weathering.py"),
        ("resurfacing_source", "09_volcanic_impact_resurfacing.py"),
        ("large_scale_topography_source", "08_large_scale_topography.py"),
        ("surface_temperature_source", "05_surface_temperature.py"),
        ("early_atmosphere_source", "04_early_atmosphere.py"),
        ("primary_crust_source", "03_primary_crust.py"),
        ("interior_source", "02_interior.py"),
        ("planet_source", "01_planet.py"),
        ("coupled_regolith_layer", "true"),
        ("coupled_resurfacing_layer", "true"),
        ("coupled_topography_layer", "true"),
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
        ("ocean_model", "basin_retention_plus_liquid_stability"),
        ("glacier_model", "polar_relief_cold_trap_scaling"),
        ("runoff_model", "moisture_plus_relief_pathway_scaling"),
        ("basin_fill_model", "sediment_plus_runoff_plus_basin_retention"),
        (
            "dynamic_fields",
            "stable_ocean_fraction, inland_sea_fraction, glacier_fraction, "
            "glacier_zone_count, runoff_pathway_count, basin_filling_fraction, "
            "hydrology_state",
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
        ("env", 12),
        ("regime", 18),
        ("ocean_f", 8),
        ("inland_f", 8),
        ("glacier_f", 9),
        ("glaciers", 9),
        ("runoff", 8),
        ("basin_f", 8),
        ("hydrology_state", 24),
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
            f"{state.surface_environment:>12} "
            f"{state.tectonic_regime:>18} "
            f"{planet.format_decimal(state.stable_ocean_fraction, 3):>8} "
            f"{planet.format_decimal(state.inland_sea_fraction, 3):>8} "
            f"{planet.format_decimal(state.glacier_fraction, 3):>9} "
            f"{state.glacier_zone_count:>9d} "
            f"{state.runoff_pathway_count:>8d} "
            f"{planet.format_decimal(state.basin_filling_fraction, 3):>8} "
            f"{state.hydrology_state:>24}"
        )


def print_present_day_summary(
    criteria: planet.SimulationCriteria, surface_grid_resolution: tuple[int, int]
) -> None:
    states = list(simulate(criteria, surface_grid_resolution))
    final_state = states[-1]
    first_integrated_state = first_integrated_hydrology_state(states)
    terrain_resolution = subdivided_surface_grid_resolution(surface_grid_resolution)
    surface = load_planet_surface(
        surface_state_output_path(
            __file__, terrain_resolution[0], terrain_resolution[1]
        )
    )

    assert first_integrated_state is not None

    fields = [
        ("world_class", final_state.world_class),
        ("surface_environment", final_state.surface_environment),
        ("surface_temperature_regime", final_state.surface_temperature_regime),
        ("tectonic_regime", final_state.tectonic_regime),
        (
            "stable_ocean_fraction",
            planet.format_decimal(final_state.stable_ocean_fraction, 6),
        ),
        (
            "inland_sea_fraction",
            planet.format_decimal(final_state.inland_sea_fraction, 6),
        ),
        (
            "glacier_fraction",
            planet.format_decimal(final_state.glacier_fraction, 6),
        ),
        ("glacier_zone_count", str(final_state.glacier_zone_count)),
        ("runoff_pathway_count", str(final_state.runoff_pathway_count)),
        (
            "basin_filling_fraction",
            planet.format_decimal(final_state.basin_filling_fraction, 6),
        ),
        ("hydrology_state", final_state.hydrology_state),
        ("surface_region_count", str(surface.region_ids.shape[0])),
        ("surface_mesh_level", surface.mesh_level),
        ("surface_state_path", str(surface_state_output_path(
            __file__, terrain_resolution[0], terrain_resolution[1]
        ))),
        ("first_integrated_hydrology_step", str(first_integrated_state.step_index)),
        (
            "first_integrated_hydrology_age_myr",
            planet.format_decimal(
                Decimal(first_integrated_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT HYDROLOGY SUMMARY")
    print("=========================")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")

    print()
    print("PRESENT HYDROLOGY FEATURES")
    print("==========================")
    headers = (
        ("feature", 30),
        ("type", 14),
        ("state", 12),
        ("activity", 9),
        ("area_f", 8),
        ("water_f", 8),
        ("ice_f", 8),
        ("fill_f", 8),
    )
    header_line = " ".join(f"{label:>{width}}" for label, width in headers)
    divider_line = " ".join("-" * width for _, width in headers)
    print(header_line)
    print(divider_line)
    for feature in final_state.features:
        print(
            f"{feature.feature_id:>30} "
            f"{feature.hydro_type:>14} "
            f"{feature.hydrology_state:>12} "
            f"{planet.format_decimal(feature.activity_index, 3):>9} "
            f"{planet.format_decimal(feature.area_fraction, 3):>8} "
            f"{planet.format_decimal(feature.water_fraction, 3):>8} "
            f"{planet.format_decimal(feature.ice_fraction, 3):>8} "
            f"{planet.format_decimal(feature.fill_fraction, 3):>8}"
        )


def main() -> int:
    args = parse_args()
    try:
        criteria = planet.build_criteria(args.step_years)
        surface_grid_resolution = basic_regolith_weathering.volcanic_impact_resurfacing.large_scale_topography.plate_system.parse_surface_grid_resolution(
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
