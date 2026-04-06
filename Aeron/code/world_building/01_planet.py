#!/usr/bin/env python3
"""Deterministic bulk-evolution simulation for Aeron.

When run as a script, this module prints deterministic timestep tables, a
present-world summary, and deterministic PNGs that show Aeron's radius growth
as both concentric circles and quadrant-projected time-radius views.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Iterable, Sequence

try:
    from .world_building_paths import step_output_path
    from .world_building_support import materialize_layer_states
except ImportError:
    from world_building_paths import step_output_path  # type: ignore
    from world_building_support import materialize_layer_states  # type: ignore

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

VIS_BACKGROUND = "#f6f1e8"
VIS_PANEL = "#fffdf8"
VIS_TEXT = "#1f2937"
VIS_MUTED = "#6b7280"
VIS_GRID = "#d7d2c8"
RADIUS_GROWTH_FILENAME = "radius_growth.png"
RADIUS_GROWTH_TITLE = "Aeron Radius Growth Over Time"
RADIUS_QUADRANT_TIME_LINEAR_FILENAME = "radius_quadrant_time_linear.png"
RADIUS_QUADRANT_RADIUS_LINEAR_FILENAME = "radius_quadrant_radius_linear.png"
THERMAL_ERA_COLORS = (
    "#b42318",
    "#ea580c",
    "#f5b63f",
    "#7c4ab8",
    "#2563eb",
)
RADIUS_QUADRANT_TITLES = {
    "time_linear": "Aeron Radius Growth (Quadrant Projection - Time Linear)",
    "radius_linear": "Aeron Radius Growth (Quadrant Projection - Radius Linear)",
}
RADIUS_QUADRANT_SUBTITLES = {
    "time_linear": (
        "Upper-right quadrant projected so local horizontal distance maps linearly to time"
    ),
    "radius_linear": (
        "Upper-right quadrant projected so radius remains linear and time is derived from radius"
    ),
}


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
            "using fixed deterministic time steps, while exporting the standard "
            "text output, the concentric radius-growth PNG, and deterministic "
            "quadrant-projected time-radius PNGs."
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
        "--plot-radius-quadrant",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Write the derived upper-right-quadrant radius projections "
            "(time-linear and radius-linear). Default: %(default)s."
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
    def build_states() -> Iterable[PlanetState]:
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

    return materialize_layer_states(__file__, criteria, build_states)


def quantize(value: Decimal, places: int) -> Decimal:
    quantum = Decimal("1").scaleb(-places)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def format_decimal(value: Decimal, places: int) -> str:
    return f"{quantize(value, places):f}"


def visualization_output_path(current_file: str, filename: str) -> Path:
    return step_output_path(current_file, filename)


def radius_growth_output_path(current_file: str) -> Path:
    return visualization_output_path(current_file, RADIUS_GROWTH_FILENAME)


def radius_quadrant_output_path(current_file: str, mode: str) -> Path:
    filename_by_mode = {
        "time_linear": RADIUS_QUADRANT_TIME_LINEAR_FILENAME,
        "radius_linear": RADIUS_QUADRANT_RADIUS_LINEAR_FILENAME,
    }
    if mode not in filename_by_mode:
        raise ValueError(f"Unsupported radius quadrant projection mode: {mode}.")
    return visualization_output_path(current_file, filename_by_mode[mode])


def radius_growth_base_linewidth(state_count: int) -> float:
    if state_count <= 40:
        return 1.8
    if state_count <= 400:
        return 0.95
    if state_count <= 2_000:
        return 0.48
    return 0.22


def radius_growth_emphasis_stride(state_count: int) -> int:
    if state_count <= 24:
        return 1
    return max(1, state_count // 72)


def thermal_era_positions(states: Sequence[PlanetState]) -> list[float]:
    if not states:
        return []

    earliest_age = states[0].age_years
    latest_age = states[-1].age_years
    if latest_age == earliest_age:
        return [0.0 for _ in states]

    total_span = latest_age - earliest_age
    return [(state.age_years - earliest_age) / total_span for state in states]


def age_myr_from_years(age_years: int) -> float:
    return age_years / 1_000_000.0


def age_myr_at_radius(radius_km: float) -> float:
    """Invert the deterministic radius growth law back into simulation age."""

    initial_radius_km = float(INITIAL_RADIUS_KM)
    present_radius_km = float(EARTH_RADIUS_KM)
    growth_constant_per_year = float(GROWTH_CONSTANT_PER_YEAR)
    clamped_radius_km = min(max(radius_km, initial_radius_km), present_radius_km)
    if clamped_radius_km <= initial_radius_km or growth_constant_per_year == 0.0:
        return 0.0

    years = math.log(clamped_radius_km / initial_radius_km) / growth_constant_per_year
    years = min(max(years, 0.0), float(TOTAL_DURATION_YEARS))
    return years / 1_000_000.0


def radius_quadrant_base_linewidth(state_count: int) -> float:
    if state_count <= 40:
        return 1.6
    if state_count <= 400:
        return 0.95
    if state_count <= 2_000:
        return 0.55
    return 0.22


def radius_quadrant_emphasis_stride(state_count: int) -> int:
    if state_count <= 24:
        return 1
    return max(1, state_count // 64)


def radius_quadrant_sample_count(state_count: int) -> int:
    if state_count <= 12:
        return 96
    if state_count <= 400:
        return 72
    return 56


def quadrant_projection_points(
    state: PlanetState,
    mode: str,
    sample_count: int,
) -> list[tuple[float, float]]:
    """Project one timestep's upper-right circle quadrant into time-radius space.

    Original quadrant geometry for a timestep of radius ``r_i`` uses the exact
    circle relation ``x_local^2 + y_local^2 = r_i^2`` with ``x_local >= 0`` and
    ``y_local >= 0``.

    Time-linear mode keeps time intuitive by mapping the local horizontal
    fraction directly onto that state's actual simulation age:
    ``x_time = t_i * (x_local / r_i)`` and
    ``y_radius = sqrt(r_i^2 - x_local^2)``.

    Radius-linear mode keeps radius intuitive on the vertical axis, then derives
    time from the same local horizontal fraction. Because Aeron begins from a
    non-zero initial radius, the retained local horizontal fraction is rebased
    onto the modeled radius interval ``[r_0, r_i]`` before inverting the growth
    law: ``horizontal_radius = r_0 + u * (r_i - r_0)`` with
    ``u = x_local / r_i``, and ``x_time = age(horizontal_radius)``.

    Both modes therefore come from the same quadrant geometry rather than a
    conventional radius-versus-time line chart.
    """

    radius_km = float(state.radius_km)
    if radius_km <= 0.0:
        return [(0.0, 0.0)]

    age_myr = age_myr_from_years(state.age_years)
    initial_radius_km = float(INITIAL_RADIUS_KM)

    if sample_count <= 1:
        return [(0.0, radius_km)]

    points: list[tuple[float, float]] = []
    for sample_index in range(sample_count):
        local_fraction = sample_index / (sample_count - 1)
        x_local = radius_km * local_fraction
        y_radius = math.sqrt(max(radius_km * radius_km - x_local * x_local, 0.0))

        if mode == "time_linear":
            x_time = age_myr * local_fraction
        elif mode == "radius_linear":
            horizontal_radius_km = initial_radius_km + (
                local_fraction * max(radius_km - initial_radius_km, 0.0)
            )
            x_time = age_myr_at_radius(horizontal_radius_km)
        else:
            raise ValueError(f"Unsupported radius quadrant projection mode: {mode}.")

        points.append((x_time, y_radius))

    return points


def add_thermal_colorbar(fig: object, ax: object, color_norm: object, color_map: object) -> None:
    from matplotlib.cm import ScalarMappable

    colorbar = fig.colorbar(
        ScalarMappable(norm=color_norm, cmap=color_map),
        ax=ax,
        fraction=0.048,
        pad=0.035,
    )
    colorbar.set_label("Thermal era color encoding", color=VIS_TEXT, fontsize=11)
    colorbar.set_ticks([0.0, 1.0])
    colorbar.set_ticklabels(["Earlier / hotter", "Later / cooler"])
    colorbar.outline.set_edgecolor(VIS_GRID)
    colorbar.ax.tick_params(colors=VIS_MUTED, labelsize=10)


def write_radius_growth_png(states: Sequence[PlanetState], current_file: str) -> Path:
    """Render a deterministic concentric-circle radius timeline PNG.

    Each timestep contributes one unfilled full circle centered at ``(0, 0)``,
    with the circle radius equal to the simulated planetary radius in
    kilometers. Circles are drawn from earliest/smallest to latest/largest so
    the outer growth rings remain visible.

    The color ramp uses deterministic timestep ordering as a thermal-era
    encoding rather than ``internal_heat_tw``. In this bulk layer that scalar is
    size-scaled and increases with planetary growth, so it is not a reliable
    early-hot to late-cool thermometer. The palette therefore communicates the
    intended era progression directly: earlier/hotter visual states at the warm
    end, later/cooler visual states at the cool end.
    """

    if not states:
        raise ValueError("Radius-growth visualization requires at least one timestep state.")

    try:
        from matplotlib import colors, pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
        from matplotlib.patches import Circle
    except ImportError as exc:  # pragma: no cover - import-time dependency guard
        raise ImportError(
            "Radius-growth visualization requires matplotlib. Install dependencies "
            "with `python3 -m pip install -r requirements.txt`."
        ) from exc

    output_path = radius_growth_output_path(current_file)
    thermal_positions = thermal_era_positions(states)
    color_map = LinearSegmentedColormap.from_list(
        "aeron_radius_growth_thermal_era",
        THERMAL_ERA_COLORS,
    )
    color_norm = colors.Normalize(vmin=0.0, vmax=1.0)
    state_count = len(states)
    base_linewidth = radius_growth_base_linewidth(state_count)
    emphasis_stride = radius_growth_emphasis_stride(state_count)
    use_emphasis_halo = state_count > 120
    base_alpha = 0.48 if state_count > 400 else 0.82
    max_radius_km = max(float(state.radius_km) for state in states)
    axis_limit_km = max_radius_km * 1.08 if max_radius_km > 0.0 else 1.0

    fig, ax = plt.subplots(figsize=(10.8, 9.6), facecolor=VIS_BACKGROUND)
    ax.set_facecolor(VIS_PANEL)
    for spine in ax.spines.values():
        spine.set_color(VIS_GRID)

    ax.grid(True, color=VIS_GRID, linewidth=0.8, alpha=0.55)
    ax.tick_params(colors=VIS_MUTED, labelsize=10)
    ax.set_title(RADIUS_GROWTH_TITLE, loc="left", color=VIS_TEXT, fontsize=18, pad=14)
    ax.set_xlabel("X position (km)", color=VIS_TEXT, fontsize=11)
    ax.set_ylabel("Y position (km)", color=VIS_TEXT, fontsize=11)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-axis_limit_km, axis_limit_km)
    ax.set_ylim(-axis_limit_km, axis_limit_km)

    # Dense default runs can include thousands of circles. Draw every real
    # timestep, then emphasize a deterministic subset of those same circles so
    # the image still reads as discrete growth rings instead of a flat fill.
    for index, (state, thermal_position) in enumerate(zip(states, thermal_positions)):
        is_emphasized = index % emphasis_stride == 0 or index == state_count - 1
        radius_km = float(state.radius_km)
        circle_color = color_map(color_norm(thermal_position))
        emphasis_linewidth = base_linewidth * (2.8 if use_emphasis_halo else 1.6)

        if is_emphasized and use_emphasis_halo:
            halo = Circle(
                (0.0, 0.0),
                radius=radius_km,
                fill=False,
                linewidth=max(emphasis_linewidth * 1.9, 1.25),
                edgecolor=VIS_PANEL,
                alpha=0.98,
                zorder=2,
            )
            ax.add_patch(halo)

        circle = Circle(
            (0.0, 0.0),
            radius=radius_km,
            fill=False,
            linewidth=emphasis_linewidth if is_emphasized else base_linewidth,
            edgecolor=circle_color,
            alpha=0.97 if is_emphasized else base_alpha,
            zorder=3 if is_emphasized else 1,
        )
        ax.add_patch(circle)

    ax.axhline(0.0, color=VIS_MUTED, linewidth=1.15, alpha=0.85, zorder=5)
    ax.axvline(0.0, color=VIS_MUTED, linewidth=1.15, alpha=0.85, zorder=5)

    add_thermal_colorbar(fig, ax, color_norm, color_map)

    fig.tight_layout()
    fig.savefig(
        output_path,
        dpi=220,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        metadata={
            "Title": RADIUS_GROWTH_TITLE,
            "Description": (
                "Deterministic concentric-circle radius timeline for Aeron, with "
                "warm-to-cool colors mapped from earliest to latest timestep."
            ),
        },
    )
    plt.close(fig)
    return output_path


def render_radius_quadrant_projection(
    states: Sequence[PlanetState],
    current_file: str,
    *,
    mode: str,
) -> Path:
    """Render a quadrant-projected radius view derived from the concentric plot."""

    if not states:
        raise ValueError("Quadrant projection requires at least one timestep state.")

    if mode not in RADIUS_QUADRANT_TITLES:
        raise ValueError(f"Unsupported radius quadrant projection mode: {mode}.")

    try:
        from matplotlib import colors, pyplot as plt
        from matplotlib.collections import LineCollection
        from matplotlib.colors import LinearSegmentedColormap
    except ImportError as exc:  # pragma: no cover - import-time dependency guard
        raise ImportError(
            "Radius quadrant projection requires matplotlib. Install dependencies "
            "with `python3 -m pip install -r requirements.txt`."
        ) from exc

    output_path = radius_quadrant_output_path(current_file, mode)
    thermal_positions = thermal_era_positions(states)
    color_map = LinearSegmentedColormap.from_list(
        "aeron_radius_quadrant_thermal_era",
        THERMAL_ERA_COLORS,
    )
    color_norm = colors.Normalize(vmin=0.0, vmax=1.0)
    state_count = len(states)
    sample_count = radius_quadrant_sample_count(state_count)
    base_linewidth = radius_quadrant_base_linewidth(state_count)
    emphasis_stride = radius_quadrant_emphasis_stride(state_count)
    base_alpha = 0.18 if state_count > 400 else 0.48
    max_radius_km = max(float(state.radius_km) for state in states)
    max_age_myr = max(age_myr_from_years(state.age_years) for state in states)
    x_limit = max_age_myr * 1.03 if max_age_myr > 0.0 else 1.0
    y_limit = max_radius_km * 1.08 if max_radius_km > 0.0 else 1.0

    all_segments: list[list[tuple[float, float]]] = []
    all_colors: list[tuple[float, float, float, float]] = []
    emphasis_segments: list[list[tuple[float, float]]] = []
    emphasis_colors: list[tuple[float, float, float, float]] = []
    for index, (state, thermal_position) in enumerate(zip(states, thermal_positions)):
        segment = quadrant_projection_points(state, mode, sample_count)
        line_color = color_map(color_norm(thermal_position))
        all_segments.append(segment)
        all_colors.append(line_color)
        if index % emphasis_stride == 0 or index == state_count - 1:
            emphasis_segments.append(segment)
            emphasis_colors.append(line_color)

    fig, ax = plt.subplots(figsize=(12.2, 8.1), facecolor=VIS_BACKGROUND)
    ax.set_facecolor(VIS_PANEL)
    for spine in ax.spines.values():
        spine.set_color(VIS_GRID)

    ax.grid(True, color=VIS_GRID, linewidth=0.8, alpha=0.6)
    ax.tick_params(colors=VIS_MUTED, labelsize=10)
    ax.set_xlim(0.0, x_limit)
    ax.set_ylim(0.0, y_limit)
    ax.set_xlabel("Time (million years)", color=VIS_TEXT, fontsize=11)
    ax.set_ylabel("Radius (km)", color=VIS_TEXT, fontsize=11)
    ax.set_title(RADIUS_QUADRANT_TITLES[mode], loc="left", color=VIS_TEXT, fontsize=18, pad=28)
    ax.text(
        0.0,
        1.002,
        RADIUS_QUADRANT_SUBTITLES[mode],
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10.5,
        color=VIS_MUTED,
    )

    ax.add_collection(
        LineCollection(
            all_segments,
            colors=all_colors,
            linewidths=base_linewidth,
            alpha=base_alpha,
            capstyle="round",
            joinstyle="round",
            zorder=2,
        )
    )
    ax.add_collection(
        LineCollection(
            emphasis_segments,
            colors=emphasis_colors,
            linewidths=max(base_linewidth * 2.8, 0.9),
            alpha=0.94,
            capstyle="round",
            joinstyle="round",
            zorder=3,
        )
    )

    add_thermal_colorbar(fig, ax, color_norm, color_map)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    fig.savefig(
        output_path,
        dpi=220,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        metadata={
            "Title": RADIUS_QUADRANT_TITLES[mode],
            "Description": (
                "Deterministic upper-right-quadrant projection derived from Aeron's "
                "concentric radius-growth visualization."
            ),
        },
    )
    plt.close(fig)
    return output_path


def write_radius_quadrant_projection_pngs(
    states: Sequence[PlanetState], current_file: str
) -> tuple[Path, Path]:
    return (
        render_radius_quadrant_projection(states, current_file, mode="time_linear"),
        render_radius_quadrant_projection(states, current_file, mode="radius_linear"),
    )


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


def print_input_criteria(
    criteria: SimulationCriteria, *, plot_radius_quadrant: bool
) -> None:
    fields = [
        ("planet_name", "Aeron"),
        ("deterministic", "true"),
        ("bulk_world_class", BULK_WORLD_CLASS),
        ("radius_growth_png", RADIUS_GROWTH_FILENAME),
        ("plot_radius_quadrant", str(plot_radius_quadrant).lower()),
        ("radius_quadrant_time_linear_png", RADIUS_QUADRANT_TIME_LINEAR_FILENAME),
        ("radius_quadrant_radius_linear_png", RADIUS_QUADRANT_RADIUS_LINEAR_FILENAME),
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


def print_table(states: Sequence[PlanetState]) -> None:
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

    for state in states:
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


def print_present_day_summary(final_state: PlanetState) -> None:
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

    states = simulate(criteria)
    if not states:
        raise SystemExit("Planet simulation produced no timestep states.")

    print_input_criteria(criteria, plot_radius_quadrant=args.plot_radius_quadrant)
    print_table(states)
    print_present_day_summary(states[-1])

    try:
        write_radius_growth_png(states, __file__)
        if args.plot_radius_quadrant:
            write_radius_quadrant_projection_pngs(states, __file__)
    except (ImportError, OSError, ValueError) as exc:
        raise SystemExit(f"Failed to write radius visualizations: {exc}") from exc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
