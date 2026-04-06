#!/usr/bin/env python3
"""Deterministic interior structure and thermal evolution simulation for Aeron.

When run as a script, this module prints deterministic timestep tables, a
present-interior summary, and a present-state cutaway PNG that makes the coarse
interior model legible to humans.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Iterable, Sequence

try:
    from .world_building_paths import step_output_path
    from .world_building_support import load_pipeline_module, materialize_layer_states
except ImportError:
    from world_building_paths import step_output_path  # type: ignore
    from world_building_support import load_pipeline_module, materialize_layer_states  # type: ignore

planet = load_pipeline_module(__package__, __file__, "01_planet")

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

CUTAWAY_FILENAME = "cutaway_present.png"
CUTAWAY_TITLE = "Aeron Present-Day Interior Cutaway"
CUTAWAY_SUBTITLE = "Deterministic coarse interior structure from the final simulated state"

FIGURE_BACKGROUND = "#f3efe7"
FIGURE_PANEL = "#fffaf2"
TEXT_COLOR = "#1f2937"
MUTED_TEXT = "#667085"
LINE_COLOR = "#475467"
CARD_BORDER = "#d0c7b8"
CARD_FILL = "#fffdf8"

SPACE_GLOW = "#dbeafe"
PLANET_OUTLINE = "#173241"
PLANET_SURFACE = "#6b8391"
PLANET_SHADOW = "#405564"
PLANET_HIGHLIGHT = "#8ea6b2"
PLANET_STREAK = "#a7bbc4"
PLANET_BAND = "#7a8f68"

LAYER_COLORS = {
    "primordial_crust": "#f4e7c9",
    "mantle": "#d97706",
    "differentiated_core": "#c2410c",
    "residual_melt": "#fde68a",
}

DISPLAY_THICKNESS_EXAGGERATION_KEYS = frozenset({"primordial_crust"})
MIN_DISPLAY_THICKNESS_FRACTION = Decimal("0.016")
MIN_DISPLAY_THICKNESS_FLOOR_KM = Decimal("75")
WEDGE_HALF_ANGLE_DEG = 38


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


@dataclass(frozen=True)
class InteriorLayerBand:
    key: str
    label: str
    actual_outer_radius_km: Decimal
    actual_inner_radius_km: Decimal
    display_outer_radius_km: Decimal
    display_inner_radius_km: Decimal
    color: str

    @property
    def actual_thickness_km(self) -> Decimal:
        return self.actual_outer_radius_km - self.actual_inner_radius_km

    @property
    def display_thickness_km(self) -> Decimal:
        return self.display_outer_radius_km - self.display_inner_radius_km


@dataclass(frozen=True)
class PresentInteriorGeometry:
    planet_radius_km: Decimal
    planet_mass_kg: Decimal
    age_gyr: Decimal
    crust_thickness_km: Decimal
    core_radius_km: Decimal
    residual_melt_radius_km: Decimal
    display_note: str | None
    layers: tuple[InteriorLayerBand, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's interior structure and thermal evolution by "
            "ticking the bulk-planet layer, printing the timestep outputs, and "
            "exporting a deterministic present-state interior cutaway PNG."
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


def pretty_label(value: str) -> str:
    return value.replace("_", " ").strip().title()


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


def build_interior_states(criteria: planet.SimulationCriteria) -> tuple[InteriorState, ...]:
    return tuple(
        interior_state_from_planet_state(base_state)
        for base_state in planet.simulate(criteria)
    )


def simulate(criteria: planet.SimulationCriteria) -> Iterable[InteriorState]:
    return materialize_layer_states(__file__, criteria, lambda: build_interior_states(criteria))


def validate_model() -> None:
    planet.validate_model()
    reference_criteria = planet.build_criteria(planet.TOTAL_DURATION_YEARS)
    states = build_interior_states(reference_criteria)
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


def primordial_crust_thickness_km(state: InteriorState) -> Decimal:
    return planet.crust_thickness_at(state.radius_km) * clamp_unit_interval(
        state.primordial_crust_fraction
    )


def core_radius_km(state: InteriorState, crust_thickness_km: Decimal) -> Decimal:
    non_crust_radius = state.radius_km - crust_thickness_km
    if non_crust_radius <= Decimal("0"):
        return Decimal("0")

    total_differentiation = (
        clamp_unit_interval(state.core_formation_fraction)
        + clamp_unit_interval(state.mantle_formation_fraction)
    )
    if total_differentiation <= Decimal("0"):
        return Decimal("0")

    # The interior model tracks core and mantle formation progress, but not
    # explicit radii. For the cutaway, allocate the non-crust interior between
    # mantle shell and core sphere using those relative differentiation
    # fractions so the displayed boundary remains tied to the simulated state.
    return non_crust_radius * state.core_formation_fraction / total_differentiation


def residual_melt_radius_km(state: InteriorState, core_radius_value_km: Decimal) -> Decimal:
    if core_radius_value_km <= Decimal("0"):
        return Decimal("0")

    # The model does not explicitly separate inner and outer core. The central
    # "residual melt" region therefore visualizes the unsolidified share of the
    # coarse interior model rather than claiming a literal inner-core radius.
    return core_radius_value_km * (Decimal("1") - clamp_unit_interval(state.solid_fraction))


def build_actual_layer_band_data(
    state: InteriorState,
) -> tuple[list[tuple[str, str, Decimal, Decimal]], Decimal, Decimal, Decimal]:
    crust_thickness_value = primordial_crust_thickness_km(state)
    core_radius_value = core_radius_km(state, crust_thickness_value)
    residual_melt_radius_value = residual_melt_radius_km(state, core_radius_value)
    mantle_outer_radius = state.radius_km - crust_thickness_value

    band_data: list[tuple[str, str, Decimal, Decimal]] = []
    if crust_thickness_value > Decimal("0"):
        band_data.append(
            (
                "primordial_crust",
                "Primordial Crust",
                state.radius_km,
                mantle_outer_radius,
            )
        )
    if mantle_outer_radius > core_radius_value:
        band_data.append(("mantle", "Mantle", mantle_outer_radius, core_radius_value))
    if core_radius_value > residual_melt_radius_value:
        band_data.append(
            (
                "differentiated_core",
                "Differentiated Core",
                core_radius_value,
                residual_melt_radius_value,
            )
        )
    if residual_melt_radius_value > Decimal("0"):
        band_data.append(
            ("residual_melt", "Residual Melt", residual_melt_radius_value, Decimal("0"))
        )

    return band_data, crust_thickness_value, core_radius_value, residual_melt_radius_value


def build_display_layer_bands(
    layer_data: Sequence[tuple[str, str, Decimal, Decimal]], planet_radius_km: Decimal
) -> tuple[tuple[InteriorLayerBand, ...], str | None]:
    if not layer_data:
        return (), None

    min_display_thickness = max(
        planet_radius_km * MIN_DISPLAY_THICKNESS_FRACTION,
        MIN_DISPLAY_THICKNESS_FLOOR_KM,
    )
    actual_thicknesses = [outer - inner for _, _, outer, inner in layer_data]

    display_thicknesses: list[Decimal] = []
    extra_total = Decimal("0")
    compressible_total = Decimal("0")
    crust_display_adjusted = False
    crust_actual_thickness = Decimal("0")
    crust_display_thickness = Decimal("0")

    for (key, _, _, _), actual_thickness in zip(layer_data, actual_thicknesses):
        if key in DISPLAY_THICKNESS_EXAGGERATION_KEYS and actual_thickness > Decimal("0"):
            display_thickness = max(actual_thickness, min_display_thickness)
            extra_total += display_thickness - actual_thickness
            if display_thickness != actual_thickness:
                crust_display_adjusted = True
                crust_actual_thickness = actual_thickness
                crust_display_thickness = display_thickness
        else:
            display_thickness = actual_thickness
            compressible_total += actual_thickness
        display_thicknesses.append(display_thickness)

    if extra_total > Decimal("0") and compressible_total > Decimal("0"):
        compression_scale = (compressible_total - extra_total) / compressible_total
        if compression_scale <= Decimal("0"):
            raise ValueError("Display thickness exaggeration exceeded available interior radius.")

        for index, (key, _, _, _) in enumerate(layer_data):
            if key not in DISPLAY_THICKNESS_EXAGGERATION_KEYS:
                display_thicknesses[index] *= compression_scale

    display_outer_radius = planet_radius_km
    layers: list[InteriorLayerBand] = []
    for (key, label, actual_outer_radius, actual_inner_radius), display_thickness in zip(
        layer_data, display_thicknesses
    ):
        display_inner_radius = max(Decimal("0"), display_outer_radius - display_thickness)
        layers.append(
            InteriorLayerBand(
                key=key,
                label=label,
                actual_outer_radius_km=actual_outer_radius,
                actual_inner_radius_km=actual_inner_radius,
                display_outer_radius_km=display_outer_radius,
                display_inner_radius_km=display_inner_radius,
                color=LAYER_COLORS[key],
            )
        )
        display_outer_radius = display_inner_radius

    display_note = None
    if crust_display_adjusted:
        display_note = (
            "Crust thickness is display-enhanced from "
            f"{planet.format_decimal(crust_actual_thickness, 1)} km to "
            f"{planet.format_decimal(crust_display_thickness, 1)} km for readability."
        )

    return tuple(layers), display_note


def build_present_interior_geometry(state: InteriorState) -> PresentInteriorGeometry:
    layer_data, crust_thickness_value, core_radius_value, residual_melt_radius_value = (
        build_actual_layer_band_data(state)
    )
    layers, display_note = build_display_layer_bands(layer_data, state.radius_km)
    return PresentInteriorGeometry(
        planet_radius_km=state.radius_km,
        planet_mass_kg=planet.mass_kg_at(state.radius_km),
        age_gyr=Decimal(state.age_years) / planet.YEARS_PER_GYR,
        crust_thickness_km=crust_thickness_value,
        core_radius_km=core_radius_value,
        residual_melt_radius_km=residual_melt_radius_value,
        display_note=display_note,
        layers=layers,
    )


def dominant_heat_source(state: InteriorState) -> str:
    source = "residual"
    if state.radiogenic_heat_tw >= state.residual_heat_tw:
        source = "radiogenic"
    if state.tidal_heat_tw >= max(state.residual_heat_tw, state.radiogenic_heat_tw):
        source = "tidal"
    return source


def format_scientific(value: Decimal, significant_digits: int = 3) -> str:
    if value == 0:
        return "0"

    exponent = value.adjusted()
    mantissa = value.scaleb(-exponent)
    places = max(0, significant_digits - 1)
    mantissa_text = planet.format_decimal(mantissa, places)
    mantissa_value = Decimal(mantissa_text)
    if mantissa_value >= Decimal("10"):
        exponent += 1
        mantissa_value /= Decimal("10")
        mantissa_text = planet.format_decimal(mantissa_value, places)
    return f"{mantissa_text} x 10^{exponent}"


def interior_cutaway_output_path(current_file: str) -> Path:
    return step_output_path(current_file, CUTAWAY_FILENAME)


def label_anchor_angles(layer_count: int) -> list[float]:
    if layer_count <= 1:
        return [0.0]

    span = float(WEDGE_HALF_ANGLE_DEG) - 10.0
    step = (span * 2.0) / (layer_count - 1)
    return [span - (index * step) for index in range(layer_count)]


def adjusted_label_y_positions(anchor_y_positions: Sequence[float], radius_km: float) -> list[float]:
    min_gap = radius_km * 0.19
    upper_bound = radius_km * 0.78
    lower_bound = -radius_km * 0.78

    adjusted: list[float] = []
    previous_y: float | None = None
    for anchor_y in anchor_y_positions:
        y_position = min(anchor_y, upper_bound)
        if previous_y is not None and y_position > previous_y - min_gap:
            y_position = previous_y - min_gap
        adjusted.append(y_position)
        previous_y = y_position

    if adjusted and adjusted[-1] < lower_bound:
        shift = lower_bound - adjusted[-1]
        adjusted = [y + shift for y in adjusted]
    if adjusted and adjusted[0] > upper_bound:
        shift = upper_bound - adjusted[0]
        adjusted = [y + shift for y in adjusted]

    return adjusted


def summary_cards(
    state: InteriorState, geometry: PresentInteriorGeometry
) -> tuple[tuple[str, str], ...]:
    return (
        ("Age", f"{planet.format_decimal(geometry.age_gyr, 3)} Ga"),
        ("Radius", f"{planet.format_decimal(state.radius_km, 1)} km"),
        ("Mass", f"{format_scientific(geometry.planet_mass_kg, 3)} kg"),
        ("Crust Thickness", f"{planet.format_decimal(geometry.crust_thickness_km, 1)} km"),
        ("Core Radius", f"{planet.format_decimal(geometry.core_radius_km, 1)} km"),
        (
            "Convection",
            f"{planet.format_decimal(state.convection_index, 3)} ({pretty_label(state.convection_state)})",
        ),
    )


def render_interior_cutaway_png(state: InteriorState, current_file: str) -> Path:
    """Render a deterministic present-state cutaway diagram for the interior layer."""

    geometry = build_present_interior_geometry(state)
    if not geometry.layers:
        raise ValueError("Interior cutaway requires at least one modeled display layer.")

    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.patches import Circle, Ellipse, FancyBboxPatch, Wedge
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ImportError(
            "Interior cutaway visualization requires matplotlib. Install dependencies "
            "with `python3 -m pip install -r requirements.txt`."
        ) from exc

    output_path = interior_cutaway_output_path(current_file)
    planet_radius_float = float(geometry.planet_radius_km)
    center_x = -0.18 * planet_radius_float
    center_y = 0.0

    fig = plt.figure(figsize=(13.6, 10.2), facecolor=FIGURE_BACKGROUND)
    grid = fig.add_gridspec(2, 1, height_ratios=[4.4, 1.35], hspace=0.02)
    ax = fig.add_subplot(grid[0, 0])
    stats_ax = fig.add_subplot(grid[1, 0])

    ax.set_facecolor(FIGURE_PANEL)
    stats_ax.set_facecolor(FIGURE_BACKGROUND)

    for extra_radius, alpha in ((1.12, 0.18), (1.07, 0.12), (1.03, 0.08)):
        ax.add_patch(
            Circle(
                (center_x, center_y),
                planet_radius_float * extra_radius,
                facecolor=SPACE_GLOW,
                edgecolor="none",
                alpha=alpha,
                zorder=0,
            )
        )

    planet_disk = Circle(
        (center_x, center_y),
        planet_radius_float,
        facecolor=PLANET_SURFACE,
        edgecolor=PLANET_OUTLINE,
        linewidth=2.4,
        zorder=1,
    )
    ax.add_patch(planet_disk)

    for radius_factor, facecolor, alpha in (
        (0.97, PLANET_HIGHLIGHT, 0.16),
        (0.88, PLANET_SURFACE, 0.35),
        (0.78, PLANET_SHADOW, 0.18),
    ):
        ax.add_patch(
            Circle(
                (center_x - (0.08 * planet_radius_float), center_y + (0.10 * planet_radius_float)),
                planet_radius_float * radius_factor,
                facecolor=facecolor,
                edgecolor="none",
                alpha=alpha,
                zorder=2,
            )
        )

    for patch in (
        Ellipse(
            (center_x - (0.20 * planet_radius_float), center_y + (0.26 * planet_radius_float)),
            width=1.18 * planet_radius_float,
            height=0.24 * planet_radius_float,
            angle=-18,
            facecolor=PLANET_BAND,
            edgecolor="none",
            alpha=0.22,
            zorder=3,
        ),
        Ellipse(
            (center_x - (0.08 * planet_radius_float), center_y - (0.18 * planet_radius_float)),
            width=1.05 * planet_radius_float,
            height=0.18 * planet_radius_float,
            angle=12,
            facecolor=PLANET_STREAK,
            edgecolor="none",
            alpha=0.18,
            zorder=3,
        ),
        Ellipse(
            (center_x + (0.06 * planet_radius_float), center_y + (0.02 * planet_radius_float)),
            width=0.92 * planet_radius_float,
            height=0.12 * planet_radius_float,
            angle=-32,
            facecolor=PLANET_STREAK,
            edgecolor="none",
            alpha=0.12,
            zorder=3,
        ),
    ):
        patch.set_clip_path(planet_disk)
        ax.add_patch(patch)

    for layer in geometry.layers:
        outer_radius = float(layer.display_outer_radius_km)
        inner_radius = float(layer.display_inner_radius_km)
        if outer_radius <= 0:
            continue
        width = None if inner_radius <= 0 else outer_radius - inner_radius
        edgecolor = "#6b2f12"
        linewidth = 1.5
        if layer.key == "primordial_crust":
            edgecolor = "#8a6a34"
            linewidth = 2.2
        ax.add_patch(
            Wedge(
                (center_x, center_y),
                outer_radius,
                -WEDGE_HALF_ANGLE_DEG,
                WEDGE_HALF_ANGLE_DEG,
                width=width,
                facecolor=layer.color,
                edgecolor=edgecolor,
                linewidth=linewidth,
                zorder=6,
            )
        )

    ax.add_patch(
        Wedge(
            (center_x, center_y),
            planet_radius_float,
            -WEDGE_HALF_ANGLE_DEG,
            WEDGE_HALF_ANGLE_DEG,
            facecolor="none",
            edgecolor="#7c2d12",
            linewidth=2.0,
            zorder=7,
        )
    )

    ax.add_patch(
        Circle(
            (center_x, center_y),
            planet_radius_float,
            facecolor="none",
            edgecolor=PLANET_OUTLINE,
            linewidth=2.2,
            zorder=8,
        )
    )

    labels = list(geometry.layers)
    anchor_angles = label_anchor_angles(len(labels))
    anchor_y_positions: list[float] = []
    anchor_points: list[tuple[float, float]] = []
    for layer, angle_deg in zip(labels, anchor_angles):
        mid_radius = float(
            (layer.display_outer_radius_km + layer.display_inner_radius_km) / Decimal("2")
        )
        angle_rad = math.radians(angle_deg)
        anchor_x = center_x + (mid_radius * math.cos(angle_rad))
        anchor_y = center_y + (mid_radius * math.sin(angle_rad))
        anchor_points.append((anchor_x, anchor_y))
        anchor_y_positions.append(anchor_y)

    label_y_positions = adjusted_label_y_positions(anchor_y_positions, planet_radius_float)
    label_x = center_x + (1.58 * planet_radius_float)

    for layer, (anchor_x, anchor_y), label_y in zip(labels, anchor_points, label_y_positions):
        ax.annotate(
            layer.label,
            xy=(anchor_x, anchor_y),
            xytext=(label_x, label_y),
            ha="left",
            va="center",
            fontsize=12.5,
            color=TEXT_COLOR,
            arrowprops={
                "arrowstyle": "-",
                "color": LINE_COLOR,
                "lw": 1.6,
                "shrinkA": 0,
                "shrinkB": 4,
            },
            zorder=10,
        )

    ax.text(
        0.02,
        0.98,
        CUTAWAY_TITLE,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=22,
        color=TEXT_COLOR,
        weight="bold",
    )
    ax.text(
        0.02,
        0.925,
        CUTAWAY_SUBTITLE,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11.5,
        color=MUTED_TEXT,
    )
    ax.text(
        0.02,
        0.875,
        (
            f"State: {pretty_label(state.solidification_state)} | "
            f"Dominant heat source: {pretty_label(dominant_heat_source(state))} | "
            f"Tectonic readiness: {pretty_label(state.tectonic_readiness)}"
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10.5,
        color=MUTED_TEXT,
    )

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(center_x - (1.55 * planet_radius_float), center_x + (1.95 * planet_radius_float))
    ax.set_ylim(center_y - (1.22 * planet_radius_float), center_y + (1.22 * planet_radius_float))
    ax.axis("off")

    stats_ax.axis("off")
    cards = summary_cards(state, geometry)
    columns = 3
    rows = 2
    left_margin = 0.04
    gap = 0.025
    card_width = (1.0 - left_margin * 2 - gap * (columns - 1)) / columns
    card_height = 0.34
    row_y_positions = (0.54, 0.12)

    for index, (label, value) in enumerate(cards):
        row = index // columns
        column = index % columns
        x = left_margin + column * (card_width + gap)
        y = row_y_positions[row]
        stats_ax.add_patch(
            FancyBboxPatch(
                (x, y),
                card_width,
                card_height,
                transform=stats_ax.transAxes,
                boxstyle="round,pad=0.014,rounding_size=0.02",
                facecolor=CARD_FILL,
                edgecolor=CARD_BORDER,
                linewidth=1.2,
            )
        )
        stats_ax.text(
            x + 0.026,
            y + 0.23,
            label,
            transform=stats_ax.transAxes,
            ha="left",
            va="center",
            fontsize=10,
            color=MUTED_TEXT,
        )
        stats_ax.text(
            x + 0.026,
            y + 0.09,
            value,
            transform=stats_ax.transAxes,
            ha="left",
            va="center",
            fontsize=14.2,
            color=TEXT_COLOR,
            weight="bold",
        )

    footer_note = geometry.display_note or (
        "Layer radii are driven by the simulated present-state crust, core, mantle, and "
        "solidification fractions."
    )
    stats_ax.text(
        0.04,
        0.02,
        footer_note,
        transform=stats_ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9.4,
        color=MUTED_TEXT,
    )

    fig.savefig(
        output_path,
        dpi=220,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        metadata={
            "Title": CUTAWAY_TITLE,
            "Description": (
                "Deterministic present-state cutaway diagram for Aeron's coarse "
                "interior model."
            ),
        },
    )
    plt.close(fig)
    return output_path


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "interior_structure_and_thermal_evolution"),
        ("planet_source", "01_planet.py"),
        ("coupled_bulk_layer", "true"),
        ("deterministic", "true"),
        ("present_cutaway_png", CUTAWAY_FILENAME),
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


def print_table(states: Sequence[InteriorState]) -> None:
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

    for state in states:
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


def print_present_day_summary(final_state: InteriorState) -> None:
    geometry = build_present_interior_geometry(final_state)

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
        ("dominant_heat_source", dominant_heat_source(final_state)),
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
        (
            "derived_crust_thickness_km",
            planet.format_decimal(geometry.crust_thickness_km, 6),
        ),
        ("derived_core_radius_km", planet.format_decimal(geometry.core_radius_km, 6)),
        (
            "derived_residual_melt_radius_km",
            planet.format_decimal(geometry.residual_melt_radius_km, 6),
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

    states = simulate(criteria)
    if not states:
        raise SystemExit("Interior simulation produced no timestep states.")

    print_input_criteria(criteria)
    print_table(states)
    print_present_day_summary(states[-1])

    try:
        render_interior_cutaway_png(states[-1], __file__)
    except (ImportError, OSError, ValueError) as exc:
        raise SystemExit(f"Failed to write interior cutaway visualization: {exc}") from exc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
