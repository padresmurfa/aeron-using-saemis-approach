#!/usr/bin/env python3
"""Deterministic large-scale topography generation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable

try:
    from . import plate_system, planet
except ImportError:
    import plate_system  # type: ignore
    import planet  # type: ignore

getcontext().prec = 50

VALIDATION_STEP_YEARS = 100_000_000


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


def simulate(criteria: planet.SimulationCriteria) -> Iterable[LargeScaleTopographyState]:
    for base_state in plate_system.simulate(criteria):
        yield large_scale_topography_state_from_plate_system_state(base_state)


def first_structured_topography_state(
    states: Iterable[LargeScaleTopographyState],
) -> LargeScaleTopographyState | None:
    for state in states:
        if state.topography_state == "structured_barren_world":
            return state
    return None


def validate_model() -> None:
    plate_system.validate_model()
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria))
    initial_state = states[0]
    present_state = states[-1]
    first_structured_state = first_structured_topography_state(states)
    present_feature_types = {feature.feature_type for feature in present_state.features}
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


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "large_scale_topography_generation"),
        ("plate_system_source", "plate_system.py"),
        ("proto_tectonics_source", "proto_tectonics.py"),
        ("surface_temperature_source", "surface_temperature.py"),
        ("early_atmosphere_source", "early_atmosphere.py"),
        ("primary_crust_source", "primary_crust.py"),
        ("interior_source", "interior.py"),
        ("planet_source", "planet.py"),
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
        ("province_model", "fixed_template_relief_features"),
        ("relief_model", "tectonic_rate_scaled_first_order_relief"),
        ("erosion_model", "not_yet_applied"),
        (
            "dynamic_fields",
            "proto_continent_fraction, ocean_basin_fraction, "
            "highest_relief_m, deepest_basin_m, relief_contrast_m, "
            "topography_state, feature_count",
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

    for state in simulate(criteria):
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


def print_present_day_summary(criteria: planet.SimulationCriteria) -> None:
    states = list(simulate(criteria))
    final_state = states[-1]
    first_structured_state = first_structured_topography_state(states)

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
        validate_model()
    except ValueError as exc:
        raise SystemExit(str(exc))

    print_input_criteria(criteria)
    print_table(criteria)
    print_present_day_summary(criteria)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
