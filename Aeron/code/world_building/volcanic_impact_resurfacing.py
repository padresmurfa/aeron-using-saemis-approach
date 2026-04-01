#!/usr/bin/env python3
"""Deterministic volcanic and impact resurfacing simulation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable

try:
    from . import large_scale_topography, planet
except ImportError:
    import large_scale_topography  # type: ignore
    import planet  # type: ignore

getcontext().prec = 50

VALIDATION_STEP_YEARS = 100_000_000


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


def simulate(
    criteria: planet.SimulationCriteria,
) -> Iterable[VolcanicImpactResurfacingState]:
    for base_state in large_scale_topography.simulate(criteria):
        yield volcanic_impact_resurfacing_state_from_topography_state(base_state)


def first_ancient_scarred_state(
    states: Iterable[VolcanicImpactResurfacingState],
) -> VolcanicImpactResurfacingState | None:
    for state in states:
        if state.scar_state == "ancient_scarred_world":
            return state
    return None


def validate_model() -> None:
    large_scale_topography.validate_model()
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria))
    initial_state = states[0]
    present_state = states[-1]
    first_scarred_state = first_ancient_scarred_state(states)
    present_feature_types = {feature.feature_type for feature in present_state.features}

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


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "volcanic_and_impact_resurfacing"),
        ("large_scale_topography_source", "large_scale_topography.py"),
        ("plate_system_source", "plate_system.py"),
        ("proto_tectonics_source", "proto_tectonics.py"),
        ("surface_temperature_source", "surface_temperature.py"),
        ("early_atmosphere_source", "early_atmosphere.py"),
        ("primary_crust_source", "primary_crust.py"),
        ("interior_source", "interior.py"),
        ("planet_source", "planet.py"),
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


def print_table(criteria: planet.SimulationCriteria) -> None:
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

    for state in simulate(criteria):
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


def print_present_day_summary(criteria: planet.SimulationCriteria) -> None:
    states = list(simulate(criteria))
    final_state = states[-1]
    first_scarred_state = first_ancient_scarred_state(states)

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
        validate_model()
    except ValueError as exc:
        raise SystemExit(str(exc))

    print_input_criteria(criteria)
    print_table(criteria)
    print_present_day_summary(criteria)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
