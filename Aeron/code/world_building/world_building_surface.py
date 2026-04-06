"""Shared tectonic and terrain surface geometry for spatial world-building layers."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

try:
    from .world_building_paths import step_output_dir, step_output_path
except ImportError:
    from world_building_paths import step_output_dir, step_output_path  # type: ignore


SHARED_SURFACE_MODEL = "deterministic_shared_planet_surface"
SHARED_SURFACE_GEOMETRY = "spherical_lat_lon_cell_center_mesh"
MAX_FRAME_COUNT = 18
CHILD_SUBDIVISION_ORDER = ("south_west", "south_east", "north_west", "north_east")
BOUNDARY_PRIORITY_ORDER = ("convergent", "spreading", "transform", "indeterminate")
ACTIVE_BOUNDARY_TYPES = {"convergent", "spreading", "transform"}


@dataclass
class PlanetSurface:
    model: str
    geometry: str
    mesh_level: str
    subdivision_level: int
    step_index: int
    age_years: int
    radius_km: float
    longitude_cells: int
    latitude_cells: int
    vertices: np.ndarray
    faces: np.ndarray
    region_ids: np.ndarray
    parent_cell_id: np.ndarray
    root_tectonic_cell_id: np.ndarray
    child_index_within_parent: np.ndarray
    latitude_index: np.ndarray
    longitude_index: np.ndarray
    latitude_south_degrees: np.ndarray
    latitude_north_degrees: np.ndarray
    longitude_west_degrees: np.ndarray
    longitude_east_degrees: np.ndarray
    center_latitude_degrees: np.ndarray
    center_longitude_degrees: np.ndarray
    neighbor_indices: np.ndarray
    tectonic_active: np.ndarray
    plate_id: np.ndarray
    plate_region_id: np.ndarray
    boundary_role: np.ndarray
    boundary_influence_type: np.ndarray
    boundary_influence_index: np.ndarray
    motion_direction: np.ndarray
    motion_vector_cm_per_yr: np.ndarray
    lithosphere_rigidity: np.ndarray
    thermal_stress: np.ndarray
    fracture_susceptibility: np.ndarray
    proto_rift_likelihood: np.ndarray
    upwelling_tendency: np.ndarray
    recycling_tendency: np.ndarray
    crust_creation_tendency: np.ndarray
    crust_destruction_tendency: np.ndarray
    uplift_tendency: np.ndarray
    basin_tendency: np.ndarray
    terrain_class: np.ndarray
    elevation: np.ndarray
    temperature: np.ndarray
    crust_type: np.ndarray
    resurfacing_fraction: np.ndarray
    surface_age_proxy: np.ndarray
    lava_coverage: np.ndarray
    crater_density: np.ndarray
    regolith_depth: np.ndarray
    weathering_intensity: np.ndarray
    dust_cover: np.ndarray
    exposed_bedrock_fraction: np.ndarray
    water_depth: np.ndarray
    volcanic_hotspot: np.ndarray
    impact_intensity: np.ndarray
    runoff_flux: np.ndarray
    basin_index: np.ndarray
    flow_receiver_index: np.ndarray
    basin_fill: np.ndarray
    glacier_presence: np.ndarray
    inland_sea: np.ndarray
    edge_region_indices: np.ndarray
    edge_boundary_type: np.ndarray
    edge_interaction_index: np.ndarray
    metadata: dict[str, Any]


def surface_grid_resolution_label(longitude_cells: int, latitude_cells: int) -> str:
    return f"{longitude_cells}x{latitude_cells}"


def subdivided_surface_grid_resolution(
    resolution: tuple[int, int], levels: int = 1
) -> tuple[int, int]:
    factor = 2 ** max(0, levels)
    return (resolution[0] * factor, resolution[1] * factor)


def data_output_dir(current_file: str) -> Path:
    return step_output_dir(current_file)


def visualization_output_dir(current_file: str) -> Path:
    return step_output_dir(current_file)


def surface_state_output_path(
    current_file: str, longitude_cells: int, latitude_cells: int
) -> Path:
    resolution = surface_grid_resolution_label(longitude_cells, latitude_cells)
    return step_output_path(current_file, f"surface_state_{resolution}.npz")


def visualization_output_path(current_file: str, suffix: str) -> Path:
    return step_output_path(current_file, suffix, default_extension=".png")


def frame_output_dir(
    current_file: str,
    directory_name: str,
    longitude_cells: int,
    latitude_cells: int,
) -> Path:
    resolution = surface_grid_resolution_label(longitude_cells, latitude_cells)
    output_dir = visualization_output_dir(current_file) / f"{directory_name}_{resolution}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def clear_frame_directory(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for frame_path in output_dir.glob("frame_*.png"):
        frame_path.unlink()
    return output_dir


def lat_lon_to_cartesian(
    latitude_degrees: float, longitude_degrees: float, radius_km: float
) -> tuple[float, float, float]:
    latitude_radians = math.radians(latitude_degrees)
    longitude_radians = math.radians(longitude_degrees)
    cos_latitude = math.cos(latitude_radians)
    return (
        radius_km * cos_latitude * math.cos(longitude_radians),
        radius_km * cos_latitude * math.sin(longitude_radians),
        radius_km * math.sin(latitude_radians),
    )


def grid_vertex_index(latitude_index: int, longitude_index: int, longitude_cells: int) -> int:
    return (latitude_index * longitude_cells) + longitude_index


def build_lat_lon_faces(longitude_cells: int, latitude_cells: int) -> np.ndarray:
    faces: list[tuple[int, int, int]] = []
    for latitude_index in range(latitude_cells - 1):
        next_latitude = latitude_index + 1
        for longitude_index in range(longitude_cells):
            next_longitude = (longitude_index + 1) % longitude_cells
            south_west = grid_vertex_index(
                latitude_index, longitude_index, longitude_cells
            )
            south_east = grid_vertex_index(
                latitude_index, next_longitude, longitude_cells
            )
            north_west = grid_vertex_index(
                next_latitude, longitude_index, longitude_cells
            )
            north_east = grid_vertex_index(
                next_latitude, next_longitude, longitude_cells
            )
            faces.append((south_west, north_west, north_east))
            faces.append((south_west, north_east, south_east))
    return np.asarray(faces, dtype=np.int32)


def stable_neighbor_matrix(longitude_cells: int, latitude_cells: int) -> np.ndarray:
    region_count = longitude_cells * latitude_cells
    neighbors = np.full((region_count, 4), -1, dtype=np.int32)
    for latitude_index in range(latitude_cells):
        for longitude_index in range(longitude_cells):
            region_index = grid_vertex_index(
                latitude_index, longitude_index, longitude_cells
            )
            ordered_neighbors: list[int] = [
                grid_vertex_index(
                    latitude_index, (longitude_index - 1) % longitude_cells, longitude_cells
                ),
                grid_vertex_index(
                    latitude_index, (longitude_index + 1) % longitude_cells, longitude_cells
                ),
            ]
            if latitude_index > 0:
                ordered_neighbors.append(
                    grid_vertex_index(latitude_index - 1, longitude_index, longitude_cells)
                )
            if latitude_index < latitude_cells - 1:
                ordered_neighbors.append(
                    grid_vertex_index(latitude_index + 1, longitude_index, longitude_cells)
                )
            neighbors[region_index, : len(ordered_neighbors)] = ordered_neighbors
    return neighbors


def string_array(values: Iterable[str]) -> np.ndarray:
    materialized = tuple(values)
    max_length = max((len(value) for value in materialized), default=1)
    return np.asarray(materialized, dtype=f"<U{max_length}")


def region_area_weight(surface: PlanetSurface) -> np.ndarray:
    latitude_radians = np.radians(surface.center_latitude_degrees)
    weights = np.cos(latitude_radians)
    return np.clip(weights, 1.0e-6, None)


def deep_copy_surface(surface: PlanetSurface) -> PlanetSurface:
    return PlanetSurface(
        model=surface.model,
        geometry=surface.geometry,
        mesh_level=surface.mesh_level,
        subdivision_level=surface.subdivision_level,
        step_index=surface.step_index,
        age_years=surface.age_years,
        radius_km=surface.radius_km,
        longitude_cells=surface.longitude_cells,
        latitude_cells=surface.latitude_cells,
        vertices=np.array(surface.vertices, copy=True),
        faces=np.array(surface.faces, copy=True),
        region_ids=np.array(surface.region_ids, copy=True),
        parent_cell_id=np.array(surface.parent_cell_id, copy=True),
        root_tectonic_cell_id=np.array(surface.root_tectonic_cell_id, copy=True),
        child_index_within_parent=np.array(surface.child_index_within_parent, copy=True),
        latitude_index=np.array(surface.latitude_index, copy=True),
        longitude_index=np.array(surface.longitude_index, copy=True),
        latitude_south_degrees=np.array(surface.latitude_south_degrees, copy=True),
        latitude_north_degrees=np.array(surface.latitude_north_degrees, copy=True),
        longitude_west_degrees=np.array(surface.longitude_west_degrees, copy=True),
        longitude_east_degrees=np.array(surface.longitude_east_degrees, copy=True),
        center_latitude_degrees=np.array(surface.center_latitude_degrees, copy=True),
        center_longitude_degrees=np.array(surface.center_longitude_degrees, copy=True),
        neighbor_indices=np.array(surface.neighbor_indices, copy=True),
        tectonic_active=np.array(surface.tectonic_active, copy=True),
        plate_id=np.array(surface.plate_id, copy=True),
        plate_region_id=np.array(surface.plate_region_id, copy=True),
        boundary_role=np.array(surface.boundary_role, copy=True),
        boundary_influence_type=np.array(surface.boundary_influence_type, copy=True),
        boundary_influence_index=np.array(surface.boundary_influence_index, copy=True),
        motion_direction=np.array(surface.motion_direction, copy=True),
        motion_vector_cm_per_yr=np.array(surface.motion_vector_cm_per_yr, copy=True),
        lithosphere_rigidity=np.array(surface.lithosphere_rigidity, copy=True),
        thermal_stress=np.array(surface.thermal_stress, copy=True),
        fracture_susceptibility=np.array(surface.fracture_susceptibility, copy=True),
        proto_rift_likelihood=np.array(surface.proto_rift_likelihood, copy=True),
        upwelling_tendency=np.array(surface.upwelling_tendency, copy=True),
        recycling_tendency=np.array(surface.recycling_tendency, copy=True),
        crust_creation_tendency=np.array(surface.crust_creation_tendency, copy=True),
        crust_destruction_tendency=np.array(surface.crust_destruction_tendency, copy=True),
        uplift_tendency=np.array(surface.uplift_tendency, copy=True),
        basin_tendency=np.array(surface.basin_tendency, copy=True),
        terrain_class=np.array(surface.terrain_class, copy=True),
        elevation=np.array(surface.elevation, copy=True),
        temperature=np.array(surface.temperature, copy=True),
        crust_type=np.array(surface.crust_type, copy=True),
        resurfacing_fraction=np.array(surface.resurfacing_fraction, copy=True),
        surface_age_proxy=np.array(surface.surface_age_proxy, copy=True),
        lava_coverage=np.array(surface.lava_coverage, copy=True),
        crater_density=np.array(surface.crater_density, copy=True),
        regolith_depth=np.array(surface.regolith_depth, copy=True),
        weathering_intensity=np.array(surface.weathering_intensity, copy=True),
        dust_cover=np.array(surface.dust_cover, copy=True),
        exposed_bedrock_fraction=np.array(surface.exposed_bedrock_fraction, copy=True),
        water_depth=np.array(surface.water_depth, copy=True),
        volcanic_hotspot=np.array(surface.volcanic_hotspot, copy=True),
        impact_intensity=np.array(surface.impact_intensity, copy=True),
        runoff_flux=np.array(surface.runoff_flux, copy=True),
        basin_index=np.array(surface.basin_index, copy=True),
        flow_receiver_index=np.array(surface.flow_receiver_index, copy=True),
        basin_fill=np.array(surface.basin_fill, copy=True),
        glacier_presence=np.array(surface.glacier_presence, copy=True),
        inland_sea=np.array(surface.inland_sea, copy=True),
        edge_region_indices=np.array(surface.edge_region_indices, copy=True),
        edge_boundary_type=np.array(surface.edge_boundary_type, copy=True),
        edge_interaction_index=np.array(surface.edge_interaction_index, copy=True),
        metadata=json.loads(json.dumps(surface.metadata, sort_keys=True)),
    )


def surface_grid(surface: PlanetSurface, values: np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=float).reshape(
        surface.latitude_cells, surface.longitude_cells
    )


def clamp_unit_interval(values: np.ndarray) -> np.ndarray:
    return np.clip(values, 0.0, 1.0)


def neighbor_mean(values: np.ndarray, neighbor_indices: np.ndarray) -> np.ndarray:
    result = np.array(values, dtype=float, copy=True)
    for index in range(values.shape[0]):
        neighbors = neighbor_indices[index]
        valid_neighbors = neighbors[neighbors >= 0]
        if valid_neighbors.size == 0:
            continue
        result[index] = float(np.mean(values[valid_neighbors]))
    return result


def diffuse_scalar(
    values: np.ndarray, neighbor_indices: np.ndarray, *, iterations: int, alpha: float
) -> np.ndarray:
    current = np.array(values, dtype=float, copy=True)
    for _ in range(max(0, iterations)):
        smoothed = neighbor_mean(current, neighbor_indices)
        current = ((1.0 - alpha) * current) + (alpha * smoothed)
    return current


def normalized(values: np.ndarray) -> np.ndarray:
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    if math.isclose(maximum, minimum):
        return np.zeros_like(values, dtype=float)
    return (np.asarray(values, dtype=float) - minimum) / (maximum - minimum)


def gradient_magnitude(surface: PlanetSurface, values: np.ndarray) -> np.ndarray:
    grid = surface_grid(surface, values)
    north = np.roll(grid, -1, axis=0)
    south = np.roll(grid, 1, axis=0)
    east = np.roll(grid, -1, axis=1)
    west = np.roll(grid, 1, axis=1)
    latitude_scale = np.cos(np.radians(surface.center_latitude_degrees)).reshape(
        surface.latitude_cells, surface.longitude_cells
    )
    latitude_scale = np.clip(latitude_scale, 0.2, None)
    d_latitude = (north - south) * 0.5
    d_longitude = ((east - west) * 0.5) / latitude_scale
    magnitude = np.sqrt((d_latitude**2) + (d_longitude**2))
    return magnitude.reshape(-1)


def downhill_receivers(surface: PlanetSurface, heights: np.ndarray) -> np.ndarray:
    receivers = np.arange(heights.shape[0], dtype=np.int32)
    for index in range(heights.shape[0]):
        candidate = index
        candidate_height = heights[index]
        for neighbor_index in surface.neighbor_indices[index]:
            if neighbor_index < 0:
                continue
            neighbor_height = heights[neighbor_index]
            if neighbor_height < candidate_height:
                candidate = int(neighbor_index)
                candidate_height = float(neighbor_height)
        receivers[index] = candidate
    return receivers


def accumulate_flow(
    surface: PlanetSurface, heights: np.ndarray, source_flux: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    receivers = downhill_receivers(surface, heights)
    order = np.argsort(-np.asarray(heights, dtype=float))
    flow = np.asarray(source_flux, dtype=float).copy()
    for index in order:
        receiver = int(receivers[index])
        if receiver != index:
            flow[receiver] += flow[index]
    return flow, receivers


def frame_sample_indices(state_count: int, max_frames: int = MAX_FRAME_COUNT) -> list[int]:
    if state_count <= 0:
        return []
    if state_count <= max_frames:
        return list(range(state_count))
    sampled = {
        int(round((frame_index * (state_count - 1)) / (max_frames - 1)))
        for frame_index in range(max_frames)
    }
    return sorted(sampled)


def initial_crust_type_for_region(region: Any) -> str:
    continental_score = (
        (0.50 * float(region.lithosphere_rigidity_index))
        + (0.25 * float(region.recycling_tendency_index))
        + (0.15 * float(region.crust_destruction_tendency_index))
        - (0.10 * float(region.proto_rift_tendency_index))
    )
    oceanic_score = (
        (0.45 * float(region.upwelling_influence_index))
        + (0.30 * float(region.crust_creation_tendency_index))
        + (0.25 * float(region.proto_rift_tendency_index))
    )
    if continental_score >= 0.58 and continental_score >= oceanic_score + 0.05:
        return "proto_continental"
    if oceanic_score >= 0.52:
        return "juvenile_oceanic"
    return "hybrid_primordial"


def side_from_indices(
    latitude_index: int,
    longitude_index: int,
    neighbor_latitude_index: int,
    neighbor_longitude_index: int,
    longitude_cells: int,
) -> str:
    if neighbor_latitude_index == latitude_index + 1 and neighbor_longitude_index == longitude_index:
        return "north"
    if neighbor_latitude_index == latitude_index - 1 and neighbor_longitude_index == longitude_index:
        return "south"
    if neighbor_latitude_index == latitude_index:
        if neighbor_longitude_index == (longitude_index + 1) % longitude_cells:
            return "east"
        if neighbor_longitude_index == (longitude_index - 1) % longitude_cells:
            return "west"
    raise ValueError(
        "Neighbor relationship does not map to a cardinal side for the deterministic grid."
    )


def opposite_side(side: str) -> str:
    return {
        "north": "south",
        "south": "north",
        "east": "west",
        "west": "east",
    }[side]


def preferred_boundary_type(
    candidates: Iterable[tuple[str, float]],
) -> tuple[str, float]:
    materialized = list(candidates)
    if not materialized:
        return ("none", 0.0)
    return max(
        materialized,
        key=lambda item: (
            float(item[1]),
            -BOUNDARY_PRIORITY_ORDER.index(item[0])
            if item[0] in BOUNDARY_PRIORITY_ORDER
            else -len(BOUNDARY_PRIORITY_ORDER),
        ),
    )


def boundary_side_lookup(
    surface: PlanetSurface,
) -> dict[tuple[int, str], tuple[str, float]]:
    lookup: dict[tuple[int, str], tuple[str, float]] = {}
    for edge_index in range(surface.edge_region_indices.shape[0]):
        region_a_index = int(surface.edge_region_indices[edge_index, 0])
        region_b_index = int(surface.edge_region_indices[edge_index, 1])
        boundary_type = str(surface.edge_boundary_type[edge_index])
        interaction_index = float(surface.edge_interaction_index[edge_index])
        side_a = side_from_indices(
            int(surface.latitude_index[region_a_index]),
            int(surface.longitude_index[region_a_index]),
            int(surface.latitude_index[region_b_index]),
            int(surface.longitude_index[region_b_index]),
            surface.longitude_cells,
        )
        side_b = opposite_side(side_a)
        lookup[(region_a_index, side_a)] = preferred_boundary_type(
            [lookup.get((region_a_index, side_a), ("none", 0.0)), (boundary_type, interaction_index)]
        )
        lookup[(region_b_index, side_b)] = preferred_boundary_type(
            [lookup.get((region_b_index, side_b), ("none", 0.0)), (boundary_type, interaction_index)]
        )
    return lookup


def boundary_influence_arrays(
    surface: PlanetSurface,
) -> tuple[np.ndarray, np.ndarray]:
    influence_lookup = boundary_side_lookup(surface)
    influence_types: list[str] = []
    influence_indices: list[float] = []
    for region_index in range(surface.region_ids.shape[0]):
        candidates = [
            influence_lookup[(region_index, side)]
            for side in ("north", "east", "south", "west")
            if (region_index, side) in influence_lookup
        ]
        boundary_type, interaction_index = preferred_boundary_type(candidates)
        influence_types.append(boundary_type)
        influence_indices.append(interaction_index)
    return string_array(influence_types), np.asarray(influence_indices, dtype=float)


def boundary_role_for_influence(
    tectonic_active: str, boundary_type: str
) -> str:
    if boundary_type in ACTIVE_BOUNDARY_TYPES:
        return f"{boundary_type}_boundary"
    if boundary_type == "indeterminate":
        return "inactive" if tectonic_active == "no" else "ambiguous"
    return "inactive" if tectonic_active == "no" else "interior"


def uplift_tendency_from_fields(
    boundary_influence_type: np.ndarray,
    boundary_influence_index: np.ndarray,
    recycling_tendency: np.ndarray,
    crust_destruction_tendency: np.ndarray,
    lithosphere_rigidity: np.ndarray,
) -> np.ndarray:
    return clamp_unit_interval(
        (0.45 * np.where(boundary_influence_type == "convergent", boundary_influence_index, 0.0))
        + (0.25 * recycling_tendency)
        + (0.20 * crust_destruction_tendency)
        + (0.10 * lithosphere_rigidity)
    )


def basin_tendency_from_fields(
    boundary_influence_type: np.ndarray,
    boundary_influence_index: np.ndarray,
    proto_rift_likelihood: np.ndarray,
    upwelling_tendency: np.ndarray,
    crust_creation_tendency: np.ndarray,
) -> np.ndarray:
    return clamp_unit_interval(
        (0.40 * np.where(boundary_influence_type == "spreading", boundary_influence_index, 0.0))
        + (0.30 * proto_rift_likelihood)
        + (0.20 * upwelling_tendency)
        + (0.10 * crust_creation_tendency)
    )


def terrain_class_from_fields(
    elevation: np.ndarray,
    boundary_influence_type: np.ndarray,
    basin_tendency: np.ndarray,
    uplift_tendency: np.ndarray,
) -> np.ndarray:
    classes: list[str] = []
    for index in range(elevation.shape[0]):
        boundary_type = str(boundary_influence_type[index])
        if boundary_type == "convergent":
            classes.append("orogenic_uplift")
        elif boundary_type == "spreading":
            classes.append("rift_basin")
        elif boundary_type == "transform":
            classes.append("shear_margin")
        elif float(elevation[index]) >= 500.0 or float(uplift_tendency[index]) >= 0.55:
            classes.append("highlands")
        elif float(elevation[index]) <= -500.0 or float(basin_tendency[index]) >= 0.55:
            classes.append("basin_lowlands")
        else:
            classes.append("plate_interior")
    return string_array(classes)


def region_resolution_metadata(surface: PlanetSurface) -> dict[str, Any]:
    return {
        "mesh_level": surface.mesh_level,
        "subdivision_level": surface.subdivision_level,
        "surface_grid_resolution": surface_grid_resolution_label(
            surface.longitude_cells, surface.latitude_cells
        ),
    }


def planet_surface_from_plate_surface_model(
    surface_model: Any, *, step_index: int, age_years: int, radius_km: float
) -> PlanetSurface:
    ordered_regions = sorted(
        surface_model.regions, key=lambda region: (region.latitude_index, region.longitude_index)
    )
    region_ids = [region.region_id for region in ordered_regions]
    region_index_lookup = {
        region_id: index for index, region_id in enumerate(region_ids)
    }
    neighbor_indices = stable_neighbor_matrix(
        int(surface_model.longitude_cells), int(surface_model.latitude_cells)
    )

    vertices = np.asarray(
        [
            lat_lon_to_cartesian(
                float(region.center_latitude_degrees),
                float(region.center_longitude_degrees),
                radius_km,
            )
            for region in ordered_regions
        ],
        dtype=float,
    )
    faces = build_lat_lon_faces(
        int(surface_model.longitude_cells), int(surface_model.latitude_cells)
    )
    edge_region_indices = np.asarray(
        [
            (
                region_index_lookup[boundary.region_a_id],
                region_index_lookup[boundary.region_b_id],
            )
            for boundary in surface_model.boundaries
        ],
        dtype=np.int32,
    ).reshape(-1, 2)
    edge_boundary_type = string_array(
        boundary.boundary_type for boundary in surface_model.boundaries
    )
    edge_interaction_index = np.asarray(
        [float(boundary.interaction_index) for boundary in surface_model.boundaries],
        dtype=float,
    )
    tectonic_active = string_array(region.tectonic_active for region in ordered_regions)
    plate_id = string_array(region.plate_id for region in ordered_regions)
    plate_region_id = string_array(region.plate_region_id for region in ordered_regions)
    boundary_role = string_array(region.local_role for region in ordered_regions)
    motion_direction = string_array(region.motion_direction for region in ordered_regions)
    lithosphere_rigidity = np.asarray(
        [float(region.lithosphere_rigidity_index) for region in ordered_regions],
        dtype=float,
    )
    thermal_stress = np.asarray(
        [float(region.thermal_stress_index) for region in ordered_regions],
        dtype=float,
    )
    fracture_susceptibility = np.asarray(
        [float(region.fracture_susceptibility_index) for region in ordered_regions],
        dtype=float,
    )
    proto_rift_likelihood = np.asarray(
        [float(region.proto_rift_tendency_index) for region in ordered_regions],
        dtype=float,
    )
    upwelling_tendency = np.asarray(
        [float(region.upwelling_influence_index) for region in ordered_regions],
        dtype=float,
    )
    recycling_tendency = np.asarray(
        [float(region.recycling_tendency_index) for region in ordered_regions],
        dtype=float,
    )
    crust_creation_tendency = np.asarray(
        [float(region.crust_creation_tendency_index) for region in ordered_regions],
        dtype=float,
    )
    crust_destruction_tendency = np.asarray(
        [float(region.crust_destruction_tendency_index) for region in ordered_regions],
        dtype=float,
    )
    boundary_influence_type, boundary_influence_index = boundary_influence_arrays(
        PlanetSurface(
            model=SHARED_SURFACE_MODEL,
            geometry=SHARED_SURFACE_GEOMETRY,
            mesh_level="tectonic_mesh",
            subdivision_level=0,
            step_index=step_index,
            age_years=age_years,
            radius_km=radius_km,
            longitude_cells=int(surface_model.longitude_cells),
            latitude_cells=int(surface_model.latitude_cells),
            vertices=vertices,
            faces=faces,
            region_ids=string_array(region_ids),
            parent_cell_id=string_array(region_ids),
            root_tectonic_cell_id=string_array(region_ids),
            child_index_within_parent=np.full(len(ordered_regions), -1, dtype=np.int32),
            latitude_index=np.asarray(
                [region.latitude_index for region in ordered_regions], dtype=np.int32
            ),
            longitude_index=np.asarray(
                [region.longitude_index for region in ordered_regions], dtype=np.int32
            ),
            latitude_south_degrees=np.asarray(
                [float(region.latitude_south_degrees) for region in ordered_regions],
                dtype=float,
            ),
            latitude_north_degrees=np.asarray(
                [float(region.latitude_north_degrees) for region in ordered_regions],
                dtype=float,
            ),
            longitude_west_degrees=np.asarray(
                [float(region.longitude_west_degrees) for region in ordered_regions],
                dtype=float,
            ),
            longitude_east_degrees=np.asarray(
                [float(region.longitude_east_degrees) for region in ordered_regions],
                dtype=float,
            ),
            center_latitude_degrees=np.asarray(
                [float(region.center_latitude_degrees) for region in ordered_regions],
                dtype=float,
            ),
            center_longitude_degrees=np.asarray(
                [float(region.center_longitude_degrees) for region in ordered_regions],
                dtype=float,
            ),
            neighbor_indices=neighbor_indices,
            tectonic_active=tectonic_active,
            plate_id=plate_id,
            plate_region_id=plate_region_id,
            boundary_role=boundary_role,
            boundary_influence_type=string_array("none" for _ in ordered_regions),
            boundary_influence_index=np.zeros(len(ordered_regions), dtype=float),
            motion_direction=motion_direction,
            motion_vector_cm_per_yr=np.asarray(
                [
                    [float(region.vector_x_cm_per_yr), float(region.vector_y_cm_per_yr)]
                    for region in ordered_regions
                ],
                dtype=float,
            ),
            lithosphere_rigidity=lithosphere_rigidity,
            thermal_stress=thermal_stress,
            fracture_susceptibility=fracture_susceptibility,
            proto_rift_likelihood=proto_rift_likelihood,
            upwelling_tendency=upwelling_tendency,
            recycling_tendency=recycling_tendency,
            crust_creation_tendency=crust_creation_tendency,
            crust_destruction_tendency=crust_destruction_tendency,
            uplift_tendency=np.zeros(len(ordered_regions), dtype=float),
            basin_tendency=np.zeros(len(ordered_regions), dtype=float),
            terrain_class=string_array("plate_interior" for _ in ordered_regions),
            elevation=np.zeros(len(ordered_regions), dtype=float),
            temperature=np.zeros(len(ordered_regions), dtype=float),
            crust_type=string_array(
                initial_crust_type_for_region(region) for region in ordered_regions
            ),
            resurfacing_fraction=np.zeros(len(ordered_regions), dtype=float),
            surface_age_proxy=np.ones(len(ordered_regions), dtype=float),
            lava_coverage=np.zeros(len(ordered_regions), dtype=float),
            crater_density=np.zeros(len(ordered_regions), dtype=float),
            regolith_depth=np.zeros(len(ordered_regions), dtype=float),
            weathering_intensity=np.zeros(len(ordered_regions), dtype=float),
            dust_cover=np.zeros(len(ordered_regions), dtype=float),
            exposed_bedrock_fraction=np.ones(len(ordered_regions), dtype=float),
            water_depth=np.zeros(len(ordered_regions), dtype=float),
            volcanic_hotspot=np.zeros(len(ordered_regions), dtype=float),
            impact_intensity=np.zeros(len(ordered_regions), dtype=float),
            runoff_flux=np.zeros(len(ordered_regions), dtype=float),
            basin_index=np.zeros(len(ordered_regions), dtype=float),
            flow_receiver_index=np.arange(len(ordered_regions), dtype=np.int32),
            basin_fill=np.zeros(len(ordered_regions), dtype=float),
            glacier_presence=np.zeros(len(ordered_regions), dtype=float),
            inland_sea=np.zeros(len(ordered_regions), dtype=float),
            edge_region_indices=edge_region_indices,
            edge_boundary_type=edge_boundary_type,
            edge_interaction_index=edge_interaction_index,
            metadata={},
        )
    )
    uplift_tendency = uplift_tendency_from_fields(
        boundary_influence_type,
        boundary_influence_index,
        recycling_tendency,
        crust_destruction_tendency,
        lithosphere_rigidity,
    )
    basin_tendency = basin_tendency_from_fields(
        boundary_influence_type,
        boundary_influence_index,
        proto_rift_likelihood,
        upwelling_tendency,
        crust_creation_tendency,
    )

    return PlanetSurface(
        model=SHARED_SURFACE_MODEL,
        geometry=SHARED_SURFACE_GEOMETRY,
        mesh_level="tectonic_mesh",
        subdivision_level=0,
        step_index=step_index,
        age_years=age_years,
        radius_km=radius_km,
        longitude_cells=int(surface_model.longitude_cells),
        latitude_cells=int(surface_model.latitude_cells),
        vertices=vertices,
        faces=faces,
        region_ids=string_array(region_ids),
        parent_cell_id=string_array(region_ids),
        root_tectonic_cell_id=string_array(region_ids),
        child_index_within_parent=np.full(len(ordered_regions), -1, dtype=np.int32),
        latitude_index=np.asarray(
            [region.latitude_index for region in ordered_regions], dtype=np.int32
        ),
        longitude_index=np.asarray(
            [region.longitude_index for region in ordered_regions], dtype=np.int32
        ),
        latitude_south_degrees=np.asarray(
            [float(region.latitude_south_degrees) for region in ordered_regions],
            dtype=float,
        ),
        latitude_north_degrees=np.asarray(
            [float(region.latitude_north_degrees) for region in ordered_regions],
            dtype=float,
        ),
        longitude_west_degrees=np.asarray(
            [float(region.longitude_west_degrees) for region in ordered_regions],
            dtype=float,
        ),
        longitude_east_degrees=np.asarray(
            [float(region.longitude_east_degrees) for region in ordered_regions],
            dtype=float,
        ),
        center_latitude_degrees=np.asarray(
            [float(region.center_latitude_degrees) for region in ordered_regions],
            dtype=float,
        ),
        center_longitude_degrees=np.asarray(
            [float(region.center_longitude_degrees) for region in ordered_regions],
            dtype=float,
        ),
        neighbor_indices=neighbor_indices,
        tectonic_active=tectonic_active,
        plate_id=plate_id,
        plate_region_id=plate_region_id,
        boundary_role=boundary_role,
        boundary_influence_type=boundary_influence_type,
        boundary_influence_index=boundary_influence_index,
        motion_direction=motion_direction,
        motion_vector_cm_per_yr=np.asarray(
            [
                [float(region.vector_x_cm_per_yr), float(region.vector_y_cm_per_yr)]
                for region in ordered_regions
            ],
            dtype=float,
        ),
        lithosphere_rigidity=lithosphere_rigidity,
        thermal_stress=thermal_stress,
        fracture_susceptibility=fracture_susceptibility,
        proto_rift_likelihood=proto_rift_likelihood,
        upwelling_tendency=upwelling_tendency,
        recycling_tendency=recycling_tendency,
        crust_creation_tendency=crust_creation_tendency,
        crust_destruction_tendency=crust_destruction_tendency,
        uplift_tendency=uplift_tendency,
        basin_tendency=basin_tendency,
        terrain_class=terrain_class_from_fields(
            np.zeros(len(ordered_regions), dtype=float),
            boundary_influence_type,
            basin_tendency,
            uplift_tendency,
        ),
        elevation=np.zeros(len(ordered_regions), dtype=float),
        temperature=np.zeros(len(ordered_regions), dtype=float),
        crust_type=string_array(
            initial_crust_type_for_region(region) for region in ordered_regions
        ),
        resurfacing_fraction=np.zeros(len(ordered_regions), dtype=float),
        surface_age_proxy=np.ones(len(ordered_regions), dtype=float),
        lava_coverage=np.zeros(len(ordered_regions), dtype=float),
        crater_density=np.zeros(len(ordered_regions), dtype=float),
        regolith_depth=np.zeros(len(ordered_regions), dtype=float),
        weathering_intensity=np.zeros(len(ordered_regions), dtype=float),
        dust_cover=np.zeros(len(ordered_regions), dtype=float),
        exposed_bedrock_fraction=np.ones(len(ordered_regions), dtype=float),
        water_depth=np.zeros(len(ordered_regions), dtype=float),
        volcanic_hotspot=np.zeros(len(ordered_regions), dtype=float),
        impact_intensity=np.zeros(len(ordered_regions), dtype=float),
        runoff_flux=np.zeros(len(ordered_regions), dtype=float),
        basin_index=np.zeros(len(ordered_regions), dtype=float),
        flow_receiver_index=np.arange(len(ordered_regions), dtype=np.int32),
        basin_fill=np.zeros(len(ordered_regions), dtype=float),
        glacier_presence=np.zeros(len(ordered_regions), dtype=float),
        inland_sea=np.zeros(len(ordered_regions), dtype=float),
        edge_region_indices=edge_region_indices,
        edge_boundary_type=edge_boundary_type,
        edge_interaction_index=edge_interaction_index,
        metadata={
            "source_surface_model": getattr(surface_model, "model", "unknown"),
            "source_surface_geometry": getattr(surface_model, "geometry", "unknown"),
            "present_day_regime": getattr(surface_model, "present_day_regime", "unknown"),
            "plate_count": int(getattr(surface_model, "plate_count", 0)),
            "boundary_count": int(getattr(surface_model, "boundary_count", 0)),
            "active_plate_ids": list(getattr(surface_model, "active_plate_ids", ())),
            "subdivision_rule": "authoritative_tectonic_mesh",
        },
    )


def subdivide_lat_lon_surface(surface: PlanetSurface) -> PlanetSurface:
    child_longitude_cells, child_latitude_cells = subdivided_surface_grid_resolution(
        (surface.longitude_cells, surface.latitude_cells)
    )
    parent_boundary_lookup = boundary_side_lookup(surface)

    region_count = child_longitude_cells * child_latitude_cells
    child_index_lookup: dict[tuple[int, int], int] = {}
    region_ids: list[str] = []
    parent_cell_id: list[str] = []
    root_tectonic_cell_id: list[str] = []
    child_index_within_parent: list[int] = []
    latitude_index: list[int] = []
    longitude_index: list[int] = []
    latitude_south_degrees: list[float] = []
    latitude_north_degrees: list[float] = []
    longitude_west_degrees: list[float] = []
    longitude_east_degrees: list[float] = []
    center_latitude_degrees: list[float] = []
    center_longitude_degrees: list[float] = []
    tectonic_active: list[str] = []
    plate_id: list[str] = []
    plate_region_id: list[str] = []
    boundary_role: list[str] = []
    boundary_influence_type: list[str] = []
    boundary_influence_index: list[float] = []
    motion_direction: list[str] = []
    motion_vector_cm_per_yr: list[list[float]] = []
    lithosphere_rigidity: list[float] = []
    thermal_stress: list[float] = []
    fracture_susceptibility: list[float] = []
    proto_rift_likelihood: list[float] = []
    upwelling_tendency: list[float] = []
    recycling_tendency: list[float] = []
    crust_creation_tendency: list[float] = []
    crust_destruction_tendency: list[float] = []
    uplift_tendency: list[float] = []
    basin_tendency: list[float] = []
    terrain_class: list[str] = []
    elevation: list[float] = []
    temperature: list[float] = []
    crust_type: list[str] = []
    resurfacing_fraction: list[float] = []
    surface_age_proxy: list[float] = []
    lava_coverage: list[float] = []
    crater_density: list[float] = []
    regolith_depth: list[float] = []
    weathering_intensity: list[float] = []
    dust_cover: list[float] = []
    exposed_bedrock_fraction: list[float] = []
    water_depth: list[float] = []
    volcanic_hotspot: list[float] = []
    impact_intensity: list[float] = []
    runoff_flux: list[float] = []
    basin_index: list[float] = []
    flow_receiver_index = np.arange(region_count, dtype=np.int32)
    basin_fill: list[float] = []
    glacier_presence: list[float] = []
    inland_sea: list[float] = []

    for parent_index in range(surface.region_ids.shape[0]):
        parent_id = str(surface.region_ids[parent_index])
        lat_south = float(surface.latitude_south_degrees[parent_index])
        lat_north = float(surface.latitude_north_degrees[parent_index])
        lon_west = float(surface.longitude_west_degrees[parent_index])
        lon_east = float(surface.longitude_east_degrees[parent_index])
        lat_mid = 0.5 * (lat_south + lat_north)
        lon_mid = 0.5 * (lon_west + lon_east)
        parent_latitude = int(surface.latitude_index[parent_index])
        parent_longitude = int(surface.longitude_index[parent_index])
        root_id = str(surface.root_tectonic_cell_id[parent_index])
        tectonic_flag = str(surface.tectonic_active[parent_index])
        parent_boundary_role = str(surface.boundary_role[parent_index])

        child_specs = (
            (0, 0, lat_south, lat_mid, lon_west, lon_mid),
            (0, 1, lat_south, lat_mid, lon_mid, lon_east),
            (1, 0, lat_mid, lat_north, lon_west, lon_mid),
            (1, 1, lat_mid, lat_north, lon_mid, lon_east),
        )
        for child_number, (lat_offset, lon_offset, child_south, child_north, child_west, child_east) in enumerate(child_specs):
            child_latitude_index = (parent_latitude * 2) + lat_offset
            child_longitude_index = (parent_longitude * 2) + lon_offset
            child_linear_index = grid_vertex_index(
                child_latitude_index, child_longitude_index, child_longitude_cells
            )
            child_index_lookup[(child_latitude_index, child_longitude_index)] = child_linear_index
            region_ids.append(f"{parent_id}.{child_number}")
            parent_cell_id.append(parent_id)
            root_tectonic_cell_id.append(root_id)
            child_index_within_parent.append(child_number)
            latitude_index.append(child_latitude_index)
            longitude_index.append(child_longitude_index)
            latitude_south_degrees.append(child_south)
            latitude_north_degrees.append(child_north)
            longitude_west_degrees.append(child_west)
            longitude_east_degrees.append(child_east)
            center_latitude_degrees.append(0.5 * (child_south + child_north))
            center_longitude_degrees.append(0.5 * (child_west + child_east))
            tectonic_active.append(tectonic_flag)
            plate_id.append(str(surface.plate_id[parent_index]))
            plate_region_id.append(str(surface.plate_region_id[parent_index]))
            motion_direction.append(str(surface.motion_direction[parent_index]))
            motion_vector_cm_per_yr.append(
                [
                    float(surface.motion_vector_cm_per_yr[parent_index, 0]),
                    float(surface.motion_vector_cm_per_yr[parent_index, 1]),
                ]
            )
            lithosphere_rigidity.append(float(surface.lithosphere_rigidity[parent_index]))
            thermal_stress.append(float(surface.thermal_stress[parent_index]))
            fracture_susceptibility.append(float(surface.fracture_susceptibility[parent_index]))
            proto_rift_likelihood.append(float(surface.proto_rift_likelihood[parent_index]))
            upwelling_tendency.append(float(surface.upwelling_tendency[parent_index]))
            recycling_tendency.append(float(surface.recycling_tendency[parent_index]))
            crust_creation_tendency.append(float(surface.crust_creation_tendency[parent_index]))
            crust_destruction_tendency.append(float(surface.crust_destruction_tendency[parent_index]))
            uplift_tendency.append(float(surface.uplift_tendency[parent_index]))
            basin_tendency.append(float(surface.basin_tendency[parent_index]))
            elevation.append(float(surface.elevation[parent_index]))
            temperature.append(float(surface.temperature[parent_index]))
            crust_type.append(str(surface.crust_type[parent_index]))
            resurfacing_fraction.append(float(surface.resurfacing_fraction[parent_index]))
            surface_age_proxy.append(float(surface.surface_age_proxy[parent_index]))
            lava_coverage.append(float(surface.lava_coverage[parent_index]))
            crater_density.append(float(surface.crater_density[parent_index]))
            regolith_depth.append(float(surface.regolith_depth[parent_index]))
            weathering_intensity.append(float(surface.weathering_intensity[parent_index]))
            dust_cover.append(float(surface.dust_cover[parent_index]))
            exposed_bedrock_fraction.append(float(surface.exposed_bedrock_fraction[parent_index]))
            water_depth.append(float(surface.water_depth[parent_index]))
            volcanic_hotspot.append(float(surface.volcanic_hotspot[parent_index]))
            impact_intensity.append(float(surface.impact_intensity[parent_index]))
            runoff_flux.append(float(surface.runoff_flux[parent_index]))
            basin_index.append(float(surface.basin_index[parent_index]))
            basin_fill.append(float(surface.basin_fill[parent_index]))
            glacier_presence.append(float(surface.glacier_presence[parent_index]))
            inland_sea.append(float(surface.inland_sea[parent_index]))

            boundary_candidates: list[tuple[str, float]] = []
            if child_number in {0, 2} and (parent_index, "west") in parent_boundary_lookup:
                boundary_candidates.append(parent_boundary_lookup[(parent_index, "west")])
            if child_number in {1, 3} and (parent_index, "east") in parent_boundary_lookup:
                boundary_candidates.append(parent_boundary_lookup[(parent_index, "east")])
            if child_number in {0, 1} and (parent_index, "south") in parent_boundary_lookup:
                boundary_candidates.append(parent_boundary_lookup[(parent_index, "south")])
            if child_number in {2, 3} and (parent_index, "north") in parent_boundary_lookup:
                boundary_candidates.append(parent_boundary_lookup[(parent_index, "north")])
            child_boundary_type, child_boundary_index = preferred_boundary_type(boundary_candidates)
            boundary_influence_type.append(child_boundary_type)
            boundary_influence_index.append(child_boundary_index)
            if child_boundary_type == "none" and parent_boundary_role in {"inactive", "ambiguous"}:
                boundary_role.append(parent_boundary_role)
            else:
                boundary_role.append(boundary_role_for_influence(tectonic_flag, child_boundary_type))
            terrain_class.append(str(surface.terrain_class[parent_index]))

    neighbor_indices = stable_neighbor_matrix(child_longitude_cells, child_latitude_cells)
    vertices = np.asarray(
        [
            lat_lon_to_cartesian(latitude, longitude, surface.radius_km)
            for latitude, longitude in zip(center_latitude_degrees, center_longitude_degrees)
        ],
        dtype=float,
    )
    faces = build_lat_lon_faces(child_longitude_cells, child_latitude_cells)

    edge_pairs: list[tuple[int, int]] = []
    edge_types: list[str] = []
    edge_interactions: list[float] = []
    for child_latitude_index in range(child_latitude_cells):
        for child_longitude_index in range(child_longitude_cells):
            region_a_index = child_index_lookup[(child_latitude_index, child_longitude_index)]
            east_neighbor_index = child_index_lookup[
                (child_latitude_index, (child_longitude_index + 1) % child_longitude_cells)
            ]
            if plate_id[region_a_index] != plate_id[east_neighbor_index]:
                boundary_type, interaction_index = preferred_boundary_type(
                    [
                        (boundary_influence_type[region_a_index], boundary_influence_index[region_a_index]),
                        (boundary_influence_type[east_neighbor_index], boundary_influence_index[east_neighbor_index]),
                    ]
                )
                edge_pairs.append((region_a_index, east_neighbor_index))
                edge_types.append(boundary_type if boundary_type != "none" else "indeterminate")
                edge_interactions.append(interaction_index)
            if child_latitude_index < child_latitude_cells - 1:
                north_neighbor_index = child_index_lookup[
                    (child_latitude_index + 1, child_longitude_index)
                ]
                if plate_id[region_a_index] != plate_id[north_neighbor_index]:
                    boundary_type, interaction_index = preferred_boundary_type(
                        [
                            (boundary_influence_type[region_a_index], boundary_influence_index[region_a_index]),
                            (boundary_influence_type[north_neighbor_index], boundary_influence_index[north_neighbor_index]),
                        ]
                    )
                    edge_pairs.append((region_a_index, north_neighbor_index))
                    edge_types.append(boundary_type if boundary_type != "none" else "indeterminate")
                    edge_interactions.append(interaction_index)

    uplift_array = uplift_tendency_from_fields(
        string_array(boundary_influence_type),
        np.asarray(boundary_influence_index, dtype=float),
        np.asarray(recycling_tendency, dtype=float),
        np.asarray(crust_destruction_tendency, dtype=float),
        np.asarray(lithosphere_rigidity, dtype=float),
    )
    basin_array = basin_tendency_from_fields(
        string_array(boundary_influence_type),
        np.asarray(boundary_influence_index, dtype=float),
        np.asarray(proto_rift_likelihood, dtype=float),
        np.asarray(upwelling_tendency, dtype=float),
        np.asarray(crust_creation_tendency, dtype=float),
    )

    return PlanetSurface(
        model=surface.model,
        geometry=surface.geometry,
        mesh_level="terrain_mesh",
        subdivision_level=surface.subdivision_level + 1,
        step_index=surface.step_index,
        age_years=surface.age_years,
        radius_km=surface.radius_km,
        longitude_cells=child_longitude_cells,
        latitude_cells=child_latitude_cells,
        vertices=vertices,
        faces=faces,
        region_ids=string_array(region_ids),
        parent_cell_id=string_array(parent_cell_id),
        root_tectonic_cell_id=string_array(root_tectonic_cell_id),
        child_index_within_parent=np.asarray(child_index_within_parent, dtype=np.int32),
        latitude_index=np.asarray(latitude_index, dtype=np.int32),
        longitude_index=np.asarray(longitude_index, dtype=np.int32),
        latitude_south_degrees=np.asarray(latitude_south_degrees, dtype=float),
        latitude_north_degrees=np.asarray(latitude_north_degrees, dtype=float),
        longitude_west_degrees=np.asarray(longitude_west_degrees, dtype=float),
        longitude_east_degrees=np.asarray(longitude_east_degrees, dtype=float),
        center_latitude_degrees=np.asarray(center_latitude_degrees, dtype=float),
        center_longitude_degrees=np.asarray(center_longitude_degrees, dtype=float),
        neighbor_indices=neighbor_indices,
        tectonic_active=string_array(tectonic_active),
        plate_id=string_array(plate_id),
        plate_region_id=string_array(plate_region_id),
        boundary_role=string_array(boundary_role),
        boundary_influence_type=string_array(boundary_influence_type),
        boundary_influence_index=np.asarray(boundary_influence_index, dtype=float),
        motion_direction=string_array(motion_direction),
        motion_vector_cm_per_yr=np.asarray(motion_vector_cm_per_yr, dtype=float),
        lithosphere_rigidity=np.asarray(lithosphere_rigidity, dtype=float),
        thermal_stress=np.asarray(thermal_stress, dtype=float),
        fracture_susceptibility=np.asarray(fracture_susceptibility, dtype=float),
        proto_rift_likelihood=np.asarray(proto_rift_likelihood, dtype=float),
        upwelling_tendency=np.asarray(upwelling_tendency, dtype=float),
        recycling_tendency=np.asarray(recycling_tendency, dtype=float),
        crust_creation_tendency=np.asarray(crust_creation_tendency, dtype=float),
        crust_destruction_tendency=np.asarray(crust_destruction_tendency, dtype=float),
        uplift_tendency=uplift_array,
        basin_tendency=basin_array,
        terrain_class=terrain_class_from_fields(
            np.asarray(elevation, dtype=float),
            string_array(boundary_influence_type),
            basin_array,
            uplift_array,
        ),
        elevation=np.asarray(elevation, dtype=float),
        temperature=np.asarray(temperature, dtype=float),
        crust_type=string_array(crust_type),
        resurfacing_fraction=np.asarray(resurfacing_fraction, dtype=float),
        surface_age_proxy=np.asarray(surface_age_proxy, dtype=float),
        lava_coverage=np.asarray(lava_coverage, dtype=float),
        crater_density=np.asarray(crater_density, dtype=float),
        regolith_depth=np.asarray(regolith_depth, dtype=float),
        weathering_intensity=np.asarray(weathering_intensity, dtype=float),
        dust_cover=np.asarray(dust_cover, dtype=float),
        exposed_bedrock_fraction=np.asarray(exposed_bedrock_fraction, dtype=float),
        water_depth=np.asarray(water_depth, dtype=float),
        volcanic_hotspot=np.asarray(volcanic_hotspot, dtype=float),
        impact_intensity=np.asarray(impact_intensity, dtype=float),
        runoff_flux=np.asarray(runoff_flux, dtype=float),
        basin_index=np.asarray(basin_index, dtype=float),
        flow_receiver_index=flow_receiver_index,
        basin_fill=np.asarray(basin_fill, dtype=float),
        glacier_presence=np.asarray(glacier_presence, dtype=float),
        inland_sea=np.asarray(inland_sea, dtype=float),
        edge_region_indices=np.asarray(edge_pairs, dtype=np.int32).reshape(-1, 2),
        edge_boundary_type=string_array(edge_types),
        edge_interaction_index=np.asarray(edge_interactions, dtype=float),
        metadata={
            **json.loads(json.dumps(surface.metadata, sort_keys=True)),
            "parent_mesh_level": surface.mesh_level,
            "parent_surface_grid_resolution": surface_grid_resolution_label(
                surface.longitude_cells, surface.latitude_cells
            ),
            "subdivision_rule": "deterministic_lat_lon_quadrisection",
            "subdivision_child_order": list(CHILD_SUBDIVISION_ORDER),
            "root_surface_grid_resolution": surface.metadata.get(
                "root_surface_grid_resolution",
                surface_grid_resolution_label(surface.longitude_cells, surface.latitude_cells),
            ),
        },
    )


def save_planet_surface(surface: PlanetSurface, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        model=np.asarray(surface.model),
        geometry=np.asarray(surface.geometry),
        mesh_level=np.asarray(surface.mesh_level),
        subdivision_level=np.asarray(surface.subdivision_level, dtype=np.int32),
        step_index=np.asarray(surface.step_index, dtype=np.int32),
        age_years=np.asarray(surface.age_years, dtype=np.int64),
        radius_km=np.asarray(surface.radius_km, dtype=float),
        longitude_cells=np.asarray(surface.longitude_cells, dtype=np.int32),
        latitude_cells=np.asarray(surface.latitude_cells, dtype=np.int32),
        vertices=surface.vertices,
        faces=surface.faces,
        region_ids=surface.region_ids,
        parent_cell_id=surface.parent_cell_id,
        root_tectonic_cell_id=surface.root_tectonic_cell_id,
        child_index_within_parent=surface.child_index_within_parent,
        latitude_index=surface.latitude_index,
        longitude_index=surface.longitude_index,
        latitude_south_degrees=surface.latitude_south_degrees,
        latitude_north_degrees=surface.latitude_north_degrees,
        longitude_west_degrees=surface.longitude_west_degrees,
        longitude_east_degrees=surface.longitude_east_degrees,
        center_latitude_degrees=surface.center_latitude_degrees,
        center_longitude_degrees=surface.center_longitude_degrees,
        neighbor_indices=surface.neighbor_indices,
        tectonic_active=surface.tectonic_active,
        plate_id=surface.plate_id,
        plate_region_id=surface.plate_region_id,
        boundary_role=surface.boundary_role,
        boundary_influence_type=surface.boundary_influence_type,
        boundary_influence_index=surface.boundary_influence_index,
        motion_direction=surface.motion_direction,
        motion_vector_cm_per_yr=surface.motion_vector_cm_per_yr,
        lithosphere_rigidity=surface.lithosphere_rigidity,
        thermal_stress=surface.thermal_stress,
        fracture_susceptibility=surface.fracture_susceptibility,
        proto_rift_likelihood=surface.proto_rift_likelihood,
        upwelling_tendency=surface.upwelling_tendency,
        recycling_tendency=surface.recycling_tendency,
        crust_creation_tendency=surface.crust_creation_tendency,
        crust_destruction_tendency=surface.crust_destruction_tendency,
        uplift_tendency=surface.uplift_tendency,
        basin_tendency=surface.basin_tendency,
        terrain_class=surface.terrain_class,
        elevation=surface.elevation,
        temperature=surface.temperature,
        crust_type=surface.crust_type,
        resurfacing_fraction=surface.resurfacing_fraction,
        surface_age_proxy=surface.surface_age_proxy,
        lava_coverage=surface.lava_coverage,
        crater_density=surface.crater_density,
        regolith_depth=surface.regolith_depth,
        weathering_intensity=surface.weathering_intensity,
        dust_cover=surface.dust_cover,
        exposed_bedrock_fraction=surface.exposed_bedrock_fraction,
        water_depth=surface.water_depth,
        volcanic_hotspot=surface.volcanic_hotspot,
        impact_intensity=surface.impact_intensity,
        runoff_flux=surface.runoff_flux,
        basin_index=surface.basin_index,
        flow_receiver_index=surface.flow_receiver_index,
        basin_fill=surface.basin_fill,
        glacier_presence=surface.glacier_presence,
        inland_sea=surface.inland_sea,
        edge_region_indices=surface.edge_region_indices,
        edge_boundary_type=surface.edge_boundary_type,
        edge_interaction_index=surface.edge_interaction_index,
        metadata_json=np.asarray(json.dumps(surface.metadata, sort_keys=True)),
    )
    return output_path


def load_planet_surface(input_path: Path) -> PlanetSurface:
    with np.load(input_path, allow_pickle=False) as payload:
        return PlanetSurface(
            model=str(payload["model"].item()),
            geometry=str(payload["geometry"].item()),
            mesh_level=str(payload["mesh_level"].item()),
            subdivision_level=int(payload["subdivision_level"].item()),
            step_index=int(payload["step_index"].item()),
            age_years=int(payload["age_years"].item()),
            radius_km=float(payload["radius_km"].item()),
            longitude_cells=int(payload["longitude_cells"].item()),
            latitude_cells=int(payload["latitude_cells"].item()),
            vertices=np.array(payload["vertices"], copy=True),
            faces=np.array(payload["faces"], copy=True),
            region_ids=np.array(payload["region_ids"], copy=True),
            parent_cell_id=np.array(payload["parent_cell_id"], copy=True),
            root_tectonic_cell_id=np.array(payload["root_tectonic_cell_id"], copy=True),
            child_index_within_parent=np.array(payload["child_index_within_parent"], copy=True),
            latitude_index=np.array(payload["latitude_index"], copy=True),
            longitude_index=np.array(payload["longitude_index"], copy=True),
            latitude_south_degrees=np.array(payload["latitude_south_degrees"], copy=True),
            latitude_north_degrees=np.array(payload["latitude_north_degrees"], copy=True),
            longitude_west_degrees=np.array(payload["longitude_west_degrees"], copy=True),
            longitude_east_degrees=np.array(payload["longitude_east_degrees"], copy=True),
            center_latitude_degrees=np.array(
                payload["center_latitude_degrees"], copy=True
            ),
            center_longitude_degrees=np.array(
                payload["center_longitude_degrees"], copy=True
            ),
            neighbor_indices=np.array(payload["neighbor_indices"], copy=True),
            tectonic_active=np.array(payload["tectonic_active"], copy=True),
            plate_id=np.array(payload["plate_id"], copy=True),
            plate_region_id=np.array(payload["plate_region_id"], copy=True),
            boundary_role=np.array(payload["boundary_role"], copy=True),
            boundary_influence_type=np.array(payload["boundary_influence_type"], copy=True),
            boundary_influence_index=np.array(payload["boundary_influence_index"], copy=True),
            motion_direction=np.array(payload["motion_direction"], copy=True),
            motion_vector_cm_per_yr=np.array(
                payload["motion_vector_cm_per_yr"], copy=True
            ),
            lithosphere_rigidity=np.array(payload["lithosphere_rigidity"], copy=True),
            thermal_stress=np.array(payload["thermal_stress"], copy=True),
            fracture_susceptibility=np.array(
                payload["fracture_susceptibility"], copy=True
            ),
            proto_rift_likelihood=np.array(
                payload["proto_rift_likelihood"], copy=True
            ),
            upwelling_tendency=np.array(payload["upwelling_tendency"], copy=True),
            recycling_tendency=np.array(payload["recycling_tendency"], copy=True),
            crust_creation_tendency=np.array(
                payload["crust_creation_tendency"], copy=True
            ),
            crust_destruction_tendency=np.array(
                payload["crust_destruction_tendency"], copy=True
            ),
            uplift_tendency=np.array(payload["uplift_tendency"], copy=True),
            basin_tendency=np.array(payload["basin_tendency"], copy=True),
            terrain_class=np.array(payload["terrain_class"], copy=True),
            elevation=np.array(payload["elevation"], copy=True),
            temperature=np.array(payload["temperature"], copy=True),
            crust_type=np.array(payload["crust_type"], copy=True),
            resurfacing_fraction=np.array(payload["resurfacing_fraction"], copy=True),
            surface_age_proxy=np.array(payload["surface_age_proxy"], copy=True),
            lava_coverage=np.array(payload["lava_coverage"], copy=True),
            crater_density=np.array(payload["crater_density"], copy=True),
            regolith_depth=np.array(payload["regolith_depth"], copy=True),
            weathering_intensity=np.array(payload["weathering_intensity"], copy=True),
            dust_cover=np.array(payload["dust_cover"], copy=True),
            exposed_bedrock_fraction=np.array(
                payload["exposed_bedrock_fraction"], copy=True
            ),
            water_depth=np.array(payload["water_depth"], copy=True),
            volcanic_hotspot=np.array(payload["volcanic_hotspot"], copy=True),
            impact_intensity=np.array(payload["impact_intensity"], copy=True),
            runoff_flux=np.array(payload["runoff_flux"], copy=True),
            basin_index=np.array(payload["basin_index"], copy=True),
            flow_receiver_index=np.array(payload["flow_receiver_index"], copy=True),
            basin_fill=np.array(payload["basin_fill"], copy=True),
            glacier_presence=np.array(payload["glacier_presence"], copy=True),
            inland_sea=np.array(payload["inland_sea"], copy=True),
            edge_region_indices=np.array(payload["edge_region_indices"], copy=True),
            edge_boundary_type=np.array(payload["edge_boundary_type"], copy=True),
            edge_interaction_index=np.array(
                payload["edge_interaction_index"], copy=True
            ),
            metadata=json.loads(str(payload["metadata_json"].item())),
        )


def region_records(surface: PlanetSurface) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index in range(surface.region_ids.shape[0]):
        neighbor_ids = [
            str(surface.region_ids[neighbor_index])
            for neighbor_index in surface.neighbor_indices[index]
            if int(neighbor_index) >= 0
        ]
        records.append(
            {
                "region_id": str(surface.region_ids[index]),
                "cell_id": str(surface.region_ids[index]),
                "mesh_level": surface.mesh_level,
                "subdivision_level": int(surface.subdivision_level),
                "parent_cell_id": str(surface.parent_cell_id[index]),
                "root_tectonic_cell_id": str(surface.root_tectonic_cell_id[index]),
                "child_index_within_parent": int(surface.child_index_within_parent[index]),
                "latitude_index": int(surface.latitude_index[index]),
                "longitude_index": int(surface.longitude_index[index]),
                "latitude_south_degrees": float(surface.latitude_south_degrees[index]),
                "latitude_north_degrees": float(surface.latitude_north_degrees[index]),
                "longitude_west_degrees": float(surface.longitude_west_degrees[index]),
                "longitude_east_degrees": float(surface.longitude_east_degrees[index]),
                "center_latitude_degrees": float(surface.center_latitude_degrees[index]),
                "center_longitude_degrees": float(
                    surface.center_longitude_degrees[index]
                ),
                "neighbor_region_ids": neighbor_ids,
                "tectonic_active": str(surface.tectonic_active[index]),
                "plate_id": str(surface.plate_id[index]),
                "plate_region_id": str(surface.plate_region_id[index]),
                "boundary_role": str(surface.boundary_role[index]),
                "boundary_influence_type": str(surface.boundary_influence_type[index]),
                "boundary_influence_index": float(surface.boundary_influence_index[index]),
                "motion_direction": str(surface.motion_direction[index]),
                "motion_vector_cm_per_yr": [
                    float(surface.motion_vector_cm_per_yr[index, 0]),
                    float(surface.motion_vector_cm_per_yr[index, 1]),
                ],
                "lithosphere_rigidity": float(surface.lithosphere_rigidity[index]),
                "thermal_stress": float(surface.thermal_stress[index]),
                "fracture_susceptibility": float(
                    surface.fracture_susceptibility[index]
                ),
                "proto_rift_likelihood": float(surface.proto_rift_likelihood[index]),
                "upwelling_tendency": float(surface.upwelling_tendency[index]),
                "recycling_tendency": float(surface.recycling_tendency[index]),
                "crust_creation_tendency": float(
                    surface.crust_creation_tendency[index]
                ),
                "crust_destruction_tendency": float(
                    surface.crust_destruction_tendency[index]
                ),
                "uplift_tendency": float(surface.uplift_tendency[index]),
                "basin_tendency": float(surface.basin_tendency[index]),
                "terrain_class": str(surface.terrain_class[index]),
                "elevation_m": float(surface.elevation[index]),
                "temperature_c": float(surface.temperature[index]),
                "crust_type": str(surface.crust_type[index]),
                "resurfacing_fraction": float(surface.resurfacing_fraction[index]),
                "surface_age_proxy": float(surface.surface_age_proxy[index]),
                "lava_coverage": float(surface.lava_coverage[index]),
                "crater_density": float(surface.crater_density[index]),
                "regolith_depth_m": float(surface.regolith_depth[index]),
                "weathering_intensity": float(surface.weathering_intensity[index]),
                "dust_cover": float(surface.dust_cover[index]),
                "exposed_bedrock_fraction": float(surface.exposed_bedrock_fraction[index]),
                "water_depth_m": float(surface.water_depth[index]),
                "volcanic_hotspot_index": float(surface.volcanic_hotspot[index]),
                "impact_intensity_index": float(surface.impact_intensity[index]),
                "runoff_flux_index": float(surface.runoff_flux[index]),
                "basin_index": float(surface.basin_index[index]),
                "flow_receiver_region_id": str(
                    surface.region_ids[int(surface.flow_receiver_index[index])]
                ),
                "basin_fill_index": float(surface.basin_fill[index]),
                "glacier_presence_index": float(surface.glacier_presence[index]),
                "inland_sea_index": float(surface.inland_sea[index]),
            }
        )
    return records


def boundary_records(surface: PlanetSurface) -> list[dict[str, Any]]:
    boundaries: list[dict[str, Any]] = []
    for edge_index in range(surface.edge_region_indices.shape[0]):
        region_a_index = int(surface.edge_region_indices[edge_index, 0])
        region_b_index = int(surface.edge_region_indices[edge_index, 1])
        boundaries.append(
            {
                "boundary_id": f"edge_{edge_index:04d}",
                "region_a_id": str(surface.region_ids[region_a_index]),
                "region_b_id": str(surface.region_ids[region_b_index]),
                "plate_a_id": str(surface.plate_id[region_a_index]),
                "plate_b_id": str(surface.plate_id[region_b_index]),
                "boundary_type": str(surface.edge_boundary_type[edge_index]),
                "interaction_index": float(surface.edge_interaction_index[edge_index]),
            }
        )
    return boundaries


def surface_json_payload(
    surface: PlanetSurface,
    *,
    state_path: Path | None = None,
    frame_directory: Path | None = None,
) -> dict[str, Any]:
    return {
        "model": surface.model,
        "geometry": surface.geometry,
        "mesh_level": surface.mesh_level,
        "subdivision_level": int(surface.subdivision_level),
        "surface_grid_resolution": surface_grid_resolution_label(
            surface.longitude_cells, surface.latitude_cells
        ),
        "step_index": surface.step_index,
        "age_years": surface.age_years,
        "radius_km": surface.radius_km,
        "region_count": int(surface.region_ids.shape[0]),
        "face_count": int(surface.faces.shape[0]),
        "state_path": str(state_path) if state_path is not None else None,
        "frame_directory": str(frame_directory) if frame_directory is not None else None,
        "field_names": [
            "parent_cell_id",
            "root_tectonic_cell_id",
            "child_index_within_parent",
            "tectonic_active",
            "plate_id",
            "plate_region_id",
            "boundary_role",
            "boundary_influence_type",
            "boundary_influence_index",
            "motion_direction",
            "motion_vector_cm_per_yr",
            "lithosphere_rigidity",
            "thermal_stress",
            "fracture_susceptibility",
            "proto_rift_likelihood",
            "upwelling_tendency",
            "recycling_tendency",
            "crust_creation_tendency",
            "crust_destruction_tendency",
            "uplift_tendency",
            "basin_tendency",
            "terrain_class",
            "elevation_m",
            "temperature_c",
            "crust_type",
            "resurfacing_fraction",
            "surface_age_proxy",
            "lava_coverage",
            "crater_density",
            "regolith_depth_m",
            "weathering_intensity",
            "dust_cover",
            "exposed_bedrock_fraction",
            "water_depth_m",
            "volcanic_hotspot_index",
            "impact_intensity_index",
            "runoff_flux_index",
            "basin_index",
            "flow_receiver_region_id",
            "basin_fill_index",
            "glacier_presence_index",
            "inland_sea_index",
        ],
        "vertices_xyz": surface.vertices.tolist(),
        "faces": surface.faces.tolist(),
        "regions": region_records(surface),
        "boundaries": boundary_records(surface),
        "metadata": surface.metadata,
    }
