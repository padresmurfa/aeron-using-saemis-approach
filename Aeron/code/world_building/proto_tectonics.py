#!/usr/bin/env python3
"""Deterministic proto-tectonic regime simulation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable

try:
    from . import planet, surface_temperature
except ImportError:
    import planet  # type: ignore
    import surface_temperature  # type: ignore

getcontext().prec = 50

TEMP_RIGIDITY_THRESHOLD_C = Decimal("220")
THERMAL_STRESS_SATURATION_C = Decimal("30")
VALIDATION_STEP_YEARS = 100_000_000

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


@dataclass(frozen=True)
class ProtoTectonicsState:
    step_index: int
    age_years: int
    radius_km: Decimal
    mean_surface_temp_c: Decimal
    stable_crust_fraction: Decimal
    crust_stability_state: str
    surface_liquid_state: str
    thermal_cycling_amplitude_c: Decimal
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
    return parser.parse_args()


def clamp_unit_interval(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")
    if value > Decimal("1"):
        return Decimal("1")
    return value


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
        stable_crust_fraction=base_state.stable_crust_fraction,
        crust_stability_state=base_state.crust_stability_state,
        surface_liquid_state=base_state.surface_liquid_state,
        thermal_cycling_amplitude_c=base_state.thermal_cycling_amplitude_c,
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


def simulate(criteria: planet.SimulationCriteria) -> Iterable[ProtoTectonicsState]:
    for base_state in surface_temperature.simulate(criteria):
        yield proto_tectonics_state_from_surface_temperature_state(base_state)


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


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "proto_tectonic_regime"),
        ("surface_temperature_source", "surface_temperature.py"),
        ("early_atmosphere_source", "early_atmosphere.py"),
        ("primary_crust_source", "primary_crust.py"),
        ("interior_source", "interior.py"),
        ("planet_source", "planet.py"),
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
        (
            "dynamic_fields",
            "lithosphere_rigidity_index, fracture_potential_index, "
            "plate_mobility_index, rigid_enough_to_fracture, plates_exist, "
            "tectonic_regime, major_fracture_zones, spreading_zones, "
            "recycling_zones",
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

    for state in simulate(criteria):
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


def print_present_day_summary(criteria: planet.SimulationCriteria) -> None:
    states = list(simulate(criteria))
    final_state = states[-1]
    first_fracture_state = first_fracture_capable_state(states)
    first_plate_state = first_plate_like_state(states)

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
        validate_model()
    except ValueError as exc:
        raise SystemExit(str(exc))

    print_input_criteria(criteria)
    print_table(criteria)
    print_present_day_summary(criteria)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
