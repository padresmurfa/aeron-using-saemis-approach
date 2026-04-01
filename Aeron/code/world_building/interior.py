#!/usr/bin/env python3
"""Deterministic interior structure and thermal evolution simulation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable

try:
    from . import planet
except ImportError:
    import planet  # type: ignore

getcontext().prec = 50

COOLING_FLOOR = Decimal("0.18")
COOLING_DECAY_RATE = Decimal("3.0")
SOLIDIFICATION_START = Decimal("0.05")
SOLIDIFICATION_SPAN = Decimal("0.95")
SOLIDIFICATION_RATE = Decimal("4.0")
CORE_FORMATION_RATE = Decimal("7.0")
MANTLE_FORMATION_RATE = Decimal("5.0")
PRIMORDIAL_CRUST_FORMATION_RATE = Decimal("3.5")
RESIDUAL_HEAT_DECAY_RATE = Decimal("4.0")
RESIDUAL_HEAT_FLOOR = Decimal("0.7")
RADIOGENIC_HEAT_DECAY_RATE = Decimal("0.4")
RADIOGENIC_HEAT_SCALE = Decimal("1.2")
RADIOGENIC_HEAT_FLOOR = Decimal("0.9")
TIDAL_HEAT_BASE = Decimal("0.03")
TIDAL_HEAT_GROWTH = Decimal("0.04")
CONVECTION_BASE = Decimal("0.45")
CONVECTION_SPAN = Decimal("0.55")
TIDAL_HEATING_MODEL = "low_level_multimoon_regulator"
TIDAL_HEATING_STATUS = "coarse_first_pass"


@dataclass(frozen=True)
class InteriorState:
    step_index: int
    age_years: int
    mass_earth: Decimal
    radius_km: Decimal
    total_internal_heat_tw: Decimal
    residual_heat_tw: Decimal
    radiogenic_heat_tw: Decimal
    tidal_heat_tw: Decimal
    cooling_index: Decimal
    solid_fraction: Decimal
    solidification_state: str
    core_formation_fraction: Decimal
    mantle_formation_fraction: Decimal
    primordial_crust_fraction: Decimal
    convection_index: Decimal
    convection_state: str
    tectonic_readiness: str
    world_class: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's interior structure and thermal evolution by "
            "ticking the bulk-planet layer and deriving interior state from it."
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


def cooling_index_at(age_years: int) -> Decimal:
    age_fraction = planet.age_fraction_at(age_years)
    return COOLING_FLOOR + (Decimal("1") - COOLING_FLOOR) * (
        age_fraction * -COOLING_DECAY_RATE
    ).exp()


def solid_fraction_at(age_years: int) -> Decimal:
    age_fraction = planet.age_fraction_at(age_years)
    return SOLIDIFICATION_START + SOLIDIFICATION_SPAN * (
        Decimal("1") - (age_fraction * -SOLIDIFICATION_RATE).exp()
    )


def solidification_state_at(solid_fraction: Decimal) -> str:
    if solid_fraction < Decimal("0.20"):
        return "magma_ocean"
    if solid_fraction < Decimal("0.50"):
        return "heavily_molten"
    if solid_fraction < Decimal("0.80"):
        return "partially_solid"
    if solid_fraction < Decimal("0.95"):
        return "mostly_solid"
    return "differentiated_solid"


def core_formation_fraction_at(age_years: int) -> Decimal:
    age_fraction = planet.age_fraction_at(age_years)
    return Decimal("1") - (age_fraction * -CORE_FORMATION_RATE).exp()


def mantle_formation_fraction_at(age_years: int) -> Decimal:
    age_fraction = planet.age_fraction_at(age_years)
    return Decimal("1") - (age_fraction * -MANTLE_FORMATION_RATE).exp()


def primordial_crust_fraction_at(age_years: int) -> Decimal:
    age_fraction = planet.age_fraction_at(age_years)
    return Decimal("1") - (age_fraction * -PRIMORDIAL_CRUST_FORMATION_RATE).exp()


def heat_source_components(
    total_internal_heat_tw: Decimal, age_years: int
) -> tuple[Decimal, Decimal, Decimal]:
    age_fraction = planet.age_fraction_at(age_years)
    residual_raw = Decimal("4.0") * (age_fraction * -RESIDUAL_HEAT_DECAY_RATE).exp()
    residual_raw += RESIDUAL_HEAT_FLOOR
    radiogenic_raw = RADIOGENIC_HEAT_SCALE * (
        age_fraction * -RADIOGENIC_HEAT_DECAY_RATE
    ).exp()
    radiogenic_raw += RADIOGENIC_HEAT_FLOOR
    tidal_raw = TIDAL_HEAT_BASE + (TIDAL_HEAT_GROWTH * age_fraction)
    total_raw = residual_raw + radiogenic_raw + tidal_raw
    return (
        total_internal_heat_tw * residual_raw / total_raw,
        total_internal_heat_tw * radiogenic_raw / total_raw,
        total_internal_heat_tw * tidal_raw / total_raw,
    )


def convection_index_at(cooling_index: Decimal) -> Decimal:
    return CONVECTION_BASE + (CONVECTION_SPAN * cooling_index)


def convection_state_at(convection_index: Decimal) -> str:
    if convection_index >= Decimal("0.80"):
        return "vigorous"
    if convection_index >= Decimal("0.55"):
        return "active"
    if convection_index >= Decimal("0.35"):
        return "moderate"
    return "weak"


def tectonic_readiness_at(
    solid_fraction: Decimal,
    primordial_crust_fraction: Decimal,
    convection_index: Decimal,
) -> str:
    if (
        solid_fraction >= Decimal("0.85")
        and primordial_crust_fraction >= Decimal("0.80")
        and convection_index >= Decimal("0.55")
    ):
        return "primed"
    if (
        solid_fraction >= Decimal("0.60")
        and primordial_crust_fraction >= Decimal("0.45")
        and convection_index >= Decimal("0.40")
    ):
        return "emerging"
    return "not_ready"


def interior_state_from_planet_state(base_state: planet.PlanetState) -> InteriorState:
    residual_heat_tw, radiogenic_heat_tw, tidal_heat_tw = heat_source_components(
        base_state.internal_heat_tw, base_state.age_years
    )
    cooling_index = cooling_index_at(base_state.age_years)
    solid_fraction = solid_fraction_at(base_state.age_years)
    core_formation_fraction = core_formation_fraction_at(base_state.age_years)
    mantle_formation_fraction = mantle_formation_fraction_at(base_state.age_years)
    primordial_crust_fraction = primordial_crust_fraction_at(base_state.age_years)
    convection_index = convection_index_at(cooling_index)
    return InteriorState(
        step_index=base_state.step_index,
        age_years=base_state.age_years,
        mass_earth=base_state.mass_earth,
        radius_km=base_state.radius_km,
        total_internal_heat_tw=base_state.internal_heat_tw,
        residual_heat_tw=residual_heat_tw,
        radiogenic_heat_tw=radiogenic_heat_tw,
        tidal_heat_tw=tidal_heat_tw,
        cooling_index=cooling_index,
        solid_fraction=solid_fraction,
        solidification_state=solidification_state_at(solid_fraction),
        core_formation_fraction=core_formation_fraction,
        mantle_formation_fraction=mantle_formation_fraction,
        primordial_crust_fraction=primordial_crust_fraction,
        convection_index=convection_index,
        convection_state=convection_state_at(convection_index),
        tectonic_readiness=tectonic_readiness_at(
            solid_fraction, primordial_crust_fraction, convection_index
        ),
        world_class=base_state.world_class,
    )


def simulate(criteria: planet.SimulationCriteria) -> Iterable[InteriorState]:
    for base_state in planet.simulate(criteria):
        yield interior_state_from_planet_state(base_state)


def validate_model() -> None:
    planet.validate_model()
    reference_criteria = planet.build_criteria(planet.TOTAL_DURATION_YEARS)
    states = list(simulate(reference_criteria))
    initial_state = states[0]
    present_state = states[-1]

    for state in (initial_state, present_state):
        reconstructed_total = (
            state.residual_heat_tw + state.radiogenic_heat_tw + state.tidal_heat_tw
        )
        if planet.quantize(reconstructed_total, 9) != planet.quantize(
            state.total_internal_heat_tw, 9
        ):
            raise ValueError("Interior heat source components do not sum to total heat.")

    if not initial_state.solid_fraction < present_state.solid_fraction:
        raise ValueError("Solid fraction must increase across the simulation span.")
    if not initial_state.cooling_index > present_state.cooling_index:
        raise ValueError("Cooling index must decline across the simulation span.")
    if not initial_state.residual_heat_tw > initial_state.radiogenic_heat_tw:
        raise ValueError("Residual heat should dominate early thermal evolution.")
    if not present_state.radiogenic_heat_tw > present_state.residual_heat_tw:
        raise ValueError("Radiogenic heat should dominate the present-day heat mix.")
    if not present_state.tectonic_readiness == "primed":
        raise ValueError("Present-day Aeron should be tectonically primed at this layer.")


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "interior_structure_and_thermal_evolution"),
        ("planet_source", "planet.py"),
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
        ("cooling_model", "coarse_first_pass_decay"),
        ("solidification_model", "coarse_first_pass_progressive_solidification"),
        ("heat_source_model", "residual_plus_radiogenic_plus_low_tidal"),
        ("tidal_heating_model", TIDAL_HEATING_MODEL),
        ("tidal_heating_status", TIDAL_HEATING_STATUS),
        (
            "dynamic_fields",
            "mass_earth, radius_km, total_internal_heat_tw, residual_heat_tw, "
            "radiogenic_heat_tw, tidal_heat_tw, cooling_index, solid_fraction, "
            "solidification_state, core_formation_fraction, "
            "mantle_formation_fraction, primordial_crust_fraction, "
            "convection_index, convection_state, tectonic_readiness",
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
        ("mass_em", 10),
        ("radius_km", 12),
        ("heat_tw", 10),
        ("res_tw", 10),
        ("rad_tw", 10),
        ("tid_tw", 10),
        ("cool_ix", 8),
        ("solid", 8),
        ("solid_state", 20),
        ("core_f", 8),
        ("mant_f", 8),
        ("crust_f", 8),
        ("conv_ix", 8),
        ("conv", 10),
        ("tect", 10),
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
            f"{planet.format_decimal(state.mass_earth, 6):>10} "
            f"{planet.format_decimal(state.radius_km, 6):>12} "
            f"{planet.format_decimal(state.total_internal_heat_tw, 6):>10} "
            f"{planet.format_decimal(state.residual_heat_tw, 6):>10} "
            f"{planet.format_decimal(state.radiogenic_heat_tw, 6):>10} "
            f"{planet.format_decimal(state.tidal_heat_tw, 6):>10} "
            f"{planet.format_decimal(state.cooling_index, 3):>8} "
            f"{planet.format_decimal(state.solid_fraction, 3):>8} "
            f"{state.solidification_state:>20} "
            f"{planet.format_decimal(state.core_formation_fraction, 3):>8} "
            f"{planet.format_decimal(state.mantle_formation_fraction, 3):>8} "
            f"{planet.format_decimal(state.primordial_crust_fraction, 3):>8} "
            f"{planet.format_decimal(state.convection_index, 3):>8} "
            f"{state.convection_state:>10} "
            f"{state.tectonic_readiness:>10}"
        )


def print_present_day_summary(criteria: planet.SimulationCriteria) -> None:
    final_state = None
    for final_state in simulate(criteria):
        pass

    assert final_state is not None

    dominant_heat_source = "residual"
    if final_state.radiogenic_heat_tw >= final_state.residual_heat_tw:
        dominant_heat_source = "radiogenic"
    if final_state.tidal_heat_tw >= max(
        final_state.residual_heat_tw, final_state.radiogenic_heat_tw
    ):
        dominant_heat_source = "tidal"

    fields = [
        ("world_class", final_state.world_class),
        ("mass_earth", planet.format_decimal(final_state.mass_earth, 6)),
        ("radius_km", planet.format_decimal(final_state.radius_km, 6)),
        (
            "total_internal_heat_tw",
            planet.format_decimal(final_state.total_internal_heat_tw, 6),
        ),
        (
            "residual_heat_tw",
            planet.format_decimal(final_state.residual_heat_tw, 6),
        ),
        (
            "radiogenic_heat_tw",
            planet.format_decimal(final_state.radiogenic_heat_tw, 6),
        ),
        ("tidal_heat_tw", planet.format_decimal(final_state.tidal_heat_tw, 6)),
        ("dominant_heat_source", dominant_heat_source),
        ("cooling_index", planet.format_decimal(final_state.cooling_index, 6)),
        ("solid_fraction", planet.format_decimal(final_state.solid_fraction, 6)),
        ("solidification_state", final_state.solidification_state),
        (
            "core_formation_fraction",
            planet.format_decimal(final_state.core_formation_fraction, 6),
        ),
        (
            "mantle_formation_fraction",
            planet.format_decimal(final_state.mantle_formation_fraction, 6),
        ),
        (
            "primordial_crust_fraction",
            planet.format_decimal(final_state.primordial_crust_fraction, 6),
        ),
        ("convection_index", planet.format_decimal(final_state.convection_index, 6)),
        ("convection_state", final_state.convection_state),
        ("tectonic_readiness", final_state.tectonic_readiness),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT INTERIOR SUMMARY")
    print("========================")
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
