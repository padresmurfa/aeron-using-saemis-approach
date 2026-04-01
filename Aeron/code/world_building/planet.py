#!/usr/bin/env python3
"""Deterministic bulk-evolution simulation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Iterable

getcontext().prec = 50

YEARS_PER_MYR = Decimal("1000000")
YEARS_PER_GYR = Decimal("1000000000")
CM_PER_KM = Decimal("100000")
G_PER_KG = Decimal("1000")
PI = Decimal("3.14159265358979323846264338327950288419716939937510")
FOUR_THIRDS_PI = (Decimal("4") / Decimal("3")) * PI

START_AGE_YEARS = 0
TOTAL_DURATION_YEARS = 5_400_000_000

EARTH_RADIUS_KM = Decimal("6371")
EARTH_MASS_KG = Decimal("5.9722E24")
EARTH_BULK_DENSITY_G_CM3 = Decimal("5.513443")
EARTH_CRUST_THICKNESS_KM = Decimal("35")
EARTH_INTERNAL_HEAT_TW = Decimal("47")
ROTATION_PERIOD_HOURS = Decimal("24")
ORBITAL_PERIOD_DAYS = Decimal("364")
AXIAL_TILT_STATE = "seasonal"
AXIAL_TILT_NUMERIC_STATUS = "pending"
ORBITAL_FRAME = "geocentric_luminary"
ORBITAL_DETAIL_STATUS = "pending"
BULK_WORLD_CLASS = "rock_dominant_terrestrial"

# Keep the internal model exact and deterministic, then round only for display.
INITIAL_RADIUS_KM = EARTH_RADIUS_KM / Decimal("7")
INITIAL_CRUST_THICKNESS_KM = EARTH_CRUST_THICKNESS_KM / Decimal("7")
MANTLE_CONVECTION_RELATIVE = Decimal("1.0")

GROWTH_RATIO = EARTH_RADIUS_KM / INITIAL_RADIUS_KM
GROWTH_CONSTANT_PER_YEAR = GROWTH_RATIO.ln() / Decimal(TOTAL_DURATION_YEARS)
GROWTH_CONSTANT_PER_GYR = GROWTH_CONSTANT_PER_YEAR * YEARS_PER_GYR


@dataclass(frozen=True)
class SimulationCriteria:
    total_duration_years: int
    step_years: int
    interval_count: int
    iteration_count: int


@dataclass(frozen=True)
class PlanetState:
    step_index: int
    age_years: int
    mass_earth: Decimal
    radius_km: Decimal
    crust_thickness_km: Decimal
    density_g_cm3: Decimal
    internal_heat_tw: Decimal
    core_state: str
    mantle_state: str
    crust_state: str
    rotation_hours: Decimal
    axial_tilt_state: str
    orbital_period_days: Decimal
    magnetic_field: str
    atmosphere_retention: str
    world_class: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's planet-scale properties from formation to present "
            "using fixed deterministic time steps."
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


def build_criteria(step_years: int) -> SimulationCriteria:
    if step_years <= 0:
        raise ValueError("--step-years must be a positive integer.")
    if TOTAL_DURATION_YEARS % step_years != 0:
        raise ValueError(
            "--step-years must evenly divide the total simulation duration "
            f"of {TOTAL_DURATION_YEARS} years."
        )

    interval_count = TOTAL_DURATION_YEARS // step_years
    return SimulationCriteria(
        total_duration_years=TOTAL_DURATION_YEARS,
        step_years=step_years,
        interval_count=interval_count,
        iteration_count=interval_count + 1,
    )


def radius_at(age_years: int) -> Decimal:
    elapsed = Decimal(age_years)
    return INITIAL_RADIUS_KM * (GROWTH_CONSTANT_PER_YEAR * elapsed).exp()


def age_fraction_at(age_years: int) -> Decimal:
    return Decimal(age_years) / Decimal(TOTAL_DURATION_YEARS)


def radius_ratio_at(radius_km: Decimal) -> Decimal:
    return radius_km / EARTH_RADIUS_KM


def mass_earth_at(radius_km: Decimal) -> Decimal:
    return radius_ratio_at(radius_km) ** 3


def mass_kg_at(radius_km: Decimal) -> Decimal:
    return EARTH_MASS_KG * mass_earth_at(radius_km)


def density_g_cm3_at(radius_km: Decimal) -> Decimal:
    radius_cm = radius_km * CM_PER_KM
    volume_cm3 = FOUR_THIRDS_PI * (radius_cm**3)
    mass_g = mass_kg_at(radius_km) * G_PER_KG
    return mass_g / volume_cm3


def crust_thickness_at(radius_km: Decimal) -> Decimal:
    return EARTH_CRUST_THICKNESS_KM * (radius_km / EARTH_RADIUS_KM)


def internal_heat_at(radius_km: Decimal) -> Decimal:
    return EARTH_INTERNAL_HEAT_TW * (radius_km / EARTH_RADIUS_KM) ** 3


def core_state_at(age_years: int) -> str:
    fraction = age_fraction_at(age_years)
    if fraction < Decimal("0.10"):
        return "forming"
    if fraction < Decimal("0.25"):
        return "stabilizing"
    return "stable"


def mantle_state_at(age_years: int) -> str:
    fraction = age_fraction_at(age_years)
    if fraction < Decimal("0.10"):
        return "mixed"
    if fraction < Decimal("0.35"):
        return "layering"
    return "active"


def crust_state_at(age_years: int) -> str:
    fraction = age_fraction_at(age_years)
    if fraction < Decimal("0.12"):
        return "nascent"
    if fraction < Decimal("0.45"):
        return "forming"
    if fraction < Decimal("0.70"):
        return "stabilizing"
    return "stable"


def magnetic_field_at(age_years: int) -> str:
    return "present" if age_fraction_at(age_years) >= Decimal("0.25") else "absent"


def atmosphere_retention_at(radius_km: Decimal, magnetic_field: str) -> str:
    radius_ratio = radius_ratio_at(radius_km)
    if magnetic_field == "absent" and radius_ratio < Decimal("0.35"):
        return "weak"
    if radius_ratio < Decimal("0.70"):
        return "moderate"
    return "high"


def world_class_at(radius_km: Decimal) -> str:
    radius_ratio = radius_ratio_at(radius_km)
    if radius_ratio < Decimal("0.35"):
        return "proto_rock_terrestrial"
    if radius_ratio < Decimal("0.85"):
        return "developing_rock_terrestrial"
    return "mature_rock_terrestrial"


def simulate(criteria: SimulationCriteria) -> Iterable[PlanetState]:
    for step_index in range(criteria.iteration_count):
        age_years = step_index * criteria.step_years
        radius_km = radius_at(age_years)
        magnetic_field = magnetic_field_at(age_years)
        yield PlanetState(
            step_index=step_index,
            age_years=age_years,
            mass_earth=mass_earth_at(radius_km),
            radius_km=radius_km,
            crust_thickness_km=crust_thickness_at(radius_km),
            density_g_cm3=density_g_cm3_at(radius_km),
            internal_heat_tw=internal_heat_at(radius_km),
            core_state=core_state_at(age_years),
            mantle_state=mantle_state_at(age_years),
            crust_state=crust_state_at(age_years),
            rotation_hours=ROTATION_PERIOD_HOURS,
            axial_tilt_state=AXIAL_TILT_STATE,
            orbital_period_days=ORBITAL_PERIOD_DAYS,
            magnetic_field=magnetic_field,
            atmosphere_retention=atmosphere_retention_at(radius_km, magnetic_field),
            world_class=world_class_at(radius_km),
        )


def quantize(value: Decimal, places: int) -> Decimal:
    quantum = Decimal("1").scaleb(-places)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def format_decimal(value: Decimal, places: int) -> str:
    return f"{quantize(value, places):f}"


def validate_model() -> None:
    checks = (
        ("initial_radius_km", radius_at(START_AGE_YEARS), INITIAL_RADIUS_KM, 12),
        ("present_radius_km", radius_at(TOTAL_DURATION_YEARS), EARTH_RADIUS_KM, 12),
        ("initial_mass_earth", mass_earth_at(INITIAL_RADIUS_KM), Decimal("1") / Decimal("343"), 12),
        ("present_mass_earth", mass_earth_at(EARTH_RADIUS_KM), Decimal("1"), 12),
        (
            "present_density_g_cm3",
            density_g_cm3_at(EARTH_RADIUS_KM),
            EARTH_BULK_DENSITY_G_CM3,
            6,
        ),
        (
            "initial_crust_km",
            crust_thickness_at(INITIAL_RADIUS_KM),
            INITIAL_CRUST_THICKNESS_KM,
            12,
        ),
        (
            "present_crust_km",
            crust_thickness_at(EARTH_RADIUS_KM),
            EARTH_CRUST_THICKNESS_KM,
            12,
        ),
        (
            "present_internal_heat_tw",
            internal_heat_at(EARTH_RADIUS_KM),
            EARTH_INTERNAL_HEAT_TW,
            12,
        ),
        ("rotation_period_hours", ROTATION_PERIOD_HOURS, Decimal("24"), 12),
        ("orbital_period_days", ORBITAL_PERIOD_DAYS, Decimal("364"), 12),
    )

    for name, actual, expected, places in checks:
        if quantize(actual, places) != quantize(expected, places):
            raise ValueError(
                f"Model invariant failed for {name}: expected "
                f"{format_decimal(expected, places)}, got {format_decimal(actual, places)}."
            )


def print_input_criteria(criteria: SimulationCriteria) -> None:
    fields = [
        ("planet_name", "Aeron"),
        ("deterministic", "true"),
        ("bulk_world_class", BULK_WORLD_CLASS),
        ("start_age_years", str(START_AGE_YEARS)),
        ("total_duration_years", str(criteria.total_duration_years)),
        (
            "total_duration_gyr",
            format_decimal(Decimal(criteria.total_duration_years) / YEARS_PER_GYR, 6),
        ),
        ("end_age_years", str(criteria.total_duration_years)),
        ("step_years", str(criteria.step_years)),
        ("step_myr", format_decimal(Decimal(criteria.step_years) / YEARS_PER_MYR, 6)),
        ("interval_count", str(criteria.interval_count)),
        ("iteration_count", str(criteria.iteration_count)),
        ("radius_model", "exponential"),
        ("initial_radius_km", format_decimal(INITIAL_RADIUS_KM, 6)),
        ("present_radius_km", format_decimal(EARTH_RADIUS_KM, 6)),
        ("mass_model", "proportional_to_radius_cubed"),
        (
            "initial_mass_earth",
            format_decimal(mass_earth_at(INITIAL_RADIUS_KM), 6),
        ),
        ("present_mass_earth", format_decimal(Decimal("1"), 6)),
        ("density_model", "earth_like_rocky_bulk_density"),
        ("present_density_g_cm3", format_decimal(density_g_cm3_at(EARTH_RADIUS_KM), 6)),
        ("growth_constant_per_year", format_decimal(GROWTH_CONSTANT_PER_YEAR, 18)),
        ("growth_constant_per_gyr", format_decimal(GROWTH_CONSTANT_PER_GYR, 12)),
        ("crust_scaling", "proportional_to_radius"),
        ("initial_crust_km", format_decimal(INITIAL_CRUST_THICKNESS_KM, 6)),
        ("present_crust_km", format_decimal(EARTH_CRUST_THICKNESS_KM, 6)),
        ("mantle_convection_relative", format_decimal(MANTLE_CONVECTION_RELATIVE, 6)),
        ("internal_heat_scaling", "proportional_to_radius_cubed"),
        (
            "initial_internal_heat_tw",
            format_decimal(internal_heat_at(INITIAL_RADIUS_KM), 6),
        ),
        ("present_internal_heat_tw", format_decimal(EARTH_INTERNAL_HEAT_TW, 6)),
        ("rotation_period_hours", format_decimal(ROTATION_PERIOD_HOURS, 6)),
        ("axial_tilt_state", AXIAL_TILT_STATE),
        ("axial_tilt_numeric_status", AXIAL_TILT_NUMERIC_STATUS),
        ("orbital_period_days", format_decimal(ORBITAL_PERIOD_DAYS, 6)),
        ("orbital_frame", ORBITAL_FRAME),
        ("orbital_detail_status", ORBITAL_DETAIL_STATUS),
        ("dynamic_fields", "mass_earth, radius_km, crust_thickness_km, density_g_cm3, internal_heat_tw, core_state, mantle_state, crust_state, magnetic_field, atmosphere_retention, world_class"),
        ("stable_fields", "rotation_period_hours, axial_tilt_state, orbital_period_days, orbital_frame"),
    ]

    key_width = max(len(key) for key, _ in fields)
    print("INPUT CRITERIA")
    print("==============")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")
    print()


def print_table(criteria: SimulationCriteria) -> None:
    headers = (
        ("step", 8),
        ("age_myr", 12),
        ("mass_em", 10),
        ("radius_km", 16),
        ("crust_km", 10),
        ("rho_gcc", 10),
        ("heat_tw", 12),
        ("core", 12),
        ("mantle", 12),
        ("crust", 12),
        ("rot_h", 8),
        ("tilt", 10),
        ("year_d", 8),
        ("mag", 8),
        ("atm_ret", 10),
    )

    header_line = " ".join(f"{label:>{width}}" for label, width in headers)
    divider_line = " ".join("-" * width for _, width in headers)
    print(header_line)
    print(divider_line)

    for state in simulate(criteria):
        age_myr = format_decimal(Decimal(state.age_years) / YEARS_PER_MYR, 3)
        mass_earth = format_decimal(state.mass_earth, 6)
        radius_km = format_decimal(state.radius_km, 6)
        crust_thickness_km = format_decimal(state.crust_thickness_km, 6)
        density_g_cm3 = format_decimal(state.density_g_cm3, 6)
        internal_heat_tw = format_decimal(state.internal_heat_tw, 6)
        rotation_hours = format_decimal(state.rotation_hours, 3)
        orbital_period_days = format_decimal(state.orbital_period_days, 3)
        print(
            f"{state.step_index:>8d} "
            f"{age_myr:>12} "
            f"{mass_earth:>10} "
            f"{radius_km:>16} "
            f"{crust_thickness_km:>10} "
            f"{density_g_cm3:>10} "
            f"{internal_heat_tw:>12} "
            f"{state.core_state:>12} "
            f"{state.mantle_state:>12} "
            f"{state.crust_state:>12} "
            f"{rotation_hours:>8} "
            f"{state.axial_tilt_state:>10} "
            f"{orbital_period_days:>8} "
            f"{state.magnetic_field:>8} "
            f"{state.atmosphere_retention:>10}"
        )


def print_present_day_summary(criteria: SimulationCriteria) -> None:
    final_state = None
    for final_state in simulate(criteria):
        pass

    assert final_state is not None

    fields = [
        ("world_class", final_state.world_class),
        ("mass_earth", format_decimal(final_state.mass_earth, 6)),
        ("radius_km", format_decimal(final_state.radius_km, 6)),
        ("crust_thickness_km", format_decimal(final_state.crust_thickness_km, 6)),
        ("density_g_cm3", format_decimal(final_state.density_g_cm3, 6)),
        ("internal_heat_tw", format_decimal(final_state.internal_heat_tw, 6)),
        ("core_state", final_state.core_state),
        ("mantle_state", final_state.mantle_state),
        ("crust_state", final_state.crust_state),
        ("rotation_period_hours", format_decimal(final_state.rotation_hours, 6)),
        ("axial_tilt_state", final_state.axial_tilt_state),
        ("axial_tilt_numeric_status", AXIAL_TILT_NUMERIC_STATUS),
        ("orbital_period_days", format_decimal(final_state.orbital_period_days, 6)),
        ("orbital_frame", ORBITAL_FRAME),
        ("orbital_detail_status", ORBITAL_DETAIL_STATUS),
        ("magnetic_field", final_state.magnetic_field),
        ("atmosphere_retention", final_state.atmosphere_retention),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT WORLD SUMMARY")
    print("=====================")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")


def main() -> int:
    args = parse_args()
    try:
        criteria = build_criteria(args.step_years)
        validate_model()
    except ValueError as exc:
        raise SystemExit(str(exc))

    print_input_criteria(criteria)
    print_table(criteria)
    print_present_day_summary(criteria)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
