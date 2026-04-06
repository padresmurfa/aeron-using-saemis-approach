#!/usr/bin/env python3
"""Deterministic primary crust formation simulation for Aeron."""

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

interior = load_pipeline_module(__package__, __file__, "02_interior")
planet = load_pipeline_module(__package__, __file__, "01_planet")

getcontext().prec = 50

SURFACE_SOLID_WEIGHT = Decimal("0.55")
PRIMORDIAL_CRUST_WEIGHT = Decimal("0.35")
COOLING_RELIEF_WEIGHT = Decimal("0.10")
STABLE_CRUST_THRESHOLD = Decimal("0.25")
STABLE_CRUST_SPAN = Decimal("0.75")
STABILITY_COOLING_BASE = Decimal("0.55")
STABILITY_COOLING_SPAN = Decimal("0.45")
WEAK_ZONE_BASE = Decimal("0.18")
WEAK_ZONE_CONVECTION_WEIGHT = Decimal("0.42")
WEAK_ZONE_SURFACE_WEIGHT = Decimal("0.25")
WEAK_ZONE_STABILITY_WEIGHT = Decimal("0.15")
VALIDATION_STEP_YEARS = 100_000_000
ZONAL_LATITUDE_BAND_COUNT = 181
ZONAL_POLAR_SOLIDIFICATION_RELIEF = Decimal("0.22")
ZONAL_SOLID_SURFACE_THRESHOLD = Decimal("0.58")
ZONAL_STABLE_CRUST_THRESHOLD = Decimal("0.10")
SURFACE_CATEGORY_COLORS = {
    "molten": "#d1495b",
    "mixed": "#edae49",
    "solid_crust": "#5c5346",
}
SURFACE_CATEGORY_LABELS = {
    "molten": "Molten",
    "mixed": "Mixed",
    "solid_crust": "Solid Crust",
}


@dataclass(frozen=True)
class PrimaryCrustState:
    step_index: int
    age_years: int
    mass_earth: Decimal
    radius_km: Decimal
    total_internal_heat_tw: Decimal
    cooling_index: Decimal
    solid_fraction: Decimal
    primordial_crust_fraction: Decimal
    convection_index: Decimal
    gross_crust_thickness_km: Decimal
    stable_crust_thickness_km: Decimal
    stable_crust_fraction: Decimal
    stable_crust_state: str
    crust_regime: str
    weak_zone_fraction: Decimal
    weak_zone_pattern: str
    surface_solid_index: Decimal
    surface_state: str
    world_class: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's primary crust formation by ticking the "
            "interior-thermal layer and deriving surface-lid behavior from it."
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


def decimal_from_float(value: float) -> Decimal:
    return Decimal(str(value))


def surface_solid_index_at(state: interior.InteriorState) -> Decimal:
    return clamp_unit_interval(
        (SURFACE_SOLID_WEIGHT * state.solid_fraction)
        + (PRIMORDIAL_CRUST_WEIGHT * state.primordial_crust_fraction)
        + (COOLING_RELIEF_WEIGHT * (Decimal("1") - state.cooling_index))
    )


def surface_state_at(surface_solid_index: Decimal) -> str:
    if surface_solid_index < Decimal("0.35"):
        return "mostly_molten"
    if surface_solid_index < Decimal("0.70"):
        return "mixed"
    return "mostly_solid"


def stable_crust_fraction_at(
    state: interior.InteriorState, surface_solid_index: Decimal
) -> Decimal:
    if surface_solid_index <= STABLE_CRUST_THRESHOLD:
        return Decimal("0")

    normalized_surface = (
        surface_solid_index - STABLE_CRUST_THRESHOLD
    ) / STABLE_CRUST_SPAN
    cooling_modifier = STABILITY_COOLING_BASE + (
        STABILITY_COOLING_SPAN * (Decimal("1") - state.cooling_index)
    )
    return clamp_unit_interval(
        normalized_surface * state.primordial_crust_fraction * cooling_modifier
    )


def stable_crust_state_at(stable_crust_fraction: Decimal) -> str:
    if stable_crust_fraction < Decimal("0.10"):
        return "absent"
    if stable_crust_fraction < Decimal("0.35"):
        return "intermittent"
    if stable_crust_fraction < Decimal("0.70"):
        return "regional"
    return "persistent"


def crust_regime_at(
    state: interior.InteriorState, stable_crust_fraction: Decimal
) -> str:
    if (
        stable_crust_fraction < Decimal("0.10")
        or state.primordial_crust_fraction < Decimal("0.45")
    ):
        return "undifferentiated"
    if (
        stable_crust_fraction >= Decimal("0.80")
        and state.convection_index < Decimal("0.50")
        and state.cooling_index < Decimal("0.28")
    ):
        return "continental_like"
    return "oceanic_like"


def weak_zone_fraction_at(
    state: interior.InteriorState,
    surface_solid_index: Decimal,
    stable_crust_fraction: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        WEAK_ZONE_BASE
        + (WEAK_ZONE_CONVECTION_WEIGHT * state.convection_index)
        + (WEAK_ZONE_SURFACE_WEIGHT * (Decimal("1") - surface_solid_index))
        + (WEAK_ZONE_STABILITY_WEIGHT * (Decimal("1") - stable_crust_fraction))
    )


def weak_zone_pattern_at(
    state: interior.InteriorState,
    surface_state: str,
    weak_zone_fraction: Decimal,
) -> str:
    if surface_state == "mostly_molten":
        return "global_overturn_scars"
    if surface_state == "mixed" and weak_zone_fraction >= Decimal("0.65"):
        return "global_cooling_fractures"
    if state.convection_index >= Decimal("0.70"):
        return "proto_rift_web"
    if state.convection_index >= Decimal("0.55"):
        return "upwelling_margin_corridors"
    return "localized_mobile_belts"


def primary_crust_state_from_interior_state(
    base_state: interior.InteriorState,
) -> PrimaryCrustState:
    gross_crust_thickness_km = planet.crust_thickness_at(base_state.radius_km)
    surface_solid_index = surface_solid_index_at(base_state)
    stable_crust_fraction = stable_crust_fraction_at(base_state, surface_solid_index)
    surface_state = surface_state_at(surface_solid_index)
    weak_zone_fraction = weak_zone_fraction_at(
        base_state, surface_solid_index, stable_crust_fraction
    )
    return PrimaryCrustState(
        step_index=base_state.step_index,
        age_years=base_state.age_years,
        mass_earth=base_state.mass_earth,
        radius_km=base_state.radius_km,
        total_internal_heat_tw=base_state.total_internal_heat_tw,
        cooling_index=base_state.cooling_index,
        solid_fraction=base_state.solid_fraction,
        primordial_crust_fraction=base_state.primordial_crust_fraction,
        convection_index=base_state.convection_index,
        gross_crust_thickness_km=gross_crust_thickness_km,
        stable_crust_thickness_km=gross_crust_thickness_km * stable_crust_fraction,
        stable_crust_fraction=stable_crust_fraction,
        stable_crust_state=stable_crust_state_at(stable_crust_fraction),
        crust_regime=crust_regime_at(base_state, stable_crust_fraction),
        weak_zone_fraction=weak_zone_fraction,
        weak_zone_pattern=weak_zone_pattern_at(
            base_state, surface_state, weak_zone_fraction
        ),
        surface_solid_index=surface_solid_index,
        surface_state=surface_state,
        world_class=base_state.world_class,
    )


def simulate(criteria: planet.SimulationCriteria) -> Iterable[PrimaryCrustState]:
    def build_states() -> Iterable[PrimaryCrustState]:
        for base_state in interior.simulate(criteria):
            yield primary_crust_state_from_interior_state(base_state)

    return materialize_layer_states(__file__, criteria, build_states)


def first_stable_crust_state(
    states: Iterable[PrimaryCrustState],
) -> PrimaryCrustState | None:
    for state in states:
        if state.stable_crust_state != "absent":
            return state
    return None


def zonal_surface_indices_at(
    state: PrimaryCrustState, latitude_degrees: float
) -> tuple[Decimal, Decimal]:
    """Return a latitude-only solidification view for the crust layer.

    This layer does not own longitude-resolved structure. The visualization
    therefore stays zonal and uses only a symmetric pole-to-equator relief:
    poles cool slightly faster, the equator slightly slower. The result is a
    latitude-band schematic derived from the real global crust state rather than
    a fake 2D world map.
    """

    latitude_radians = math.radians(latitude_degrees)
    polar_relief = ZONAL_POLAR_SOLIDIFICATION_RELIEF * decimal_from_float(
        abs(math.sin(latitude_radians)) - 0.5
    )
    local_surface_solid_index = clamp_unit_interval(
        state.surface_solid_index + polar_relief
    )
    local_stable_crust_fraction = clamp_unit_interval(
        state.stable_crust_fraction + (polar_relief * Decimal("0.75"))
    )
    return local_surface_solid_index, local_stable_crust_fraction


def zonal_surface_category_at(state: PrimaryCrustState, latitude_degrees: float) -> str:
    local_surface_solid_index, local_stable_crust_fraction = zonal_surface_indices_at(
        state, latitude_degrees
    )
    if local_surface_solid_index < Decimal("0.35"):
        return "molten"
    if (
        local_surface_solid_index >= ZONAL_SOLID_SURFACE_THRESHOLD
        and local_stable_crust_fraction >= ZONAL_STABLE_CRUST_THRESHOLD
    ):
        return "solid_crust"
    return "mixed"


def zonal_latitude_samples() -> list[float]:
    return [
        -90.0 + (180.0 * index / (ZONAL_LATITUDE_BAND_COUNT - 1))
        for index in range(ZONAL_LATITUDE_BAND_COUNT)
    ]


def zonal_surface_heatmap(
    states: Sequence[PrimaryCrustState],
) -> tuple[list[list[int]], dict[str, list[float]], list[float]]:
    state_order = ("molten", "mixed", "solid_crust")
    category_to_code = {name: index for index, name in enumerate(state_order)}
    latitudes = zonal_latitude_samples()
    heatmap = [[0 for _ in states] for _ in latitudes]
    coverage = {name: [] for name in state_order}

    for state_index, state in enumerate(states):
        counts = {name: 0.0 for name in state_order}
        total_weight = 0.0
        for latitude_index, latitude in enumerate(latitudes):
            category = zonal_surface_category_at(state, latitude)
            heatmap[latitude_index][state_index] = category_to_code[category]
            weight = max(0.0, math.cos(math.radians(latitude)))
            counts[category] += weight
            total_weight += weight

        for category in state_order:
            if total_weight == 0.0:
                coverage[category].append(0.0)
            else:
                coverage[category].append(counts[category] / total_weight)

    return heatmap, coverage, latitudes


def zonal_visualization_output_path(current_file: str) -> Path:
    return step_output_path(current_file, "zonal_solidification.png")


def write_zonal_solidification_png(
    states: Sequence[PrimaryCrustState], current_file: str
) -> Path:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.colors import BoundaryNorm, ListedColormap
    except ImportError as exc:  # pragma: no cover - import-time dependency guard
        raise ImportError(
            "Zonal solidification visualization requires matplotlib. Install "
            "dependencies with `python3 -m pip install -r requirements.txt`."
        ) from exc

    if not states:
        raise ValueError("Primary crust visualization requires at least one state.")

    output_path = zonal_visualization_output_path(current_file)
    heatmap, coverage, latitudes = zonal_surface_heatmap(states)
    ages_myr = [
        float(Decimal(state.age_years) / planet.YEARS_PER_MYR) for state in states
    ]
    first_stable_state = first_stable_crust_state(states)
    first_stable_age_myr = (
        float(Decimal(first_stable_state.age_years) / planet.YEARS_PER_MYR)
        if first_stable_state is not None
        else None
    )

    fig = plt.figure(figsize=(13.4, 9.6), facecolor="#f6f1e8")
    grid = fig.add_gridspec(2, 1, height_ratios=(1.0, 1.35), hspace=0.26)
    coverage_ax = fig.add_subplot(grid[0, 0])
    heatmap_ax = fig.add_subplot(grid[1, 0])

    coverage_ax.set_facecolor("#fffdf8")
    baseline = [0.0 for _ in ages_myr]
    for category in ("molten", "mixed", "solid_crust"):
        values = coverage[category]
        top = [base + value for base, value in zip(baseline, values)]
        coverage_ax.fill_between(
            ages_myr,
            baseline,
            top,
            color=SURFACE_CATEGORY_COLORS[category],
            alpha=0.92,
            linewidth=0.0,
            label=SURFACE_CATEGORY_LABELS[category],
        )
        baseline = top

    if first_stable_age_myr is not None:
        coverage_ax.axvline(
            first_stable_age_myr,
            color="#1f2937",
            linewidth=1.2,
            linestyle="--",
            alpha=0.7,
        )

    coverage_ax.set_ylim(0.0, 1.0)
    coverage_ax.set_xlim(ages_myr[0], ages_myr[-1])
    coverage_ax.set_ylabel("Area Fraction", color="#1f2937")
    coverage_ax.set_title(
        "03 Primary Crust: Zonal Surface Solidification",
        loc="left",
        color="#1f2937",
        fontsize=18,
        pad=14,
    )
    coverage_ax.grid(True, axis="y", color="#d7d2c8", linewidth=0.8, alpha=0.8)
    for spine in coverage_ax.spines.values():
        spine.set_color("#d7d2c8")
    coverage_ax.tick_params(colors="#6b7280")
    coverage_ax.legend(frameon=False, ncol=3, loc="upper left")

    cmap = ListedColormap(
        [
            SURFACE_CATEGORY_COLORS["molten"],
            SURFACE_CATEGORY_COLORS["mixed"],
            SURFACE_CATEGORY_COLORS["solid_crust"],
        ]
    )
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)
    heatmap_ax.set_facecolor("#fffdf8")
    heatmap_ax.imshow(
        heatmap,
        origin="lower",
        aspect="auto",
        extent=(ages_myr[0], ages_myr[-1], latitudes[0], latitudes[-1]),
        cmap=cmap,
        norm=norm,
        interpolation="nearest",
    )
    if first_stable_age_myr is not None:
        heatmap_ax.axvline(
            first_stable_age_myr,
            color="#1f2937",
            linewidth=1.2,
            linestyle="--",
            alpha=0.7,
        )
    heatmap_ax.set_xlabel("Age (Myr)", color="#1f2937")
    heatmap_ax.set_ylabel("Latitude (degrees)", color="#1f2937")
    heatmap_ax.set_yticks([-90, -60, -30, 0, 30, 60, 90])
    heatmap_ax.tick_params(colors="#6b7280")
    for spine in heatmap_ax.spines.values():
        spine.set_color("#d7d2c8")

    fig.text(
        0.125,
        0.02,
        (
            "Zonal-only schematic: this layer resolves latitude bands, not true "
            "surface geography. The polar bands cool ahead of the equator using a "
            "deterministic symmetric relief applied to the real global crust state."
        ),
        ha="left",
        va="bottom",
        fontsize=10,
        color="#6b7280",
    )
    fig.subplots_adjust(left=0.08, right=0.97, top=0.93, bottom=0.12, hspace=0.28)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output_path


def validate_model() -> None:
    interior.validate_model()
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria))
    initial_state = states[0]
    present_state = states[-1]
    first_stable_state = first_stable_crust_state(states)

    if initial_state.surface_state != "mostly_molten":
        raise ValueError("Primary crust layer must start from a mostly molten surface.")
    if present_state.surface_state != "mostly_solid":
        raise ValueError("Present-day Aeron should end with a mostly solid surface.")
    if first_stable_state is None:
        raise ValueError("Stable crust must emerge somewhere in the simulation span.")
    if not initial_state.stable_crust_thickness_km < present_state.stable_crust_thickness_km:
        raise ValueError("Stable crust thickness must grow across the simulation span.")
    if initial_state.crust_regime != "undifferentiated":
        raise ValueError("Primary crust should begin in an undifferentiated regime.")
    if present_state.crust_regime == "undifferentiated":
        raise ValueError("Present-day Aeron should not remain undifferentiated.")
    if not initial_state.weak_zone_fraction > present_state.weak_zone_fraction:
        raise ValueError("Weak zones should become less globally dominant over time.")


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "primary_crust_formation"),
        ("interior_source", "02_interior.py"),
        ("planet_source", "01_planet.py"),
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
        ("surface_model", "coarse_first_pass_solid_lid"),
        ("crust_stability_model", "primary_lid_stabilization"),
        ("crust_regime_model", "undifferentiated_to_oceanic_like_first"),
        ("weak_zone_model", "surface_plus_convection_plus_stability"),
        (
            "dynamic_fields",
            "mass_earth, radius_km, total_internal_heat_tw, "
            "gross_crust_thickness_km, stable_crust_thickness_km, "
            "stable_crust_fraction, stable_crust_state, crust_regime, "
            "weak_zone_fraction, weak_zone_pattern, surface_solid_index, "
            "surface_state",
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print("INPUT CRITERIA")
    print("==============")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")
    print()


def print_table(states: Sequence[PrimaryCrustState]) -> None:
    headers = (
        ("step", 8),
        ("age_myr", 12),
        ("radius_km", 12),
        ("heat_tw", 10),
        ("cool_ix", 8),
        ("solid", 8),
        ("surf", 12),
        ("gross_km", 10),
        ("stable_km", 10),
        ("stable_f", 8),
        ("stable_state", 12),
        ("crust_type", 16),
        ("weak_ix", 8),
        ("weak_zones", 28),
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
            f"{planet.format_decimal(state.radius_km, 6):>12} "
            f"{planet.format_decimal(state.total_internal_heat_tw, 6):>10} "
            f"{planet.format_decimal(state.cooling_index, 3):>8} "
            f"{planet.format_decimal(state.solid_fraction, 3):>8} "
            f"{state.surface_state:>12} "
            f"{planet.format_decimal(state.gross_crust_thickness_km, 6):>10} "
            f"{planet.format_decimal(state.stable_crust_thickness_km, 6):>10} "
            f"{planet.format_decimal(state.stable_crust_fraction, 3):>8} "
            f"{state.stable_crust_state:>12} "
            f"{state.crust_regime:>16} "
            f"{planet.format_decimal(state.weak_zone_fraction, 3):>8} "
            f"{state.weak_zone_pattern:>28}"
        )


def print_present_day_summary(states: Sequence[PrimaryCrustState]) -> None:
    final_state = states[-1]
    first_stable_state = first_stable_crust_state(states)

    assert first_stable_state is not None

    fields = [
        ("world_class", final_state.world_class),
        ("radius_km", planet.format_decimal(final_state.radius_km, 6)),
        (
            "gross_crust_thickness_km",
            planet.format_decimal(final_state.gross_crust_thickness_km, 6),
        ),
        (
            "stable_crust_thickness_km",
            planet.format_decimal(final_state.stable_crust_thickness_km, 6),
        ),
        (
            "stable_crust_fraction",
            planet.format_decimal(final_state.stable_crust_fraction, 6),
        ),
        ("stable_crust_state", final_state.stable_crust_state),
        ("crust_regime", final_state.crust_regime),
        (
            "surface_solid_index",
            planet.format_decimal(final_state.surface_solid_index, 6),
        ),
        ("surface_state", final_state.surface_state),
        ("weak_zone_fraction", planet.format_decimal(final_state.weak_zone_fraction, 6)),
        ("weak_zone_pattern", final_state.weak_zone_pattern),
        ("first_stable_crust_step", str(first_stable_state.step_index)),
        (
            "first_stable_crust_age_myr",
            planet.format_decimal(
                Decimal(first_stable_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
        ("transition_status", "ball_to_solid_world_complete"),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT PRIMARY CRUST SUMMARY")
    print("=============================")
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
        raise SystemExit("Primary crust simulation produced no timestep states.")

    print_input_criteria(criteria)
    print_table(states)
    print_present_day_summary(states)

    try:
        write_zonal_solidification_png(states, __file__)
    except (ImportError, OSError, ValueError) as exc:
        raise SystemExit(
            f"Failed to write zonal solidification visualization: {exc}"
        ) from exc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
