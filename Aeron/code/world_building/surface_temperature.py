#!/usr/bin/env python3
"""Deterministic surface temperature regime simulation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable

try:
    from . import early_atmosphere, planet
except ImportError:
    import early_atmosphere  # type: ignore
    import planet  # type: ignore

getcontext().prec = 50

PRESSURE_GRADIENT_SATURATION_BAR = Decimal("1.5")
SEASONAL_CYCLING_BONUS_C = Decimal("4")
VALIDATION_STEP_YEARS = 100_000_000


@dataclass(frozen=True)
class SurfaceTemperatureState:
    step_index: int
    age_years: int
    radius_km: Decimal
    atmospheric_pressure_bar: Decimal
    greenhouse_index: Decimal
    stable_crust_fraction: Decimal
    surface_environment: str
    mean_surface_temp_c: Decimal
    average_temperature_band: str
    equator_to_pole_delta_c: Decimal
    latitudinal_contrast: str
    surface_liquid_state: str
    crust_stability_state: str
    thermal_cycling_amplitude_c: Decimal
    thermal_cycling_state: str
    surface_temperature_regime: str
    world_class: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's coarse surface temperature regime by ticking the "
            "early-atmosphere layer and deriving broad thermal behavior from it."
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


def pressure_factor_at(atmospheric_pressure_bar: Decimal) -> Decimal:
    return clamp_unit_interval(
        atmospheric_pressure_bar / PRESSURE_GRADIENT_SATURATION_BAR
    )


def mean_surface_temp_c_at(
    state: early_atmosphere.EarlyAtmosphereState,
) -> Decimal:
    pressure_factor = pressure_factor_at(state.atmospheric_pressure_bar)

    if state.surface_environment == "lava":
        return Decimal("900") - (Decimal("220") * state.stable_crust_fraction)
    if state.surface_environment == "steam":
        return (
            Decimal("105")
            + (Decimal("85") * state.greenhouse_index)
            + (Decimal("18") * pressure_factor)
        )
    if state.surface_environment == "wet_rock":
        return (
            Decimal("-6")
            + (Decimal("46") * state.greenhouse_index)
            + (Decimal("14") * pressure_factor)
            + (
                Decimal("6")
                if state.precipitation_state == "established"
                else Decimal("0")
            )
        )
    if state.surface_environment == "ice":
        return (
            Decimal("-58")
            + (Decimal("20") * state.greenhouse_index)
            + (Decimal("9") * pressure_factor)
        )
    if state.surface_environment == "dry_rock":
        return (
            Decimal("-32")
            + (Decimal("38") * state.greenhouse_index)
            + (Decimal("10") * pressure_factor)
        )
    return (
        Decimal("-95")
        + (Decimal("24") * state.greenhouse_index)
        + (Decimal("8") * pressure_factor)
    )


def average_temperature_band_at(mean_surface_temp_c: Decimal) -> str:
    if mean_surface_temp_c >= Decimal("500"):
        return "molten_extreme"
    if mean_surface_temp_c >= Decimal("100"):
        return "steamhouse_hot"
    if mean_surface_temp_c >= Decimal("35"):
        return "hot"
    if mean_surface_temp_c >= Decimal("5"):
        return "temperate"
    if mean_surface_temp_c >= Decimal("-20"):
        return "cold"
    return "frozen"


def equator_to_pole_delta_c_at(
    state: early_atmosphere.EarlyAtmosphereState,
) -> Decimal:
    pressure_factor = pressure_factor_at(state.atmospheric_pressure_bar)
    liquid_damping = Decimal("0")
    if state.precipitation_state == "possible":
        liquid_damping = Decimal("4")
    elif state.precipitation_state == "established":
        liquid_damping = Decimal("7")

    if state.surface_environment == "lava":
        return Decimal("8")
    if state.surface_environment == "steam":
        return Decimal("22") - (Decimal("8") * pressure_factor) - (
            Decimal("6") * state.greenhouse_index
        )
    if state.surface_environment == "wet_rock":
        return (
            Decimal("32")
            - (Decimal("8") * pressure_factor)
            - (Decimal("6") * state.greenhouse_index)
            - liquid_damping
        )
    if state.surface_environment == "ice":
        return (
            Decimal("38")
            - (Decimal("6") * pressure_factor)
            - (Decimal("5") * state.greenhouse_index)
        )
    if state.surface_environment == "dry_rock":
        return (
            Decimal("48")
            - (Decimal("7") * pressure_factor)
            - (Decimal("4") * state.greenhouse_index)
        )
    return (
        Decimal("56")
        - (Decimal("5") * pressure_factor)
        - (Decimal("4") * state.greenhouse_index)
    )


def latitudinal_contrast_at(equator_to_pole_delta_c: Decimal) -> str:
    if equator_to_pole_delta_c < Decimal("15"):
        return "low"
    if equator_to_pole_delta_c < Decimal("30"):
        return "moderate"
    return "high"


def surface_liquid_state_at(
    state: early_atmosphere.EarlyAtmosphereState,
    mean_surface_temp_c: Decimal,
) -> str:
    if state.liquid_precipitation_possible == "no":
        return "absent"
    if mean_surface_temp_c <= Decimal("0"):
        return "frozen"
    if mean_surface_temp_c >= Decimal("100"):
        return "absent"
    if state.precipitation_state == "established":
        return "stable"
    return "transient"


def thermal_cycling_amplitude_c_at(
    state: early_atmosphere.EarlyAtmosphereState,
    equator_to_pole_delta_c: Decimal,
) -> Decimal:
    pressure_factor = pressure_factor_at(state.atmospheric_pressure_bar)

    if state.surface_environment == "lava":
        amplitude = Decimal("12")
    else:
        amplitude = (equator_to_pole_delta_c * Decimal("0.55")) + (
            (Decimal("1") - pressure_factor) * Decimal("18")
        )
        if state.precipitation_state == "established":
            amplitude -= Decimal("5")
        elif state.precipitation_state == "possible":
            amplitude -= Decimal("2")
        if state.surface_environment == "steam":
            amplitude -= Decimal("3")
        if planet.AXIAL_TILT_STATE == "seasonal":
            amplitude += SEASONAL_CYCLING_BONUS_C

    if amplitude < Decimal("5"):
        return Decimal("5")
    return amplitude


def thermal_cycling_state_at(thermal_cycling_amplitude_c: Decimal) -> str:
    if thermal_cycling_amplitude_c < Decimal("15"):
        return "low"
    if thermal_cycling_amplitude_c < Decimal("30"):
        return "moderate"
    if thermal_cycling_amplitude_c < Decimal("45"):
        return "high"
    return "extreme"


def crust_stability_state_at(
    state: early_atmosphere.EarlyAtmosphereState,
    mean_surface_temp_c: Decimal,
    thermal_cycling_amplitude_c: Decimal,
) -> str:
    if state.surface_environment == "lava":
        return "disrupted"
    if state.stable_crust_fraction < Decimal("0.35"):
        return "fragile"
    if mean_surface_temp_c > Decimal("180") or thermal_cycling_amplitude_c > Decimal("35"):
        return "stressed"
    if (
        state.stable_crust_fraction >= Decimal("0.65")
        and thermal_cycling_amplitude_c <= Decimal("25")
    ):
        return "stable"
    return "stressed"


def surface_temperature_regime_at(
    state: early_atmosphere.EarlyAtmosphereState,
    surface_liquid_state: str,
) -> str:
    if state.surface_environment == "lava":
        return "hot_volcanic_rock"
    if state.surface_environment == "steam":
        return "steam_shrouded_rock"
    if state.surface_environment == "naked_rock":
        return "cold_dead_rock"
    if state.surface_environment == "dry_rock":
        return "dry_wind_scoured_rock"
    if state.surface_environment == "ice" or surface_liquid_state == "frozen":
        return "ice_rock"
    if state.surface_environment == "wet_rock":
        return "temperate_wet_rock"
    return "dry_wind_scoured_rock"


def surface_temperature_state_from_atmosphere_state(
    base_state: early_atmosphere.EarlyAtmosphereState,
) -> SurfaceTemperatureState:
    mean_surface_temp_c = mean_surface_temp_c_at(base_state)
    equator_to_pole_delta_c = equator_to_pole_delta_c_at(base_state)
    surface_liquid_state = surface_liquid_state_at(base_state, mean_surface_temp_c)
    thermal_cycling_amplitude_c = thermal_cycling_amplitude_c_at(
        base_state, equator_to_pole_delta_c
    )
    return SurfaceTemperatureState(
        step_index=base_state.step_index,
        age_years=base_state.age_years,
        radius_km=base_state.radius_km,
        atmospheric_pressure_bar=base_state.atmospheric_pressure_bar,
        greenhouse_index=base_state.greenhouse_index,
        stable_crust_fraction=base_state.stable_crust_fraction,
        surface_environment=base_state.surface_environment,
        mean_surface_temp_c=mean_surface_temp_c,
        average_temperature_band=average_temperature_band_at(mean_surface_temp_c),
        equator_to_pole_delta_c=equator_to_pole_delta_c,
        latitudinal_contrast=latitudinal_contrast_at(equator_to_pole_delta_c),
        surface_liquid_state=surface_liquid_state,
        crust_stability_state=crust_stability_state_at(
            base_state, mean_surface_temp_c, thermal_cycling_amplitude_c
        ),
        thermal_cycling_amplitude_c=thermal_cycling_amplitude_c,
        thermal_cycling_state=thermal_cycling_state_at(thermal_cycling_amplitude_c),
        surface_temperature_regime=surface_temperature_regime_at(
            base_state, surface_liquid_state
        ),
        world_class=base_state.world_class,
    )


def simulate(criteria: planet.SimulationCriteria) -> Iterable[SurfaceTemperatureState]:
    for base_state in early_atmosphere.simulate(criteria):
        yield surface_temperature_state_from_atmosphere_state(base_state)


def first_surface_liquids_state(
    states: Iterable[SurfaceTemperatureState],
) -> SurfaceTemperatureState | None:
    for state in states:
        if state.surface_liquid_state in {"transient", "stable"}:
            return state
    return None


def validate_model() -> None:
    early_atmosphere.validate_model()
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria))
    initial_state = states[0]
    present_state = states[-1]
    first_liquid_state = first_surface_liquids_state(states)

    if initial_state.surface_temperature_regime != "hot_volcanic_rock":
        raise ValueError("Temperature layer should begin from hot volcanic rock.")
    if present_state.surface_liquid_state not in {"transient", "stable"}:
        raise ValueError("Present-day Aeron should permit surface liquids.")
    if present_state.crust_stability_state not in {"stressed", "stable"}:
        raise ValueError("Present-day crust should not be disrupted at this layer.")
    if first_liquid_state is None:
        raise ValueError("Surface liquids must become possible within the span.")


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "surface_temperature_regime"),
        ("early_atmosphere_source", "early_atmosphere.py"),
        ("primary_crust_source", "primary_crust.py"),
        ("interior_source", "interior.py"),
        ("planet_source", "planet.py"),
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
        ("temperature_model", "surface_envelope_plus_greenhouse_first_pass"),
        ("latitudinal_model", "pressure_and_greenhouse_damped_gradient"),
        ("thermal_cycling_model", "latitudinal_gradient_plus_atmospheric_buffer"),
        (
            "dynamic_fields",
            "mean_surface_temp_c, average_temperature_band, "
            "equator_to_pole_delta_c, latitudinal_contrast, "
            "surface_liquid_state, crust_stability_state, "
            "thermal_cycling_amplitude_c, thermal_cycling_state, "
            "surface_temperature_regime",
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
        ("surface", 12),
        ("press", 8),
        ("green", 8),
        ("temp_c", 10),
        ("band", 16),
        ("lat_d_c", 10),
        ("liquids", 10),
        ("crust", 10),
        ("cycle_c", 10),
        ("cycle", 10),
        ("regime", 24),
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
            f"{state.surface_environment:>12} "
            f"{planet.format_decimal(state.atmospheric_pressure_bar, 3):>8} "
            f"{planet.format_decimal(state.greenhouse_index, 3):>8} "
            f"{planet.format_decimal(state.mean_surface_temp_c, 3):>10} "
            f"{state.average_temperature_band:>16} "
            f"{planet.format_decimal(state.equator_to_pole_delta_c, 3):>10} "
            f"{state.surface_liquid_state:>10} "
            f"{state.crust_stability_state:>10} "
            f"{planet.format_decimal(state.thermal_cycling_amplitude_c, 3):>10} "
            f"{state.thermal_cycling_state:>10} "
            f"{state.surface_temperature_regime:>24}"
        )


def print_present_day_summary(criteria: planet.SimulationCriteria) -> None:
    states = list(simulate(criteria))
    final_state = states[-1]
    first_liquid_state = first_surface_liquids_state(states)

    assert first_liquid_state is not None

    fields = [
        ("world_class", final_state.world_class),
        ("mean_surface_temp_c", planet.format_decimal(final_state.mean_surface_temp_c, 6)),
        ("average_temperature_band", final_state.average_temperature_band),
        (
            "equator_to_pole_delta_c",
            planet.format_decimal(final_state.equator_to_pole_delta_c, 6),
        ),
        ("latitudinal_contrast", final_state.latitudinal_contrast),
        ("surface_liquid_state", final_state.surface_liquid_state),
        ("crust_stability_state", final_state.crust_stability_state),
        (
            "thermal_cycling_amplitude_c",
            planet.format_decimal(final_state.thermal_cycling_amplitude_c, 6),
        ),
        ("thermal_cycling_state", final_state.thermal_cycling_state),
        ("surface_temperature_regime", final_state.surface_temperature_regime),
        ("first_surface_liquids_step", str(first_liquid_state.step_index)),
        (
            "first_surface_liquids_age_myr",
            planet.format_decimal(
                Decimal(first_liquid_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT SURFACE TEMPERATURE SUMMARY")
    print("===================================")
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
