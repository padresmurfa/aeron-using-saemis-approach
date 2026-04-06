#!/usr/bin/env python3
"""Deterministic plate-system simulation for Aeron."""

from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Iterable, Sequence

try:
    from .world_building_paths import step_output_path
    from .world_building_support import load_pipeline_module, materialize_layer_states
    from .world_building_surface import (
        planet_surface_from_plate_surface_model,
        save_planet_surface,
        surface_json_payload,
        surface_state_output_path,
    )
except ImportError:
    from world_building_paths import step_output_path  # type: ignore
    from world_building_support import load_pipeline_module, materialize_layer_states  # type: ignore
    from world_building_surface import (  # type: ignore
        planet_surface_from_plate_surface_model,
        save_planet_surface,
        surface_json_payload,
        surface_state_output_path,
    )

planet = load_pipeline_module(__package__, __file__, "01_planet")
proto_tectonics = load_pipeline_module(__package__, __file__, "06_proto_tectonics")

getcontext().prec = 50

VALIDATION_STEP_YEARS = 100_000_000
DEFAULT_SURFACE_GRID_RESOLUTION = proto_tectonics.DEFAULT_SURFACE_GRID_RESOLUTION
SURFACE_GEOMETRY_MODEL = "deterministic_plate_surface_partition"
SURFACE_GEOMETRY_KIND = "spherical_lat_lon_cells"
BOUNDARY_TYPE_ORDER = (
    "spreading",
    "convergent",
    "transform",
    "indeterminate",
)
PLATE_FILL_PALETTE = (
    "#355070",
    "#6d597a",
    "#b56576",
    "#e56b6f",
    "#eaac8b",
    "#7f9c96",
)
BOUNDARY_COLORS = {
    "spreading": "#2f6fed",
    "convergent": "#c4333b",
    "transform": "#f0a202",
    "indeterminate": "#7c7c7c",
}
LOCAL_ROLE_COLORS = {
    "interior": "#d7dadc",
    "spreading_boundary": "#93c5fd",
    "convergent_boundary": "#fca5a5",
    "transform_boundary": "#fde68a",
    "inactive": "#9ca3af",
    "ambiguous": "#c4b5fd",
}


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
    plate_id: str
    status: str
    active: str
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


@dataclass(frozen=True)
class PlateSurfaceRegionState:
    region_id: str
    cell_id: str
    latitude_index: int
    longitude_index: int
    center_latitude_degrees: float
    center_longitude_degrees: float
    latitude_south_degrees: float
    latitude_north_degrees: float
    longitude_west_degrees: float
    longitude_east_degrees: float
    neighbor_region_ids: tuple[str, ...]
    tectonic_active: str
    plate_id: str
    plate_region_id: str
    local_role: str
    motion_direction: str
    speed_cm_per_yr: float
    vector_x_cm_per_yr: float
    vector_y_cm_per_yr: float
    lithosphere_rigidity_index: float
    thermal_stress_index: float
    fracture_susceptibility_index: float
    proto_rift_tendency_index: float
    upwelling_influence_index: float
    recycling_tendency_index: float
    crust_creation_tendency_index: float
    crust_destruction_tendency_index: float


@dataclass(frozen=True)
class PlateSurfacePlateState:
    plate_id: str
    plate_region_id: str
    status: str
    active: str
    member_region_ids: tuple[str, ...]
    neighbor_plate_ids: tuple[str, ...]
    centroid_latitude_degrees: float
    centroid_longitude_degrees: float
    motion_direction: str
    speed_cm_per_yr: float
    vector_x_cm_per_yr: float
    vector_y_cm_per_yr: float
    region_count: int
    crust_creation_rate_km2_per_yr: float
    crust_destruction_rate_km2_per_yr: float
    fill_color: str


@dataclass(frozen=True)
class PlateBoundaryState:
    boundary_id: str
    region_a_id: str
    region_b_id: str
    plate_a_id: str
    plate_b_id: str
    boundary_type: str
    edge_orientation: str
    midpoint_latitude_degrees: float
    midpoint_longitude_degrees: float
    line_start_longitude_degrees: float
    line_start_latitude_degrees: float
    line_end_longitude_degrees: float
    line_end_latitude_degrees: float
    interaction_index: float
    relative_motion_cm_per_yr: float
    crust_creation_tendency_index: float
    crust_destruction_tendency_index: float
    transform_tendency_index: float


@dataclass(frozen=True)
class PlateAdjacencyState:
    adjacency_id: str
    plate_a_id: str
    plate_b_id: str
    dominant_boundary_type: str
    boundary_count: int
    spreading_count: int
    convergent_count: int
    transform_count: int
    indeterminate_count: int


@dataclass(frozen=True)
class PlateSurfaceModel:
    model: str
    geometry: str
    source_surface_grid_model: str
    surface_grid_resolution: str
    longitude_cells: int
    latitude_cells: int
    region_count: int
    plate_count: int
    boundary_count: int
    plate_adjacency_count: int
    present_day_regime: str
    source_major_fracture_zones: str
    source_spreading_zones: str
    source_recycling_zones: str
    active_plate_ids: tuple[str, ...]
    boundary_type_counts: dict[str, int]
    region_fields: tuple[str, ...]
    boundary_types: tuple[str, ...]
    regions: tuple[PlateSurfaceRegionState, ...]
    plates: tuple[PlateSurfacePlateState, ...]
    boundaries: tuple[PlateBoundaryState, ...]
    plate_adjacencies: tuple[PlateAdjacencyState, ...]


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
            "and deriving explicit coarse surface plate geometry, motions, and "
            "crustal cycling."
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
        default=DEFAULT_SURFACE_GRID_RESOLUTION,
        help=(
            "Coarse surface grid resolution as <longitude>x<latitude> cells for "
            "the plate surface geometry. Default: "
            f"{DEFAULT_SURFACE_GRID_RESOLUTION}."
        ),
    )
    return parser.parse_args()


def clamp_unit_interval(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")
    if value > Decimal("1"):
        return Decimal("1")
    return value


def clamp_unit_float(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def parse_surface_grid_resolution(spec: str) -> tuple[int, int]:
    return proto_tectonics.parse_surface_grid_resolution(spec)


def surface_grid_resolution_label(resolution: tuple[int, int]) -> str:
    lon_cells, lat_cells = resolution
    return f"{lon_cells}x{lat_cells}"


def plate_surface_artifact_key(resolution: tuple[int, int]) -> str:
    return f"plate_surface:{surface_grid_resolution_label(resolution)}"


def visualization_output_path(current_file: str, suffix: str) -> Path:
    return step_output_path(current_file, suffix, default_extension=".png")


def plate_map_output_path(current_file: str) -> Path:
    return visualization_output_path(current_file, "__plate_map_present.png")


def boundary_debug_output_path(current_file: str) -> Path:
    return visualization_output_path(current_file, "__boundary_debug_present.png")


def template_plate_id(template: PlateRegionTemplate) -> str:
    return template.region_id.replace("_region", "_plate")


def template_short_label(plate_id: str) -> str:
    base = plate_id.removesuffix("_plate")
    return "".join(token[0].upper() for token in base.split("_") if token)


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
                plate_id=template_plate_id(template),
                status=status,
                active="yes" if state.tectonic_regime == "plate_like" else "no",
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


def wrap_longitude(longitude_degrees: float) -> float:
    wrapped = longitude_degrees
    while wrapped <= -180.0:
        wrapped += 360.0
    while wrapped > 180.0:
        wrapped -= 360.0
    return wrapped


def wrapped_longitude_delta(
    source_longitude_degrees: float, target_longitude_degrees: float
) -> float:
    delta = target_longitude_degrees - source_longitude_degrees
    while delta <= -180.0:
        delta += 360.0
    while delta > 180.0:
        delta -= 360.0
    return delta


def location_distance_degrees(
    latitude_a_degrees: float,
    longitude_a_degrees: float,
    latitude_b_degrees: float,
    longitude_b_degrees: float,
) -> float:
    longitude_delta = wrapped_longitude_delta(
        longitude_a_degrees, longitude_b_degrees
    )
    mean_latitude_scale = max(
        0.25,
        math.cos(
            math.radians((latitude_a_degrees + latitude_b_degrees) * 0.5)
        ),
    )
    latitude_delta = latitude_b_degrees - latitude_a_degrees
    return math.sqrt(
        (latitude_delta**2) + ((longitude_delta * mean_latitude_scale) ** 2)
    )


def distance_score(
    latitude_a_degrees: float,
    longitude_a_degrees: float,
    latitude_b_degrees: float,
    longitude_b_degrees: float,
    *,
    scale_degrees: float,
) -> float:
    distance = location_distance_degrees(
        latitude_a_degrees,
        longitude_a_degrees,
        latitude_b_degrees,
        longitude_b_degrees,
    )
    return clamp_unit_float(math.exp(-((distance / scale_degrees) ** 2)))


def circular_mean_longitude(longitudes_degrees: Sequence[float]) -> float:
    if not longitudes_degrees:
        return 0.0
    x_component = sum(math.cos(math.radians(value)) for value in longitudes_degrees)
    y_component = sum(math.sin(math.radians(value)) for value in longitudes_degrees)
    if abs(x_component) < 1e-9 and abs(y_component) < 1e-9:
        return 0.0
    return wrap_longitude(math.degrees(math.atan2(y_component, x_component)))


def boundary_family_at(boundary_mode: str) -> str:
    if boundary_mode in {"spreading", "proto_rifting", "failed_rift"}:
        return "spreading"
    if boundary_mode in {
        "recycling",
        "collision",
        "compression_front",
        "delamination",
        "foundering",
        "slab_drip",
    }:
        return "convergent"
    if boundary_mode in {"transform", "shear_breakup", "shear_break"}:
        return "transform"
    return "indeterminate"


def template_anchor_latitude(template: PlateRegionTemplate) -> float:
    region_id = template.region_id
    if "boreal" in region_id:
        return 58.0
    if "austral" in region_id:
        return -54.0
    if "southern" in region_id:
        return -34.0
    if "equatorial" in region_id:
        return 6.0
    if "pelagic" in region_id:
        return -10.0
    return 0.0


def template_anchor_longitude(template: PlateRegionTemplate) -> float:
    region_id = template.region_id
    if "west" in region_id:
        return -78.0
    if "east" in region_id:
        return 104.0
    if "southern" in region_id:
        return -138.0
    if "pelagic" in region_id:
        return 166.0
    if "boreal" in region_id:
        return 28.0
    if "austral" in region_id:
        return 52.0
    return 0.0


def template_anchor_scales(template: PlateRegionTemplate) -> tuple[float, float]:
    region_id = template.region_id
    if "equatorial" in region_id:
        return 18.0, 54.0
    if "boreal" in region_id or "austral" in region_id:
        return 20.0, 58.0
    if "southern" in region_id:
        return 16.0, 48.0
    if "pelagic" in region_id:
        return 20.0, 44.0
    return 24.0, 60.0


def template_field_affinity(
    template: PlateRegionTemplate,
    cell: proto_tectonics.ProtoTectonicCell,
    tectonic_regime: str,
) -> float:
    family = boundary_family_at(primary_boundary_mode_at(template, tectonic_regime))
    if family == "spreading":
        return clamp_unit_float(
            (0.40 * cell.proto_rift_tendency_index)
            + (0.30 * cell.upwelling_influence_index)
            + (0.20 * cell.fracture_susceptibility_index)
            + (0.10 * (1.0 - cell.lithosphere_rigidity_index))
        )
    if family == "convergent":
        return clamp_unit_float(
            (0.35 * cell.recycling_tendency_index)
            + (0.30 * cell.lithosphere_rigidity_index)
            + (0.20 * cell.fracture_susceptibility_index)
            + (0.15 * cell.thermal_stress_index)
        )
    if family == "transform":
        return clamp_unit_float(
            (0.45 * cell.fracture_susceptibility_index)
            + (0.25 * cell.thermal_stress_index)
            + (0.15 * cell.proto_rift_tendency_index)
            + (0.15 * cell.upwelling_influence_index)
        )
    return clamp_unit_float(
        (0.30 * cell.lithosphere_rigidity_index)
        + (0.25 * cell.thermal_stress_index)
        + (0.25 * cell.fracture_susceptibility_index)
        + (0.20 * cell.recycling_tendency_index)
    )


def template_anchor_score(
    template: PlateRegionTemplate, cell: proto_tectonics.ProtoTectonicCell
) -> float:
    latitude_scale, longitude_scale = template_anchor_scales(template)
    latitude_score = math.exp(
        -(
            (
                (cell.latitude_degrees - template_anchor_latitude(template))
                / latitude_scale
            )
            ** 2
        )
    )
    longitude_score = math.exp(
        -(
            (
                wrapped_longitude_delta(
                    template_anchor_longitude(template), cell.longitude_degrees
                )
                / longitude_scale
            )
            ** 2
        )
    )
    return clamp_unit_float((0.55 * latitude_score) + (0.45 * longitude_score))


def seed_selection_score(
    template: PlateRegionTemplate,
    cell: proto_tectonics.ProtoTectonicCell,
    selected_seed_cells: Sequence[proto_tectonics.ProtoTectonicCell],
    tectonic_regime: str,
) -> float:
    field_score = template_field_affinity(template, cell, tectonic_regime)
    anchor_score = template_anchor_score(template, cell)
    if not selected_seed_cells:
        separation_score = 1.0
    else:
        min_distance = min(
            location_distance_degrees(
                cell.latitude_degrees,
                cell.longitude_degrees,
                other.latitude_degrees,
                other.longitude_degrees,
            )
            for other in selected_seed_cells
        )
        separation_score = clamp_unit_float(min_distance / 48.0)
    return clamp_unit_float(
        (0.55 * field_score) + (0.30 * anchor_score) + (0.15 * separation_score)
    )


def select_plate_seed_cells(
    cells: Sequence[proto_tectonics.ProtoTectonicCell],
    templates: Sequence[PlateRegionTemplate],
    tectonic_regime: str,
) -> dict[str, proto_tectonics.ProtoTectonicCell]:
    ordered_cells = sorted(cells, key=lambda cell: (cell.latitude_index, cell.longitude_index))
    seed_lookup: dict[str, proto_tectonics.ProtoTectonicCell] = {}
    chosen_cells: list[proto_tectonics.ProtoTectonicCell] = []
    for template in templates:
        best_cell = max(
            ordered_cells,
            key=lambda cell: (
                seed_selection_score(template, cell, chosen_cells, tectonic_regime),
                template_anchor_score(template, cell),
                template_field_affinity(template, cell, tectonic_regime),
            ),
        )
        seed_lookup[template.region_id] = best_cell
        chosen_cells.append(best_cell)
    return seed_lookup


def cell_assignment_score(
    cell: proto_tectonics.ProtoTectonicCell,
    template: PlateRegionTemplate,
    seed_cell: proto_tectonics.ProtoTectonicCell,
    tectonic_regime: str,
) -> float:
    seed_distance_score = distance_score(
        cell.latitude_degrees,
        cell.longitude_degrees,
        seed_cell.latitude_degrees,
        seed_cell.longitude_degrees,
        scale_degrees=62.0,
    )
    field_score = template_field_affinity(template, cell, tectonic_regime)
    anchor_score = template_anchor_score(template, cell)
    return clamp_unit_float(
        (0.60 * seed_distance_score) + (0.25 * field_score) + (0.15 * anchor_score)
    )


def assign_cells_to_plates(
    cells: Sequence[proto_tectonics.ProtoTectonicCell],
    templates: Sequence[PlateRegionTemplate],
    seed_lookup: dict[str, proto_tectonics.ProtoTectonicCell],
    tectonic_regime: str,
) -> dict[str, PlateRegionTemplate]:
    assignment: dict[str, PlateRegionTemplate] = {}
    for cell in sorted(cells, key=lambda item: (item.latitude_index, item.longitude_index)):
        best_template = max(
            templates,
            key=lambda template: cell_assignment_score(
                cell,
                template,
                seed_lookup[template.region_id],
                tectonic_regime,
            ),
        )
        assignment[cell.cell_id] = best_template
    return assignment


def cell_bounds(
    latitude_index: int,
    longitude_index: int,
    resolution: tuple[int, int],
) -> tuple[float, float, float, float]:
    lon_cells, lat_cells = resolution
    lon_step = 360.0 / lon_cells
    lat_step = 180.0 / lat_cells
    longitude_west = -180.0 + (longitude_index * lon_step)
    longitude_east = longitude_west + lon_step
    latitude_south = -90.0 + (latitude_index * lat_step)
    latitude_north = latitude_south + lat_step
    return longitude_west, longitude_east, latitude_south, latitude_north


def neighbor_region_ids_at(
    latitude_index: int, longitude_index: int, resolution: tuple[int, int]
) -> tuple[str, ...]:
    lon_cells, lat_cells = resolution
    neighbors: list[str] = []
    if latitude_index < lat_cells - 1:
        neighbors.append(f"lat_{latitude_index + 1:02d}_lon_{longitude_index:03d}")
    neighbors.append(f"lat_{latitude_index:02d}_lon_{(longitude_index + 1) % lon_cells:03d}")
    if latitude_index > 0:
        neighbors.append(f"lat_{latitude_index - 1:02d}_lon_{longitude_index:03d}")
    neighbors.append(f"lat_{latitude_index:02d}_lon_{(longitude_index - 1) % lon_cells:03d}")
    return tuple(neighbors)


def boundary_family_bias(
    target_family: str, plate_a: PlateRegionState, plate_b: PlateRegionState
) -> float:
    matches = int(boundary_family_at(plate_a.primary_boundary_mode) == target_family)
    matches += int(boundary_family_at(plate_b.primary_boundary_mode) == target_family)
    if matches == 2:
        return 1.15
    if matches == 1:
        return 1.07
    return 1.0


def boundary_state_at(
    cell_a: proto_tectonics.ProtoTectonicCell,
    cell_b: proto_tectonics.ProtoTectonicCell,
    plate_a: PlateRegionState,
    plate_b: PlateRegionState,
    *,
    edge_kind: str,
    resolution: tuple[int, int],
) -> PlateBoundaryState:
    relative_x = float(plate_b.vector_x_cm_per_yr - plate_a.vector_x_cm_per_yr)
    relative_y = float(plate_b.vector_y_cm_per_yr - plate_a.vector_y_cm_per_yr)
    relative_motion = math.sqrt((relative_x**2) + (relative_y**2))

    if edge_kind == "east":
        normal_component = relative_x
        tangential_component = relative_y
        edge_orientation = "meridional"
        longitude_west, longitude_east, latitude_south, latitude_north = cell_bounds(
            cell_a.latitude_index, cell_a.longitude_index, resolution
        )
        line_longitude = 180.0 if cell_b.longitude_index == 0 else longitude_east
        line_start_longitude = line_longitude
        line_end_longitude = line_longitude
        line_start_latitude = latitude_south
        line_end_latitude = latitude_north
        midpoint_longitude = line_longitude
        midpoint_latitude = (latitude_south + latitude_north) * 0.5
    else:
        normal_component = relative_y
        tangential_component = relative_x
        edge_orientation = "zonal"
        longitude_west, longitude_east, latitude_south, latitude_north = cell_bounds(
            cell_a.latitude_index, cell_a.longitude_index, resolution
        )
        line_latitude = latitude_north
        line_start_longitude = longitude_west
        line_end_longitude = longitude_east
        line_start_latitude = line_latitude
        line_end_latitude = line_latitude
        midpoint_longitude = wrap_longitude((longitude_west + longitude_east) * 0.5)
        midpoint_latitude = line_latitude

    divergence_score = clamp_unit_float(max(0.0, normal_component) / 8.0)
    convergence_score = clamp_unit_float(max(0.0, -normal_component) / 8.0)
    shear_score = clamp_unit_float(abs(tangential_component) / 8.0)

    average_rigidity = (
        cell_a.lithosphere_rigidity_index + cell_b.lithosphere_rigidity_index
    ) * 0.5
    average_thermal = (cell_a.thermal_stress_index + cell_b.thermal_stress_index) * 0.5
    average_fracture = (
        cell_a.fracture_susceptibility_index + cell_b.fracture_susceptibility_index
    ) * 0.5
    average_rift = (cell_a.proto_rift_tendency_index + cell_b.proto_rift_tendency_index) * 0.5
    average_upwelling = (
        cell_a.upwelling_influence_index + cell_b.upwelling_influence_index
    ) * 0.5
    average_recycling = (
        cell_a.recycling_tendency_index + cell_b.recycling_tendency_index
    ) * 0.5

    spreading_score = clamp_unit_float(
        (
            (0.50 * divergence_score)
            + (0.30 * average_rift)
            + (0.20 * average_upwelling)
        )
        * boundary_family_bias("spreading", plate_a, plate_b)
    )
    convergent_score = clamp_unit_float(
        (
            (0.50 * convergence_score)
            + (0.30 * average_recycling)
            + (0.20 * average_rigidity)
        )
        * boundary_family_bias("convergent", plate_a, plate_b)
    )
    transform_score = clamp_unit_float(
        (
            (0.55 * shear_score)
            + (0.25 * average_fracture)
            + (0.20 * average_thermal)
        )
        * boundary_family_bias("transform", plate_a, plate_b)
    )

    if plate_a.active == "no" and plate_b.active == "no":
        if plate_a.status == "overturn_domain":
            activity_scale = 0.45
        else:
            activity_scale = 0.70
        spreading_score *= activity_scale
        convergent_score *= activity_scale
        transform_score *= activity_scale

    score_map = {
        "spreading": spreading_score,
        "convergent": convergent_score,
        "transform": transform_score,
    }
    boundary_type, interaction_index = max(
        score_map.items(),
        key=lambda item: (item[1], -BOUNDARY_TYPE_ORDER.index(item[0])),
    )
    interaction_threshold = (
        0.30 if plate_a.active == "yes" or plate_b.active == "yes" else 0.42
    )
    if interaction_index < interaction_threshold:
        boundary_type = "indeterminate"

    return PlateBoundaryState(
        boundary_id=f"{cell_a.cell_id}__{cell_b.cell_id}",
        region_a_id=cell_a.cell_id,
        region_b_id=cell_b.cell_id,
        plate_a_id=plate_a.plate_id,
        plate_b_id=plate_b.plate_id,
        boundary_type=boundary_type,
        edge_orientation=edge_orientation,
        midpoint_latitude_degrees=midpoint_latitude,
        midpoint_longitude_degrees=midpoint_longitude,
        line_start_longitude_degrees=line_start_longitude,
        line_start_latitude_degrees=line_start_latitude,
        line_end_longitude_degrees=line_end_longitude,
        line_end_latitude_degrees=line_end_latitude,
        interaction_index=interaction_index,
        relative_motion_cm_per_yr=relative_motion,
        crust_creation_tendency_index=spreading_score,
        crust_destruction_tendency_index=convergent_score,
        transform_tendency_index=transform_score,
    )


def dominant_boundary_type(boundary_types: Iterable[str]) -> str:
    counts = Counter(boundary_types)
    if not counts:
        return "indeterminate"
    return max(
        BOUNDARY_TYPE_ORDER,
        key=lambda boundary_type: (counts.get(boundary_type, 0), -BOUNDARY_TYPE_ORDER.index(boundary_type)),
    )


def local_role_at(
    incident_boundaries: Sequence[PlateBoundaryState], tectonic_active: str
) -> str:
    if not incident_boundaries:
        return "interior"
    boundary_types = [boundary.boundary_type for boundary in incident_boundaries]
    active_boundary_types = [
        boundary_type
        for boundary_type in boundary_types
        if boundary_type in {"spreading", "convergent", "transform"}
    ]
    if not active_boundary_types:
        return "inactive" if tectonic_active == "no" else "ambiguous"
    return f"{dominant_boundary_type(active_boundary_types)}_boundary"


def build_plate_adjacencies(
    boundaries: Sequence[PlateBoundaryState],
) -> tuple[PlateAdjacencyState, ...]:
    grouped_boundaries: defaultdict[tuple[str, str], list[PlateBoundaryState]] = defaultdict(list)
    for boundary in boundaries:
        key = tuple(sorted((boundary.plate_a_id, boundary.plate_b_id)))
        grouped_boundaries[key].append(boundary)

    adjacency_states: list[PlateAdjacencyState] = []
    for plate_a_id, plate_b_id in sorted(grouped_boundaries):
        group = grouped_boundaries[(plate_a_id, plate_b_id)]
        counts = Counter(boundary.boundary_type for boundary in group)
        adjacency_states.append(
            PlateAdjacencyState(
                adjacency_id=f"{plate_a_id}__{plate_b_id}",
                plate_a_id=plate_a_id,
                plate_b_id=plate_b_id,
                dominant_boundary_type=dominant_boundary_type(
                    boundary.boundary_type for boundary in group
                ),
                boundary_count=len(group),
                spreading_count=counts.get("spreading", 0),
                convergent_count=counts.get("convergent", 0),
                transform_count=counts.get("transform", 0),
                indeterminate_count=counts.get("indeterminate", 0),
            )
        )
    return tuple(adjacency_states)


def build_plate_surface_model(
    proto_state: proto_tectonics.ProtoTectonicsState,
    state: PlateSystemState,
    resolution: tuple[int, int],
) -> PlateSurfaceModel:
    proto_cells = proto_tectonics.build_proto_tectonic_surface_cells(proto_state, resolution)
    templates = active_templates_at(state.tectonic_regime)
    plate_region_lookup = {region.region_id: region for region in state.plate_regions}
    seed_lookup = select_plate_seed_cells(proto_cells, templates, state.tectonic_regime)
    assignment_lookup = assign_cells_to_plates(
        proto_cells, templates, seed_lookup, state.tectonic_regime
    )
    proto_cell_lookup = {
        (cell.latitude_index, cell.longitude_index): cell for cell in proto_cells
    }

    boundaries: list[PlateBoundaryState] = []
    lon_cells, lat_cells = resolution
    for latitude_index in range(lat_cells):
        for longitude_index in range(lon_cells):
            cell = proto_cell_lookup[(latitude_index, longitude_index)]

            east_neighbor = proto_cell_lookup[
                (latitude_index, (longitude_index + 1) % lon_cells)
            ]
            template_a = assignment_lookup[cell.cell_id]
            template_b = assignment_lookup[east_neighbor.cell_id]
            plate_a = plate_region_lookup[template_a.region_id]
            plate_b = plate_region_lookup[template_b.region_id]
            if plate_a.plate_id != plate_b.plate_id:
                boundaries.append(
                    boundary_state_at(
                        cell,
                        east_neighbor,
                        plate_a,
                        plate_b,
                        edge_kind="east",
                        resolution=resolution,
                    )
                )

            if latitude_index < lat_cells - 1:
                north_neighbor = proto_cell_lookup[(latitude_index + 1, longitude_index)]
                template_b = assignment_lookup[north_neighbor.cell_id]
                plate_b = plate_region_lookup[template_b.region_id]
                if plate_a.plate_id != plate_b.plate_id:
                    boundaries.append(
                        boundary_state_at(
                            cell,
                            north_neighbor,
                            plate_a,
                            plate_b,
                            edge_kind="north",
                            resolution=resolution,
                        )
                    )

    incident_boundaries: defaultdict[str, list[PlateBoundaryState]] = defaultdict(list)
    for boundary in boundaries:
        incident_boundaries[boundary.region_a_id].append(boundary)
        incident_boundaries[boundary.region_b_id].append(boundary)

    region_states: list[PlateSurfaceRegionState] = []
    regions_by_plate: defaultdict[str, list[str]] = defaultdict(list)
    plate_neighbor_ids: defaultdict[str, set[str]] = defaultdict(set)
    for boundary in boundaries:
        plate_neighbor_ids[boundary.plate_a_id].add(boundary.plate_b_id)
        plate_neighbor_ids[boundary.plate_b_id].add(boundary.plate_a_id)

    for cell in sorted(proto_cells, key=lambda item: (item.latitude_index, item.longitude_index)):
        template = assignment_lookup[cell.cell_id]
        plate_region = plate_region_lookup[template.region_id]
        longitude_west, longitude_east, latitude_south, latitude_north = cell_bounds(
            cell.latitude_index, cell.longitude_index, resolution
        )
        region_incident_boundaries = incident_boundaries.get(cell.cell_id, [])
        if region_incident_boundaries:
            crust_creation_tendency = sum(
                boundary.crust_creation_tendency_index
                for boundary in region_incident_boundaries
            ) / len(region_incident_boundaries)
            crust_destruction_tendency = sum(
                boundary.crust_destruction_tendency_index
                for boundary in region_incident_boundaries
            ) / len(region_incident_boundaries)
        else:
            crust_creation_tendency = 0.0
            crust_destruction_tendency = 0.0

        region_states.append(
            PlateSurfaceRegionState(
                region_id=cell.cell_id,
                cell_id=cell.cell_id,
                latitude_index=cell.latitude_index,
                longitude_index=cell.longitude_index,
                center_latitude_degrees=cell.latitude_degrees,
                center_longitude_degrees=cell.longitude_degrees,
                latitude_south_degrees=latitude_south,
                latitude_north_degrees=latitude_north,
                longitude_west_degrees=longitude_west,
                longitude_east_degrees=longitude_east,
                neighbor_region_ids=neighbor_region_ids_at(
                    cell.latitude_index, cell.longitude_index, resolution
                ),
                tectonic_active=plate_region.active,
                plate_id=plate_region.plate_id,
                plate_region_id=plate_region.region_id,
                local_role=local_role_at(
                    region_incident_boundaries, plate_region.active
                ),
                motion_direction=plate_region.motion_direction,
                speed_cm_per_yr=float(plate_region.speed_cm_per_yr),
                vector_x_cm_per_yr=float(plate_region.vector_x_cm_per_yr),
                vector_y_cm_per_yr=float(plate_region.vector_y_cm_per_yr),
                lithosphere_rigidity_index=cell.lithosphere_rigidity_index,
                thermal_stress_index=cell.thermal_stress_index,
                fracture_susceptibility_index=cell.fracture_susceptibility_index,
                proto_rift_tendency_index=cell.proto_rift_tendency_index,
                upwelling_influence_index=cell.upwelling_influence_index,
                recycling_tendency_index=cell.recycling_tendency_index,
                crust_creation_tendency_index=crust_creation_tendency,
                crust_destruction_tendency_index=crust_destruction_tendency,
            )
        )
        regions_by_plate[plate_region.plate_id].append(cell.cell_id)

    plate_creation_score_totals: defaultdict[str, float] = defaultdict(float)
    plate_destruction_score_totals: defaultdict[str, float] = defaultdict(float)
    total_creation_score = 0.0
    total_destruction_score = 0.0
    for boundary in boundaries:
        total_creation_score += boundary.crust_creation_tendency_index
        total_destruction_score += boundary.crust_destruction_tendency_index
        plate_creation_score_totals[boundary.plate_a_id] += boundary.crust_creation_tendency_index
        plate_creation_score_totals[boundary.plate_b_id] += boundary.crust_creation_tendency_index
        plate_destruction_score_totals[boundary.plate_a_id] += boundary.crust_destruction_tendency_index
        plate_destruction_score_totals[boundary.plate_b_id] += boundary.crust_destruction_tendency_index

    region_lookup = {region.region_id: region for region in region_states}
    plate_states: list[PlateSurfacePlateState] = []
    template_order_lookup = {
        region.plate_id: index for index, region in enumerate(state.plate_regions)
    }
    for region_summary in state.plate_regions:
        member_region_ids = tuple(sorted(regions_by_plate[region_summary.plate_id]))
        member_regions = [region_lookup[region_id] for region_id in member_region_ids]
        centroid_latitude = sum(
            region.center_latitude_degrees for region in member_regions
        ) / len(member_regions)
        centroid_longitude = circular_mean_longitude(
            [region.center_longitude_degrees for region in member_regions]
        )
        creation_rate = (
            float(state.crust_creation_rate_km2_per_yr)
            * (plate_creation_score_totals[region_summary.plate_id] / total_creation_score)
            if total_creation_score > 0.0
            else 0.0
        )
        destruction_rate = (
            float(state.crust_destruction_rate_km2_per_yr)
            * (
                plate_destruction_score_totals[region_summary.plate_id]
                / total_destruction_score
            )
            if total_destruction_score > 0.0
            else 0.0
        )
        fill_color = PLATE_FILL_PALETTE[
            template_order_lookup[region_summary.plate_id] % len(PLATE_FILL_PALETTE)
        ]
        plate_states.append(
            PlateSurfacePlateState(
                plate_id=region_summary.plate_id,
                plate_region_id=region_summary.region_id,
                status=region_summary.status,
                active=region_summary.active,
                member_region_ids=member_region_ids,
                neighbor_plate_ids=tuple(
                    sorted(plate_neighbor_ids.get(region_summary.plate_id, set()))
                ),
                centroid_latitude_degrees=centroid_latitude,
                centroid_longitude_degrees=centroid_longitude,
                motion_direction=region_summary.motion_direction,
                speed_cm_per_yr=float(region_summary.speed_cm_per_yr),
                vector_x_cm_per_yr=float(region_summary.vector_x_cm_per_yr),
                vector_y_cm_per_yr=float(region_summary.vector_y_cm_per_yr),
                region_count=len(member_region_ids),
                crust_creation_rate_km2_per_yr=creation_rate,
                crust_destruction_rate_km2_per_yr=destruction_rate,
                fill_color=fill_color,
            )
        )

    boundary_counts = Counter(boundary.boundary_type for boundary in boundaries)
    plate_adjacencies = build_plate_adjacencies(boundaries)

    return PlateSurfaceModel(
        model=SURFACE_GEOMETRY_MODEL,
        geometry=SURFACE_GEOMETRY_KIND,
        source_surface_grid_model=proto_tectonics.SURFACE_GRID_MODEL,
        surface_grid_resolution=surface_grid_resolution_label(resolution),
        longitude_cells=lon_cells,
        latitude_cells=lat_cells,
        region_count=len(region_states),
        plate_count=len(plate_states),
        boundary_count=len(boundaries),
        plate_adjacency_count=len(plate_adjacencies),
        present_day_regime=state.tectonic_regime,
        source_major_fracture_zones=proto_state.major_fracture_zones,
        source_spreading_zones=proto_state.spreading_zones,
        source_recycling_zones=proto_state.recycling_zones,
        active_plate_ids=tuple(
            plate.plate_id for plate in plate_states if plate.active == "yes"
        ),
        boundary_type_counts={
            boundary_type: boundary_counts.get(boundary_type, 0)
            for boundary_type in BOUNDARY_TYPE_ORDER
        },
        region_fields=(
            "plate_id",
            "motion_direction",
            "speed_cm_per_yr",
            "vector_x_cm_per_yr",
            "vector_y_cm_per_yr",
            "lithosphere_rigidity_index",
            "thermal_stress_index",
            "fracture_susceptibility_index",
            "proto_rift_tendency_index",
            "upwelling_influence_index",
            "recycling_tendency_index",
            "crust_creation_tendency_index",
            "crust_destruction_tendency_index",
            "local_role",
        ),
        boundary_types=BOUNDARY_TYPE_ORDER,
        regions=tuple(region_states),
        plates=tuple(plate_states),
        boundaries=tuple(boundaries),
        plate_adjacencies=plate_adjacencies,
    )


def build_surface_geometry_extra(
    proto_states: Sequence[proto_tectonics.ProtoTectonicsState],
    states: Sequence[PlateSystemState],
    resolution: tuple[int, int],
) -> dict[str, object]:
    if not proto_states or not states:
        lon_cells, lat_cells = resolution
        empty_mesh = {
            "model": SURFACE_GEOMETRY_MODEL,
            "geometry": SURFACE_GEOMETRY_KIND,
            "mesh_level": "tectonic_mesh",
            "surface_grid_resolution": surface_grid_resolution_label(resolution),
            "longitude_cells": lon_cells,
            "latitude_cells": lat_cells,
            "region_count": 0,
            "regions": [],
            "boundaries": [],
        }
        return {
            "tectonic_mesh": empty_mesh,
            "plates": [],
            "boundaries": [],
            "plate_adjacencies": [],
            "surface_geometry": empty_mesh,
        }

    present_state = states[-1]
    surface_model = build_plate_surface_model(proto_states[-1], present_state, resolution)
    surface = planet_surface_from_plate_surface_model(
        surface_model,
        step_index=present_state.step_index,
        age_years=present_state.age_years,
        radius_km=float(present_state.radius_km),
    )
    state_path = surface_state_output_path(
        __file__, surface_model.longitude_cells, surface_model.latitude_cells
    )
    tectonic_mesh = surface_json_payload(surface, state_path=state_path)
    return {
        "tectonic_mesh": tectonic_mesh,
        "plates": surface_model.plates,
        "boundaries": surface_model.boundaries,
        "plate_adjacencies": surface_model.plate_adjacencies,
        "surface_geometry": tectonic_mesh,
    }


def write_surface_state_artifact(
    proto_states: Sequence[proto_tectonics.ProtoTectonicsState],
    states: Sequence[PlateSystemState],
    resolution: tuple[int, int],
    current_file: str,
) -> Path | None:
    if not proto_states or not states:
        return None

    present_state = states[-1]
    surface_model = build_plate_surface_model(proto_states[-1], present_state, resolution)
    surface = planet_surface_from_plate_surface_model(
        surface_model,
        step_index=present_state.step_index,
        age_years=present_state.age_years,
        radius_km=float(present_state.radius_km),
    )
    output_path = surface_state_output_path(
        current_file,
        surface_model.longitude_cells,
        surface_model.latitude_cells,
    )
    return save_planet_surface(surface, output_path)


def plate_index_grid(
    surface_model: PlateSurfaceModel, resolution: tuple[int, int]
) -> tuple[list[list[int]], list[PlateSurfacePlateState]]:
    lon_cells, lat_cells = resolution
    ordered_plates = list(surface_model.plates)
    plate_index_lookup = {
        plate.plate_id: index for index, plate in enumerate(ordered_plates)
    }
    grid = [[0 for _ in range(lon_cells)] for _ in range(lat_cells)]
    for region in surface_model.regions:
        grid[region.latitude_index][region.longitude_index] = plate_index_lookup[
            region.plate_id
        ]
    return grid, ordered_plates


def local_role_grid(
    surface_model: PlateSurfaceModel, resolution: tuple[int, int]
) -> tuple[list[list[int]], list[str]]:
    lon_cells, lat_cells = resolution
    ordered_roles = list(LOCAL_ROLE_COLORS)
    role_index_lookup = {
        role_name: index for index, role_name in enumerate(ordered_roles)
    }
    grid = [[0 for _ in range(lon_cells)] for _ in range(lat_cells)]
    for region in surface_model.regions:
        grid[region.latitude_index][region.longitude_index] = role_index_lookup[
            region.local_role
        ]
    return grid, ordered_roles


def write_present_day_plate_map_png(
    surface_model: PlateSurfaceModel,
    current_file: str,
    resolution: tuple[int, int],
) -> Path:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.colors import ListedColormap
        from matplotlib.lines import Line2D
        from matplotlib.patches import Patch
    except ImportError as exc:  # pragma: no cover - import-time dependency guard
        raise ImportError(
            "Plate map visualization requires matplotlib. Install dependencies "
            "with `python3 -m pip install -r requirements.txt`."
        ) from exc

    grid, ordered_plates = plate_index_grid(surface_model, resolution)
    figure, axis = plt.subplots(figsize=(16.8, 9.2), facecolor="#f6f1e8")
    axis.set_facecolor("#fffdf8")
    colormap = ListedColormap([plate.fill_color for plate in ordered_plates])
    image = axis.imshow(
        grid,
        origin="lower",
        extent=(-180, 180, -90, 90),
        aspect="auto",
        cmap=colormap,
        vmin=-0.5,
        vmax=max(0.5, len(ordered_plates) - 0.5),
        interpolation="nearest",
    )
    del image

    for boundary in surface_model.boundaries:
        axis.plot(
            [
                boundary.line_start_longitude_degrees,
                boundary.line_end_longitude_degrees,
            ],
            [
                boundary.line_start_latitude_degrees,
                boundary.line_end_latitude_degrees,
            ],
            color=BOUNDARY_COLORS[boundary.boundary_type],
            linewidth=2.2,
            solid_capstyle="round",
            zorder=3,
        )

    max_speed = max((plate.speed_cm_per_yr for plate in ordered_plates), default=1.0)
    arrow_scale = 12.0 / max(1.0, max_speed)
    for plate in ordered_plates:
        start_longitude = plate.centroid_longitude_degrees
        start_latitude = plate.centroid_latitude_degrees
        end_longitude = max(
            -178.0,
            min(178.0, start_longitude + (plate.vector_x_cm_per_yr * arrow_scale)),
        )
        end_latitude = max(
            -86.0,
            min(86.0, start_latitude + (plate.vector_y_cm_per_yr * arrow_scale)),
        )
        axis.annotate(
            "",
            xy=(end_longitude, end_latitude),
            xytext=(start_longitude, start_latitude),
            arrowprops={
                "arrowstyle": "-|>",
                "color": "#111827",
                "lw": 1.8,
                "shrinkA": 0.0,
                "shrinkB": 0.0,
            },
            zorder=4,
        )
        axis.text(
            start_longitude,
            start_latitude,
            template_short_label(plate.plate_id),
            fontsize=8.6,
            ha="center",
            va="center",
            color="#111827",
            bbox={
                "boxstyle": "round,pad=0.18",
                "fc": "#fffdf8",
                "ec": "#1f2937",
                "lw": 0.7,
                "alpha": 0.88,
            },
            zorder=5,
        )

    axis.set_title(
        "07 Plate System: Present-Day Deterministic Plate Geometry",
        fontsize=18,
        color="#1f2937",
        loc="left",
        pad=14,
    )
    axis.text(
        0.0,
        1.01,
        (
            f"Equirectangular projection, {surface_model.surface_grid_resolution} "
            f"surface regions, regime {surface_model.present_day_regime.replace('_', ' ')}."
        ),
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
    axis.grid(color="#d7d2c8", linewidth=0.5, alpha=0.22)
    for spine in axis.spines.values():
        spine.set_color("#d7d2c8")

    plate_handles = [
        Patch(
            facecolor=plate.fill_color,
            edgecolor="#1f2937",
            label=f"{template_short_label(plate.plate_id)} {plate.plate_id}",
        )
        for plate in ordered_plates
    ]
    boundary_handles = [
        Line2D(
            [0],
            [0],
            color=BOUNDARY_COLORS[boundary_type],
            lw=2.4,
            label=f"{boundary_type.title()} boundary",
        )
        for boundary_type in BOUNDARY_TYPE_ORDER
    ]
    arrow_handle = Line2D(
        [0],
        [0],
        color="#111827",
        lw=1.8,
        marker=">",
        markersize=7,
        label="Plate motion arrow",
    )

    plate_legend = axis.legend(
        handles=plate_handles,
        title="Plates",
        loc="center left",
        bbox_to_anchor=(1.01, 0.60),
        frameon=True,
    )
    plate_legend.get_frame().set_facecolor("#fffdf8")
    plate_legend.get_frame().set_edgecolor("#d7d2c8")
    axis.add_artist(plate_legend)

    boundary_legend = axis.legend(
        handles=boundary_handles + [arrow_handle],
        title="Boundary / Motion",
        loc="center left",
        bbox_to_anchor=(1.01, 0.19),
        frameon=True,
    )
    boundary_legend.get_frame().set_facecolor("#fffdf8")
    boundary_legend.get_frame().set_edgecolor("#d7d2c8")

    figure.text(
        0.065,
        0.02,
        (
            "Plate fills are deterministic cell-group assignments derived from the "
            "proto-tectonic surface grid. Boundary colors and motion arrows come "
            "from the same reusable spatial state written into the layer JSON."
        ),
        ha="left",
        va="bottom",
        fontsize=10,
        color="#6b7280",
    )
    figure.subplots_adjust(left=0.07, right=0.74, top=0.90, bottom=0.12)

    output_path = plate_map_output_path(current_file)
    figure.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return output_path


def write_boundary_debug_png(
    surface_model: PlateSurfaceModel,
    current_file: str,
    resolution: tuple[int, int],
) -> Path:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.colors import ListedColormap
        from matplotlib.lines import Line2D
        from matplotlib.patches import Patch
    except ImportError as exc:  # pragma: no cover - import-time dependency guard
        raise ImportError(
            "Boundary debug visualization requires matplotlib. Install "
            "dependencies with `python3 -m pip install -r requirements.txt`."
        ) from exc

    grid, ordered_roles = local_role_grid(surface_model, resolution)
    figure, axis = plt.subplots(figsize=(16.8, 9.2), facecolor="#f6f1e8")
    axis.set_facecolor("#fffdf8")
    role_colormap = ListedColormap(
        [LOCAL_ROLE_COLORS[role_name] for role_name in ordered_roles]
    )
    image = axis.imshow(
        grid,
        origin="lower",
        extent=(-180, 180, -90, 90),
        aspect="auto",
        cmap=role_colormap,
        vmin=-0.5,
        vmax=max(0.5, len(ordered_roles) - 0.5),
        interpolation="nearest",
    )
    del image

    for boundary in surface_model.boundaries:
        axis.plot(
            [
                boundary.line_start_longitude_degrees,
                boundary.line_end_longitude_degrees,
            ],
            [
                boundary.line_start_latitude_degrees,
                boundary.line_end_latitude_degrees,
            ],
            color=BOUNDARY_COLORS[boundary.boundary_type],
            linewidth=1.8,
            solid_capstyle="round",
            zorder=3,
        )

    axis.set_title(
        "07 Plate System: Present-Day Boundary Debug View",
        fontsize=18,
        color="#1f2937",
        loc="left",
        pad=14,
    )
    axis.text(
        0.0,
        1.01,
        (
            "Cell roles are derived from incident inter-plate edges on the shared "
            "surface grid. Boundary overlays show the classified edge graph."
        ),
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
    axis.grid(color="#d7d2c8", linewidth=0.5, alpha=0.22)
    for spine in axis.spines.values():
        spine.set_color("#d7d2c8")

    role_handles = [
        Patch(
            facecolor=LOCAL_ROLE_COLORS[role_name],
            edgecolor="#1f2937",
            label=role_name.replace("_", " "),
        )
        for role_name in ordered_roles
    ]
    boundary_handles = [
        Line2D(
            [0],
            [0],
            color=BOUNDARY_COLORS[boundary_type],
            lw=2.1,
            label=f"{boundary_type.title()} boundary",
        )
        for boundary_type in BOUNDARY_TYPE_ORDER
    ]

    role_legend = axis.legend(
        handles=role_handles,
        title="Cell Role",
        loc="center left",
        bbox_to_anchor=(1.01, 0.58),
        frameon=True,
    )
    role_legend.get_frame().set_facecolor("#fffdf8")
    role_legend.get_frame().set_edgecolor("#d7d2c8")
    axis.add_artist(role_legend)

    boundary_legend = axis.legend(
        handles=boundary_handles,
        title="Boundary Type",
        loc="center left",
        bbox_to_anchor=(1.01, 0.21),
        frameon=True,
    )
    boundary_legend.get_frame().set_facecolor("#fffdf8")
    boundary_legend.get_frame().set_edgecolor("#d7d2c8")

    figure.subplots_adjust(left=0.07, right=0.74, top=0.90, bottom=0.10)

    output_path = boundary_debug_output_path(current_file)
    figure.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
        facecolor=figure.get_facecolor(),
    )
    plt.close(figure)
    return output_path


def simulate(
    criteria: planet.SimulationCriteria,
    surface_grid_resolution: tuple[int, int] | None = None,
) -> Iterable[PlateSystemState]:
    resolution = surface_grid_resolution or parse_surface_grid_resolution(
        DEFAULT_SURFACE_GRID_RESOLUTION
    )
    proto_states = proto_tectonics.simulate(criteria, resolution)

    def build_states() -> Iterable[PlateSystemState]:
        for base_state in proto_states:
            yield plate_system_state_from_proto_tectonics_state(base_state)

    return materialize_layer_states(
        __file__,
        criteria,
        build_states,
        extra_builder=lambda states: build_surface_geometry_extra(
            proto_states, states, resolution
        ),
        artifact_key=plate_surface_artifact_key(resolution),
        artifact_writer=lambda states: write_surface_state_artifact(
            proto_states, states, resolution, __file__
        ),
    )


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
    resolution = parse_surface_grid_resolution(DEFAULT_SURFACE_GRID_RESOLUTION)
    proto_states = list(proto_tectonics.simulate(reference_criteria, resolution))
    states = list(simulate(reference_criteria, resolution))
    initial_state = states[0]
    present_state = states[-1]
    first_active_state = first_active_plate_state(states)
    present_surface_model = build_plate_surface_model(
        proto_states[-1], present_state, resolution
    )

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
    if present_surface_model.region_count != resolution[0] * resolution[1]:
        raise ValueError("Plate surface model must cover the full coarse grid.")
    if present_surface_model.plate_count != len(present_state.plate_regions):
        raise ValueError("Plate surface model must preserve plate-region count.")
    if present_surface_model.boundary_count <= 0:
        raise ValueError("Present-day plate geometry must contain inter-plate boundaries.")
    if any(not region.neighbor_region_ids for region in present_surface_model.regions):
        raise ValueError("Every surface region must expose neighbor relationships.")


def print_input_criteria(
    criteria: planet.SimulationCriteria, surface_grid_resolution: tuple[int, int]
) -> None:
    lon_cells, lat_cells = surface_grid_resolution
    fields = [
        ("layer_name", "plate_system_simulation"),
        ("proto_tectonics_source", "06_proto_tectonics.py"),
        ("surface_temperature_source", "05_surface_temperature.py"),
        ("early_atmosphere_source", "04_early_atmosphere.py"),
        ("primary_crust_source", "03_primary_crust.py"),
        ("interior_source", "02_interior.py"),
        ("planet_source", "01_planet.py"),
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
        ("surface_geometry_model", SURFACE_GEOMETRY_MODEL),
        ("surface_geometry_kind", SURFACE_GEOMETRY_KIND),
        ("surface_grid_resolution", f"{lon_cells}x{lat_cells}"),
        ("plate_partition_model", "deterministic_seeded_surface_grouping"),
        ("boundary_graph_model", "neighbor_edge_classification"),
        ("motion_model", "regime_scaled_vector_field"),
        ("crust_budget_model", "surface_area_scaled_creation_and_destruction"),
        (
            "dynamic_fields",
            "coherent_region_count, active_plate_count, "
            "mean_plate_speed_cm_per_yr, spreading_rate_cm_per_yr, "
            "collision_rate_cm_per_yr, recycling_rate_cm_per_yr, "
            "transform_rate_cm_per_yr, crust_creation_rate_km2_per_yr, "
            "crust_destruction_rate_km2_per_yr, net_crust_balance_km2_per_yr, "
            "surface regions, plate assignments, boundary graph",
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print("INPUT CRITERIA")
    print("==============")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")
    print()


def print_table(states: Sequence[PlateSystemState]) -> None:
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

    for state in states:
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


def print_present_day_summary(
    states: Sequence[PlateSystemState],
    surface_model: PlateSurfaceModel,
) -> None:
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
        ("surface_geometry_model", surface_model.model),
        ("surface_geometry_kind", surface_model.geometry),
        ("surface_grid_resolution", surface_model.surface_grid_resolution),
        ("surface_region_count", str(surface_model.region_count)),
        ("surface_plate_count", str(surface_model.plate_count)),
        ("boundary_count", str(surface_model.boundary_count)),
        ("plate_adjacency_count", str(surface_model.plate_adjacency_count)),
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
        ("plate_id", 28),
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
            f"{region.plate_id:>28} "
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
        surface_grid_resolution = parse_surface_grid_resolution(
            args.surface_grid_resolution
        )
        validate_model()
    except ValueError as exc:
        raise SystemExit(str(exc))

    proto_states = tuple(proto_tectonics.simulate(criteria, surface_grid_resolution))
    states = tuple(simulate(criteria, surface_grid_resolution))
    if not states:
        raise SystemExit("Plate-system simulation produced no timestep states.")

    surface_model = build_plate_surface_model(
        proto_states[-1], states[-1], surface_grid_resolution
    )

    print_input_criteria(criteria, surface_grid_resolution)
    print_table(states)
    print_present_day_summary(states, surface_model)

    try:
        write_present_day_plate_map_png(
            surface_model, __file__, surface_grid_resolution
        )
        write_boundary_debug_png(surface_model, __file__, surface_grid_resolution)
    except (ImportError, OSError, ValueError) as exc:
        raise SystemExit(
            f"Failed to write plate-system geometry visualization: {exc}"
        ) from exc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
