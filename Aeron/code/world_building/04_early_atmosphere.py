#!/usr/bin/env python3
"""Deterministic early atmosphere and volatile accumulation simulation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable

try:
    from .world_building_support import load_pipeline_module, materialize_layer_states
except ImportError:
    from world_building_support import load_pipeline_module, materialize_layer_states  # type: ignore

planet = load_pipeline_module(__package__, __file__, "01_planet")
primary_crust = load_pipeline_module(__package__, __file__, "03_primary_crust")

getcontext().prec = 50

OUTGASSING_CONVECTION_WEIGHT = Decimal("0.35")
OUTGASSING_WEAK_ZONE_WEIGHT = Decimal("0.30")
OUTGASSING_OPEN_SURFACE_WEIGHT = Decimal("0.20")
OUTGASSING_UNSEALED_CRUST_WEIGHT = Decimal("0.15")
OUTGASSING_BAR_PER_GYR_MAX = Decimal("0.48")

LOSS_RETENTION_WEIGHT = Decimal("0.55")
LOSS_MAGNETIC_WEIGHT = Decimal("0.25")
LOSS_OPEN_SURFACE_WEIGHT = Decimal("0.20")
LOSS_BAR_PER_GYR_MAX = Decimal("0.30")
LOSS_PRESSURE_SATURATION_BAR = Decimal("1.5")

GREENHOUSE_PRESSURE_WEIGHT = Decimal("0.30")
GREENHOUSE_OUTGASSING_WEIGHT = Decimal("0.30")
GREENHOUSE_STEAM_WEIGHT = Decimal("0.25")
GREENHOUSE_SURFACE_INSTABILITY_WEIGHT = Decimal("0.15")
GREENHOUSE_PRESSURE_SATURATION_BAR = Decimal("2.5")

VALIDATION_STEP_YEARS = 100_000_000


@dataclass(frozen=True)
class EarlyAtmosphereState:
    step_index: int
    age_years: int
    mass_earth: Decimal
    radius_km: Decimal
    total_internal_heat_tw: Decimal
    stable_crust_fraction: Decimal
    surface_state: str
    magnetic_field: str
    retention_potential: str
    outgassing_index: Decimal
    outgassing_flux_bar_per_gyr: Decimal
    gas_loss_index: Decimal
    gas_loss_flux_bar_per_gyr: Decimal
    atmospheric_pressure_bar: Decimal
    atmospheric_composition: str
    greenhouse_index: Decimal
    greenhouse_state: str
    liquid_precipitation_possible: str
    precipitation_state: str
    surface_environment: str
    world_class: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's early atmosphere and volatile accumulation by "
            "ticking the primary-crust layer and deriving a coarse surface "
            "envelope from it."
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


def surface_open_factor_at(surface_state: str) -> Decimal:
    if surface_state == "mostly_molten":
        return Decimal("1.0")
    if surface_state == "mixed":
        return Decimal("0.65")
    return Decimal("0.25")


def steam_factor_at(surface_state: str) -> Decimal:
    if surface_state == "mostly_molten":
        return Decimal("1.0")
    if surface_state == "mixed":
        return Decimal("0.65")
    return Decimal("0.30")


def retention_score_at(retention_potential: str) -> Decimal:
    if retention_potential == "weak":
        return Decimal("0.25")
    if retention_potential == "moderate":
        return Decimal("0.60")
    return Decimal("0.90")


def magnetic_score_at(magnetic_field: str) -> Decimal:
    return Decimal("1.0") if magnetic_field == "present" else Decimal("0.0")


def outgassing_index_at(state: primary_crust.PrimaryCrustState) -> Decimal:
    return clamp_unit_interval(
        (OUTGASSING_CONVECTION_WEIGHT * state.convection_index)
        + (OUTGASSING_WEAK_ZONE_WEIGHT * state.weak_zone_fraction)
        + (OUTGASSING_OPEN_SURFACE_WEIGHT * surface_open_factor_at(state.surface_state))
        + (OUTGASSING_UNSEALED_CRUST_WEIGHT * (Decimal("1") - state.stable_crust_fraction))
    )


def outgassing_flux_bar_per_gyr_at(outgassing_index: Decimal) -> Decimal:
    return OUTGASSING_BAR_PER_GYR_MAX * outgassing_index


def gas_loss_index_at(
    state: primary_crust.PrimaryCrustState,
    retention_potential: str,
    magnetic_field: str,
) -> Decimal:
    retention_score = retention_score_at(retention_potential)
    magnetic_score = magnetic_score_at(magnetic_field)
    return clamp_unit_interval(
        (LOSS_RETENTION_WEIGHT * (Decimal("1") - retention_score))
        + (LOSS_MAGNETIC_WEIGHT * (Decimal("1") - magnetic_score))
        + (LOSS_OPEN_SURFACE_WEIGHT * surface_open_factor_at(state.surface_state))
    )


def gas_loss_flux_bar_per_gyr_at(
    gas_loss_index: Decimal, atmospheric_pressure_bar: Decimal
) -> Decimal:
    exposure = clamp_unit_interval(
        atmospheric_pressure_bar / LOSS_PRESSURE_SATURATION_BAR
    )
    return LOSS_BAR_PER_GYR_MAX * gas_loss_index * exposure


def greenhouse_index_at(
    state: primary_crust.PrimaryCrustState,
    atmospheric_pressure_bar: Decimal,
    outgassing_index: Decimal,
) -> Decimal:
    pressure_factor = clamp_unit_interval(
        atmospheric_pressure_bar / GREENHOUSE_PRESSURE_SATURATION_BAR
    )
    return clamp_unit_interval(
        (GREENHOUSE_PRESSURE_WEIGHT * pressure_factor)
        + (GREENHOUSE_OUTGASSING_WEIGHT * outgassing_index)
        + (GREENHOUSE_STEAM_WEIGHT * steam_factor_at(state.surface_state))
        + (
            GREENHOUSE_SURFACE_INSTABILITY_WEIGHT
            * (Decimal("1") - state.stable_crust_fraction)
        )
    )


def greenhouse_state_at(greenhouse_index: Decimal) -> str:
    if greenhouse_index >= Decimal("0.75"):
        return "extreme"
    if greenhouse_index >= Decimal("0.50"):
        return "strong"
    if greenhouse_index >= Decimal("0.25"):
        return "moderate"
    return "weak"


def precipitation_state_at(
    state: primary_crust.PrimaryCrustState,
    atmospheric_pressure_bar: Decimal,
    greenhouse_index: Decimal,
    retention_potential: str,
) -> str:
    if state.surface_state == "mostly_molten":
        return "impossible"
    if atmospheric_pressure_bar < Decimal("0.15"):
        return "impossible"
    if greenhouse_index >= Decimal("0.78"):
        return "impossible"
    if retention_potential == "weak":
        return "transient"
    if (
        atmospheric_pressure_bar >= Decimal("0.60")
        and greenhouse_index <= Decimal("0.65")
        and state.stable_crust_fraction >= Decimal("0.60")
    ):
        return "established"
    if atmospheric_pressure_bar >= Decimal("0.35"):
        return "possible"
    return "transient"


def atmospheric_composition_at(
    state: primary_crust.PrimaryCrustState,
    atmospheric_pressure_bar: Decimal,
    greenhouse_index: Decimal,
    precipitation_state: str,
) -> str:
    if atmospheric_pressure_bar < Decimal("0.08"):
        return "trace_volatiles"
    if state.surface_state == "mostly_molten":
        return "steam_co2_sulfurous"
    if greenhouse_index >= Decimal("0.72"):
        return "steam_co2_dominant"
    if precipitation_state in {"possible", "established"}:
        if atmospheric_pressure_bar >= Decimal("0.80"):
            return "n2_co2_h2o"
        return "co2_h2o_with_trace_n2"
    if atmospheric_pressure_bar >= Decimal("0.50"):
        return "co2_n2_with_steam"
    return "co2_steam_trace_n2"


def surface_environment_at(
    state: primary_crust.PrimaryCrustState,
    atmospheric_pressure_bar: Decimal,
    greenhouse_index: Decimal,
    precipitation_state: str,
) -> str:
    if state.surface_state == "mostly_molten":
        return "lava"
    if greenhouse_index >= Decimal("0.55") and atmospheric_pressure_bar >= Decimal("0.20"):
        return "steam"
    if atmospheric_pressure_bar < Decimal("0.10"):
        return "naked_rock"
    if precipitation_state in {"possible", "established"}:
        if greenhouse_index < Decimal("0.25"):
            return "ice"
        return "wet_rock"
    if greenhouse_index < Decimal("0.20") and atmospheric_pressure_bar >= Decimal("0.30"):
        return "ice"
    return "dry_rock"


def build_pressure_history(
    criteria: planet.SimulationCriteria,
    crust_states: list[primary_crust.PrimaryCrustState],
) -> list[Decimal]:
    dt_gyr = Decimal(criteria.step_years) / planet.YEARS_PER_GYR
    pressure_history = [Decimal("0")]

    for previous_state in crust_states[:-1]:
        previous_pressure = pressure_history[-1]
        magnetic_field = planet.magnetic_field_at(previous_state.age_years)
        retention_potential = planet.atmosphere_retention_at(
            previous_state.radius_km, magnetic_field
        )
        outgassing_index = outgassing_index_at(previous_state)
        gas_loss_index = gas_loss_index_at(
            previous_state, retention_potential, magnetic_field
        )
        pressure_delta = (
            outgassing_flux_bar_per_gyr_at(outgassing_index)
            - gas_loss_flux_bar_per_gyr_at(gas_loss_index, previous_pressure)
        ) * dt_gyr
        next_pressure = previous_pressure + pressure_delta
        if next_pressure < Decimal("0"):
            next_pressure = Decimal("0")
        pressure_history.append(next_pressure)

    return pressure_history


def atmosphere_state_from_primary_crust_state(
    base_state: primary_crust.PrimaryCrustState,
    atmospheric_pressure_bar: Decimal,
) -> EarlyAtmosphereState:
    magnetic_field = planet.magnetic_field_at(base_state.age_years)
    retention_potential = planet.atmosphere_retention_at(
        base_state.radius_km, magnetic_field
    )
    outgassing_index = outgassing_index_at(base_state)
    gas_loss_index = gas_loss_index_at(base_state, retention_potential, magnetic_field)
    greenhouse_index = greenhouse_index_at(
        base_state, atmospheric_pressure_bar, outgassing_index
    )
    precipitation_state = precipitation_state_at(
        base_state, atmospheric_pressure_bar, greenhouse_index, retention_potential
    )
    return EarlyAtmosphereState(
        step_index=base_state.step_index,
        age_years=base_state.age_years,
        mass_earth=base_state.mass_earth,
        radius_km=base_state.radius_km,
        total_internal_heat_tw=base_state.total_internal_heat_tw,
        stable_crust_fraction=base_state.stable_crust_fraction,
        surface_state=base_state.surface_state,
        magnetic_field=magnetic_field,
        retention_potential=retention_potential,
        outgassing_index=outgassing_index,
        outgassing_flux_bar_per_gyr=outgassing_flux_bar_per_gyr_at(outgassing_index),
        gas_loss_index=gas_loss_index,
        gas_loss_flux_bar_per_gyr=gas_loss_flux_bar_per_gyr_at(
            gas_loss_index, atmospheric_pressure_bar
        ),
        atmospheric_pressure_bar=atmospheric_pressure_bar,
        atmospheric_composition=atmospheric_composition_at(
            base_state, atmospheric_pressure_bar, greenhouse_index, precipitation_state
        ),
        greenhouse_index=greenhouse_index,
        greenhouse_state=greenhouse_state_at(greenhouse_index),
        liquid_precipitation_possible=(
            "yes" if precipitation_state in {"possible", "established"} else "no"
        ),
        precipitation_state=precipitation_state,
        surface_environment=surface_environment_at(
            base_state, atmospheric_pressure_bar, greenhouse_index, precipitation_state
        ),
        world_class=base_state.world_class,
    )


def simulate(criteria: planet.SimulationCriteria) -> Iterable[EarlyAtmosphereState]:
    def build_states() -> Iterable[EarlyAtmosphereState]:
        crust_states = tuple(primary_crust.simulate(criteria))
        pressure_history = build_pressure_history(criteria, crust_states)
        for base_state, atmospheric_pressure_bar in zip(crust_states, pressure_history):
            yield atmosphere_state_from_primary_crust_state(
                base_state, atmospheric_pressure_bar
            )

    return materialize_layer_states(__file__, criteria, build_states)


def first_precipitation_state(
    states: Iterable[EarlyAtmosphereState],
) -> EarlyAtmosphereState | None:
    for state in states:
        if state.liquid_precipitation_possible == "yes":
            return state
    return None


def validate_model() -> None:
    primary_crust.validate_model()
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria))
    initial_state = states[0]
    present_state = states[-1]
    first_precip_state = first_precipitation_state(states)

    if initial_state.surface_environment != "lava":
        raise ValueError("Atmosphere layer should begin from a lava surface state.")
    if present_state.atmospheric_pressure_bar <= initial_state.atmospheric_pressure_bar:
        raise ValueError("Atmospheric pressure should accumulate over time.")
    if first_precip_state is None:
        raise ValueError("Liquid precipitation must become possible somewhere in the span.")
    if present_state.liquid_precipitation_possible != "yes":
        raise ValueError("Present-day Aeron should permit liquid precipitation.")
    if present_state.atmospheric_composition == "trace_volatiles":
        raise ValueError("Present-day Aeron should have a non-trace atmosphere.")


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "early_atmosphere_and_volatile_accumulation"),
        ("primary_crust_source", "03_primary_crust.py"),
        ("interior_source", "02_interior.py"),
        ("planet_source", "01_planet.py"),
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
        ("outgassing_model", "convection_plus_weak_zone_plus_open_surface"),
        ("retention_model", "gravity_plus_magnetic_plus_surface_escape"),
        ("pressure_model", "retained_volatile_inventory"),
        ("greenhouse_model", "pressure_plus_outgassing_plus_steam"),
        ("precipitation_model", "coarse_phase_window"),
        (
            "dynamic_fields",
            "atmospheric_pressure_bar, atmospheric_composition, "
            "outgassing_index, outgassing_flux_bar_per_gyr, gas_loss_index, "
            "gas_loss_flux_bar_per_gyr, greenhouse_index, greenhouse_state, "
            "liquid_precipitation_possible, precipitation_state, "
            "surface_environment",
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
        ("radius_km", 12),
        ("retain", 10),
        ("mag", 8),
        ("outgas", 8),
        ("loss", 8),
        ("press", 8),
        ("comp", 24),
        ("green", 8),
        ("precip", 11),
        ("surface", 12),
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
            f"{planet.format_decimal(state.radius_km, 6):>12} "
            f"{state.retention_potential:>10} "
            f"{state.magnetic_field:>8} "
            f"{planet.format_decimal(state.outgassing_index, 3):>8} "
            f"{planet.format_decimal(state.gas_loss_index, 3):>8} "
            f"{planet.format_decimal(state.atmospheric_pressure_bar, 3):>8} "
            f"{state.atmospheric_composition:>24} "
            f"{planet.format_decimal(state.greenhouse_index, 3):>8} "
            f"{state.precipitation_state:>11} "
            f"{state.surface_environment:>12}"
        )


def print_present_day_summary(criteria: planet.SimulationCriteria) -> None:
    states = list(simulate(criteria))
    final_state = states[-1]
    first_precip_state = first_precipitation_state(states)

    assert first_precip_state is not None

    fields = [
        ("world_class", final_state.world_class),
        ("atmospheric_pressure_bar", planet.format_decimal(final_state.atmospheric_pressure_bar, 6)),
        ("retention_potential", final_state.retention_potential),
        ("magnetic_field", final_state.magnetic_field),
        ("atmospheric_composition", final_state.atmospheric_composition),
        ("greenhouse_index", planet.format_decimal(final_state.greenhouse_index, 6)),
        ("greenhouse_state", final_state.greenhouse_state),
        ("liquid_precipitation_possible", final_state.liquid_precipitation_possible),
        ("precipitation_state", final_state.precipitation_state),
        ("surface_environment", final_state.surface_environment),
        ("first_precipitation_step", str(first_precip_state.step_index)),
        (
            "first_precipitation_age_myr",
            planet.format_decimal(
                Decimal(first_precip_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT EARLY ATMOSPHERE SUMMARY")
    print("===============================")
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
