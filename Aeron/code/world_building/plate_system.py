#!/usr/bin/env python3
"""Deterministic plate-system simulation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable

try:
    from . import planet, proto_tectonics
except ImportError:
    import planet  # type: ignore
    import proto_tectonics  # type: ignore

getcontext().prec = 50

VALIDATION_STEP_YEARS = 100_000_000


@dataclass(frozen=True)
class PlateRegionTemplate:
    region_id: str
    motion_direction: str
    unit_x: Decimal
    unit_y: Decimal
    speed_weight: Decimal
    activation_rank: int
    overturn_boundary_mode: str
    stagnant_boundary_mode: str
    plate_boundary_mode: str
    zone_role: str


@dataclass(frozen=True)
class PlateRegionState:
    region_id: str
    status: str
    motion_direction: str
    speed_cm_per_yr: Decimal
    vector_x_cm_per_yr: Decimal
    vector_y_cm_per_yr: Decimal
    primary_boundary_mode: str
    zone_role: str


@dataclass(frozen=True)
class PlateSystemState:
    step_index: int
    age_years: int
    radius_km: Decimal
    tectonic_regime: str
    coherent_region_count: int
    active_plate_count: int
    mean_plate_speed_cm_per_yr: Decimal
    fastest_region_speed_cm_per_yr: Decimal
    spreading_rate_cm_per_yr: Decimal
    collision_rate_cm_per_yr: Decimal
    recycling_rate_cm_per_yr: Decimal
    transform_rate_cm_per_yr: Decimal
    crust_creation_rate_km2_per_yr: Decimal
    crust_destruction_rate_km2_per_yr: Decimal
    net_crust_balance_km2_per_yr: Decimal
    plate_regions: tuple[PlateRegionState, ...]
    world_class: str


REGION_TEMPLATES = (
    PlateRegionTemplate(
        region_id="boreal_keel_region",
        motion_direction="SSE",
        unit_x=Decimal("0.35"),
        unit_y=Decimal("-0.94"),
        speed_weight=Decimal("1.05"),
        activation_rank=1,
        overturn_boundary_mode="foundering",
        stagnant_boundary_mode="delamination",
        plate_boundary_mode="recycling",
        zone_role="northern_recycling_margin",
    ),
    PlateRegionTemplate(
        region_id="west_equatorial_rift_region",
        motion_direction="ENE",
        unit_x=Decimal("0.94"),
        unit_y=Decimal("0.35"),
        speed_weight=Decimal("1.10"),
        activation_rank=2,
        overturn_boundary_mode="proto_rifting",
        stagnant_boundary_mode="failed_rift",
        plate_boundary_mode="spreading",
        zone_role="western_equatorial_spreading_axis",
    ),
    PlateRegionTemplate(
        region_id="east_equatorial_shear_region",
        motion_direction="WSW",
        unit_x=Decimal("-0.94"),
        unit_y=Decimal("-0.35"),
        speed_weight=Decimal("1.08"),
        activation_rank=3,
        overturn_boundary_mode="shear_breakup",
        stagnant_boundary_mode="shear_break",
        plate_boundary_mode="transform",
        zone_role="eastern_equatorial_transform_link",
    ),
    PlateRegionTemplate(
        region_id="austral_collision_region",
        motion_direction="NNW",
        unit_x=Decimal("-0.35"),
        unit_y=Decimal("0.94"),
        speed_weight=Decimal("0.95"),
        activation_rank=4,
        overturn_boundary_mode="slab_drip",
        stagnant_boundary_mode="compression_front",
        plate_boundary_mode="collision",
        zone_role="austral_collision_front",
    ),
    PlateRegionTemplate(
        region_id="southern_spreading_region",
        motion_direction="WNW",
        unit_x=Decimal("-0.88"),
        unit_y=Decimal("0.47"),
        speed_weight=Decimal("0.90"),
        activation_rank=5,
        overturn_boundary_mode="proto_rifting",
        stagnant_boundary_mode="failed_rift",
        plate_boundary_mode="spreading",
        zone_role="southern_spreading_axis",
    ),
    PlateRegionTemplate(
        region_id="pelagic_transform_region",
        motion_direction="ESE",
        unit_x=Decimal("0.88"),
        unit_y=Decimal("-0.47"),
        speed_weight=Decimal("0.92"),
        activation_rank=6,
        overturn_boundary_mode="shear_breakup",
        stagnant_boundary_mode="shear_break",
        plate_boundary_mode="transform",
        zone_role="pelagic_transform_bridge",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's plate system by ticking the proto-tectonic layer "
            "and deriving discrete plate regions, motions, and crustal cycling."
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


def coherent_region_count_at(tectonic_regime: str) -> int:
    if tectonic_regime == "episodic_overturn":
        return 4
    if tectonic_regime == "stagnant_lid":
        return 5
    return 6


def active_plate_count_at(tectonic_regime: str, coherent_region_count: int) -> int:
    return coherent_region_count if tectonic_regime == "plate_like" else 0


def mean_plate_speed_cm_per_yr_at(
    state: proto_tectonics.ProtoTectonicsState,
) -> Decimal:
    if state.tectonic_regime == "episodic_overturn":
        return Decimal("0.40") + (Decimal("1.60") * state.plate_mobility_index)
    if state.tectonic_regime == "stagnant_lid":
        return Decimal("0.80") + (Decimal("2.20") * state.plate_mobility_index)
    return Decimal("1.40") + (Decimal("5.20") * state.plate_mobility_index)


def spreading_rate_cm_per_yr_at(
    state: proto_tectonics.ProtoTectonicsState, mean_plate_speed_cm_per_yr: Decimal
) -> Decimal:
    if state.tectonic_regime == "episodic_overturn":
        multiplier = Decimal("0.45")
    elif state.tectonic_regime == "stagnant_lid":
        multiplier = Decimal("0.30")
    else:
        multiplier = Decimal("0.60")
    return mean_plate_speed_cm_per_yr * multiplier * (
        Decimal("0.80") + (Decimal("0.20") * state.fracture_potential_index)
    )


def collision_rate_cm_per_yr_at(
    state: proto_tectonics.ProtoTectonicsState, mean_plate_speed_cm_per_yr: Decimal
) -> Decimal:
    if state.tectonic_regime == "episodic_overturn":
        multiplier = Decimal("0.20")
    elif state.tectonic_regime == "stagnant_lid":
        multiplier = Decimal("0.35")
    else:
        multiplier = Decimal("0.42")
    return mean_plate_speed_cm_per_yr * multiplier * (
        Decimal("0.75") + (Decimal("0.25") * state.lithosphere_rigidity_index)
    )


def recycling_rate_cm_per_yr_at(
    state: proto_tectonics.ProtoTectonicsState, mean_plate_speed_cm_per_yr: Decimal
) -> Decimal:
    if state.tectonic_regime == "episodic_overturn":
        multiplier = Decimal("0.65")
    elif state.tectonic_regime == "stagnant_lid":
        multiplier = Decimal("0.28")
    else:
        multiplier = Decimal("0.48")
    return mean_plate_speed_cm_per_yr * multiplier * (
        Decimal("0.70") + (Decimal("0.30") * state.plate_mobility_index)
    )


def transform_rate_cm_per_yr_at(
    state: proto_tectonics.ProtoTectonicsState, mean_plate_speed_cm_per_yr: Decimal
) -> Decimal:
    if state.tectonic_regime == "episodic_overturn":
        multiplier = Decimal("0.15")
    elif state.tectonic_regime == "stagnant_lid":
        multiplier = Decimal("0.20")
    else:
        multiplier = Decimal("0.30")
    return mean_plate_speed_cm_per_yr * multiplier * (
        Decimal("0.80") + (Decimal("0.20") * state.fracture_potential_index)
    )


def surface_area_km2_at(radius_km: Decimal) -> Decimal:
    return Decimal("4") * planet.PI * (radius_km**2)


def crust_creation_rate_km2_per_yr_at(
    state: proto_tectonics.ProtoTectonicsState, spreading_rate_cm_per_yr: Decimal
) -> Decimal:
    surface_area_km2 = surface_area_km2_at(state.radius_km)
    spreading_speed_km_per_yr = spreading_rate_cm_per_yr / Decimal("100000")
    if state.tectonic_regime == "episodic_overturn":
        boundary_fraction = Decimal("0.00006")
        efficiency = Decimal("0.55")
    elif state.tectonic_regime == "stagnant_lid":
        boundary_fraction = Decimal("0.00010")
        efficiency = Decimal("0.65")
    else:
        boundary_fraction = Decimal("0.00014")
        efficiency = Decimal("0.82")
    return surface_area_km2 * boundary_fraction * spreading_speed_km_per_yr * efficiency


def crust_destruction_rate_km2_per_yr_at(
    state: proto_tectonics.ProtoTectonicsState, recycling_rate_cm_per_yr: Decimal
) -> Decimal:
    surface_area_km2 = surface_area_km2_at(state.radius_km)
    recycling_speed_km_per_yr = recycling_rate_cm_per_yr / Decimal("100000")
    if state.tectonic_regime == "episodic_overturn":
        boundary_fraction = Decimal("0.00006")
        efficiency = Decimal("0.65")
    elif state.tectonic_regime == "stagnant_lid":
        boundary_fraction = Decimal("0.00010")
        efficiency = Decimal("0.55")
    else:
        boundary_fraction = Decimal("0.00014")
        efficiency = Decimal("0.88")
    return (
        surface_area_km2 * boundary_fraction * recycling_speed_km_per_yr * efficiency
    )


def region_status_at(tectonic_regime: str) -> str:
    if tectonic_regime == "episodic_overturn":
        return "overturn_domain"
    if tectonic_regime == "stagnant_lid":
        return "proto_plate_region"
    return "active_plate"


def primary_boundary_mode_at(
    template: PlateRegionTemplate, tectonic_regime: str
) -> str:
    if tectonic_regime == "episodic_overturn":
        return template.overturn_boundary_mode
    if tectonic_regime == "stagnant_lid":
        return template.stagnant_boundary_mode
    return template.plate_boundary_mode


def active_templates_at(tectonic_regime: str) -> tuple[PlateRegionTemplate, ...]:
    coherent_region_count = coherent_region_count_at(tectonic_regime)
    return tuple(
        template
        for template in REGION_TEMPLATES
        if template.activation_rank <= coherent_region_count
    )


def plate_regions_at(
    state: proto_tectonics.ProtoTectonicsState, mean_plate_speed_cm_per_yr: Decimal
) -> tuple[PlateRegionState, ...]:
    status = region_status_at(state.tectonic_regime)
    region_states: list[PlateRegionState] = []

    for template in active_templates_at(state.tectonic_regime):
        speed_cm_per_yr = mean_plate_speed_cm_per_yr * template.speed_weight
        region_states.append(
            PlateRegionState(
                region_id=template.region_id,
                status=status,
                motion_direction=template.motion_direction,
                speed_cm_per_yr=speed_cm_per_yr,
                vector_x_cm_per_yr=speed_cm_per_yr * template.unit_x,
                vector_y_cm_per_yr=speed_cm_per_yr * template.unit_y,
                primary_boundary_mode=primary_boundary_mode_at(
                    template, state.tectonic_regime
                ),
                zone_role=template.zone_role,
            )
        )

    return tuple(region_states)


def plate_system_state_from_proto_tectonics_state(
    base_state: proto_tectonics.ProtoTectonicsState,
) -> PlateSystemState:
    coherent_region_count = coherent_region_count_at(base_state.tectonic_regime)
    active_plate_count = active_plate_count_at(
        base_state.tectonic_regime, coherent_region_count
    )
    mean_plate_speed_cm_per_yr = mean_plate_speed_cm_per_yr_at(base_state)
    spreading_rate_cm_per_yr = spreading_rate_cm_per_yr_at(
        base_state, mean_plate_speed_cm_per_yr
    )
    collision_rate_cm_per_yr = collision_rate_cm_per_yr_at(
        base_state, mean_plate_speed_cm_per_yr
    )
    recycling_rate_cm_per_yr = recycling_rate_cm_per_yr_at(
        base_state, mean_plate_speed_cm_per_yr
    )
    transform_rate_cm_per_yr = transform_rate_cm_per_yr_at(
        base_state, mean_plate_speed_cm_per_yr
    )
    plate_regions = plate_regions_at(base_state, mean_plate_speed_cm_per_yr)
    crust_creation_rate_km2_per_yr = crust_creation_rate_km2_per_yr_at(
        base_state, spreading_rate_cm_per_yr
    )
    crust_destruction_rate_km2_per_yr = crust_destruction_rate_km2_per_yr_at(
        base_state, recycling_rate_cm_per_yr
    )
    return PlateSystemState(
        step_index=base_state.step_index,
        age_years=base_state.age_years,
        radius_km=base_state.radius_km,
        tectonic_regime=base_state.tectonic_regime,
        coherent_region_count=coherent_region_count,
        active_plate_count=active_plate_count,
        mean_plate_speed_cm_per_yr=mean_plate_speed_cm_per_yr,
        fastest_region_speed_cm_per_yr=max(
            region.speed_cm_per_yr for region in plate_regions
        ),
        spreading_rate_cm_per_yr=spreading_rate_cm_per_yr,
        collision_rate_cm_per_yr=collision_rate_cm_per_yr,
        recycling_rate_cm_per_yr=recycling_rate_cm_per_yr,
        transform_rate_cm_per_yr=transform_rate_cm_per_yr,
        crust_creation_rate_km2_per_yr=crust_creation_rate_km2_per_yr,
        crust_destruction_rate_km2_per_yr=crust_destruction_rate_km2_per_yr,
        net_crust_balance_km2_per_yr=(
            crust_creation_rate_km2_per_yr - crust_destruction_rate_km2_per_yr
        ),
        plate_regions=plate_regions,
        world_class=base_state.world_class,
    )


def simulate(criteria: planet.SimulationCriteria) -> Iterable[PlateSystemState]:
    for base_state in proto_tectonics.simulate(criteria):
        yield plate_system_state_from_proto_tectonics_state(base_state)


def first_active_plate_state(
    states: Iterable[PlateSystemState],
) -> PlateSystemState | None:
    for state in states:
        if state.active_plate_count > 0:
            return state
    return None


def validate_model() -> None:
    proto_tectonics.validate_model()
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria))
    initial_state = states[0]
    present_state = states[-1]
    first_active_state = first_active_plate_state(states)

    if initial_state.active_plate_count != 0:
        raise ValueError("Active plates should not exist at the start of the layer.")
    if present_state.active_plate_count < 4:
        raise ValueError("Present-day Aeron should sustain multiple active plates.")
    if first_active_state is None:
        raise ValueError("A discrete active plate system must emerge within the span.")
    if present_state.crust_creation_rate_km2_per_yr <= Decimal("0"):
        raise ValueError("Crust creation rate must be positive in the present-day state.")
    if present_state.crust_destruction_rate_km2_per_yr <= Decimal("0"):
        raise ValueError(
            "Crust destruction rate must be positive in the present-day state."
        )


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "plate_system_simulation"),
        ("proto_tectonics_source", "proto_tectonics.py"),
        ("surface_temperature_source", "surface_temperature.py"),
        ("early_atmosphere_source", "early_atmosphere.py"),
        ("primary_crust_source", "primary_crust.py"),
        ("interior_source", "interior.py"),
        ("planet_source", "planet.py"),
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
        ("region_model", "fixed_template_plate_regions"),
        ("motion_model", "regime_scaled_vector_field"),
        ("boundary_model", "spreading_collision_recycling_transform"),
        ("crust_budget_model", "surface_area_scaled_creation_and_destruction"),
        (
            "dynamic_fields",
            "coherent_region_count, active_plate_count, "
            "mean_plate_speed_cm_per_yr, spreading_rate_cm_per_yr, "
            "collision_rate_cm_per_yr, recycling_rate_cm_per_yr, "
            "transform_rate_cm_per_yr, crust_creation_rate_km2_per_yr, "
            "crust_destruction_rate_km2_per_yr, net_crust_balance_km2_per_yr",
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
        ("regions", 8),
        ("plates", 8),
        ("mean_v", 9),
        ("spread", 9),
        ("collide", 9),
        ("recycle", 9),
        ("transform", 10),
        ("create", 9),
        ("destroy", 9),
        ("net", 9),
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
            f"{state.coherent_region_count:>8d} "
            f"{state.active_plate_count:>8d} "
            f"{planet.format_decimal(state.mean_plate_speed_cm_per_yr, 3):>9} "
            f"{planet.format_decimal(state.spreading_rate_cm_per_yr, 3):>9} "
            f"{planet.format_decimal(state.collision_rate_cm_per_yr, 3):>9} "
            f"{planet.format_decimal(state.recycling_rate_cm_per_yr, 3):>9} "
            f"{planet.format_decimal(state.transform_rate_cm_per_yr, 3):>10} "
            f"{planet.format_decimal(state.crust_creation_rate_km2_per_yr, 3):>9} "
            f"{planet.format_decimal(state.crust_destruction_rate_km2_per_yr, 3):>9} "
            f"{planet.format_decimal(state.net_crust_balance_km2_per_yr, 3):>9}"
        )


def print_present_day_summary(criteria: planet.SimulationCriteria) -> None:
    states = list(simulate(criteria))
    final_state = states[-1]
    first_active_state = first_active_plate_state(states)

    assert first_active_state is not None

    fields = [
        ("world_class", final_state.world_class),
        ("tectonic_regime", final_state.tectonic_regime),
        ("coherent_region_count", str(final_state.coherent_region_count)),
        ("active_plate_count", str(final_state.active_plate_count)),
        (
            "mean_plate_speed_cm_per_yr",
            planet.format_decimal(final_state.mean_plate_speed_cm_per_yr, 6),
        ),
        (
            "fastest_region_speed_cm_per_yr",
            planet.format_decimal(final_state.fastest_region_speed_cm_per_yr, 6),
        ),
        (
            "spreading_rate_cm_per_yr",
            planet.format_decimal(final_state.spreading_rate_cm_per_yr, 6),
        ),
        (
            "collision_rate_cm_per_yr",
            planet.format_decimal(final_state.collision_rate_cm_per_yr, 6),
        ),
        (
            "recycling_rate_cm_per_yr",
            planet.format_decimal(final_state.recycling_rate_cm_per_yr, 6),
        ),
        (
            "transform_rate_cm_per_yr",
            planet.format_decimal(final_state.transform_rate_cm_per_yr, 6),
        ),
        (
            "crust_creation_rate_km2_per_yr",
            planet.format_decimal(final_state.crust_creation_rate_km2_per_yr, 6),
        ),
        (
            "crust_destruction_rate_km2_per_yr",
            planet.format_decimal(final_state.crust_destruction_rate_km2_per_yr, 6),
        ),
        (
            "net_crust_balance_km2_per_yr",
            planet.format_decimal(final_state.net_crust_balance_km2_per_yr, 6),
        ),
        ("first_active_plate_step", str(first_active_state.step_index)),
        (
            "first_active_plate_age_myr",
            planet.format_decimal(
                Decimal(first_active_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT PLATE-SYSTEM SUMMARY")
    print("============================")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")

    print()
    print("PRESENT PLATE REGIONS")
    print("=====================")
    headers = (
        ("region", 30),
        ("status", 18),
        ("dir", 6),
        ("speed", 9),
        ("vx", 9),
        ("vy", 9),
        ("boundary", 12),
        ("role", 34),
    )
    header_line = " ".join(f"{label:>{width}}" for label, width in headers)
    divider_line = " ".join("-" * width for _, width in headers)
    print(header_line)
    print(divider_line)
    for region in final_state.plate_regions:
        print(
            f"{region.region_id:>30} "
            f"{region.status:>18} "
            f"{region.motion_direction:>6} "
            f"{planet.format_decimal(region.speed_cm_per_yr, 3):>9} "
            f"{planet.format_decimal(region.vector_x_cm_per_yr, 3):>9} "
            f"{planet.format_decimal(region.vector_y_cm_per_yr, 3):>9} "
            f"{region.primary_boundary_mode:>12} "
            f"{region.zone_role:>34}"
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
