#!/usr/bin/env python3
"""Deterministic surface temperature regime simulation for Aeron."""

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

early_atmosphere = load_pipeline_module(__package__, __file__, "04_early_atmosphere")
planet = load_pipeline_module(__package__, __file__, "01_planet")

getcontext().prec = 50

PRESSURE_GRADIENT_SATURATION_BAR = Decimal("1.5")
SEASONAL_CYCLING_BONUS_C = Decimal("4")
VALIDATION_STEP_YEARS = 100_000_000
ZONAL_LATITUDE_BAND_COUNT = 181
PROFILE_LATITUDES = (0.0, 45.0, 90.0)
TEMPERATURE_BAND_COLORS = {
    "molten_extreme": "#8b0000",
    "steamhouse_hot": "#d1495b",
    "hot": "#edae49",
    "temperate": "#72b7b2",
    "cold": "#4c78a8",
    "frozen": "#264653",
}
TEMPERATURE_BAND_LABELS = {
    "molten_extreme": "Molten Extreme",
    "steamhouse_hot": "Steamhouse Hot",
    "hot": "Hot",
    "temperate": "Temperate",
    "cold": "Cold",
    "frozen": "Frozen",
}


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


def temperature_visualization_output_path(current_file: str) -> Path:
    return step_output_path(current_file, "zonal_bands.png")


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
    def build_states() -> Iterable[SurfaceTemperatureState]:
        for base_state in early_atmosphere.simulate(criteria):
            yield surface_temperature_state_from_atmosphere_state(base_state)

    return materialize_layer_states(__file__, criteria, build_states)


def first_surface_liquids_state(
    states: Iterable[SurfaceTemperatureState],
) -> SurfaceTemperatureState | None:
    for state in states:
        if state.surface_liquid_state in {"transient", "stable"}:
            return state
    return None


def zonal_temperature_c_at(
    state: SurfaceTemperatureState, latitude_degrees: float
) -> Decimal:
    """Project the modeled global thermal state into latitude bands.

    The layer owns a mean surface temperature and an equator-to-pole delta, but
    not longitude-resolved geometry. This zonal view therefore uses a symmetric
    `cos(latitude)^2` profile. Subtracting two-thirds preserves the modeled
    area-weighted mean while the equator-to-pole contrast remains exactly the
    simulated `equator_to_pole_delta_c`.
    """

    latitude_radians = math.radians(latitude_degrees)
    latitudinal_shape = Decimal(str((math.cos(latitude_radians) ** 2) - (2.0 / 3.0)))
    return state.mean_surface_temp_c + (state.equator_to_pole_delta_c * latitudinal_shape)


def zonal_latitude_samples() -> list[float]:
    return [
        -90.0 + (180.0 * index / (ZONAL_LATITUDE_BAND_COUNT - 1))
        for index in range(ZONAL_LATITUDE_BAND_COUNT)
    ]


def zonal_temperature_band_heatmap(
    states: Sequence[SurfaceTemperatureState],
) -> tuple[list[list[int]], list[float], dict[float, list[float]]]:
    state_order = (
        "molten_extreme",
        "steamhouse_hot",
        "hot",
        "temperate",
        "cold",
        "frozen",
    )
    band_to_code = {name: index for index, name in enumerate(state_order)}
    latitudes = zonal_latitude_samples()
    heatmap = [[0 for _ in states] for _ in latitudes]
    profile_series = {latitude: [] for latitude in PROFILE_LATITUDES}

    for state_index, state in enumerate(states):
        for latitude_index, latitude in enumerate(latitudes):
            zonal_temperature = zonal_temperature_c_at(state, latitude)
            band = average_temperature_band_at(zonal_temperature)
            heatmap[latitude_index][state_index] = band_to_code[band]
        for latitude in PROFILE_LATITUDES:
            profile_series[latitude].append(float(zonal_temperature_c_at(state, latitude)))

    return heatmap, latitudes, profile_series


def write_zonal_temperature_bands_png(
    states: Sequence[SurfaceTemperatureState], current_file: str
) -> Path:
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        from matplotlib.colors import BoundaryNorm, ListedColormap
        from matplotlib.patches import Patch
    except ImportError as exc:  # pragma: no cover - import-time dependency guard
        raise ImportError(
            "Zonal temperature visualization requires matplotlib. Install "
            "dependencies with `python3 -m pip install -r requirements.txt`."
        ) from exc

    if not states:
        raise ValueError("Surface temperature visualization requires at least one state.")

    output_path = temperature_visualization_output_path(current_file)
    heatmap, latitudes, profile_series = zonal_temperature_band_heatmap(states)
    ages_myr = [
        float(Decimal(state.age_years) / planet.YEARS_PER_MYR) for state in states
    ]
    first_liquid_state = first_surface_liquids_state(states)
    first_liquid_age_myr = (
        float(Decimal(first_liquid_state.age_years) / planet.YEARS_PER_MYR)
        if first_liquid_state is not None
        else None
    )

    fig = plt.figure(figsize=(13.6, 9.8), facecolor="#f6f1e8")
    grid = fig.add_gridspec(2, 1, height_ratios=(1.0, 1.4), hspace=0.28)
    profile_ax = fig.add_subplot(grid[0, 0])
    heatmap_ax = fig.add_subplot(grid[1, 0])

    profile_ax.set_facecolor("#fffdf8")
    profile_colors = {0.0: "#d1495b", 45.0: "#edae49", 90.0: "#264653"}
    profile_labels = {0.0: "Equator", 45.0: "45°", 90.0: "Pole"}
    for latitude in PROFILE_LATITUDES:
        profile_ax.plot(
            ages_myr,
            profile_series[latitude],
            color=profile_colors[latitude],
            linewidth=2.4,
            label=profile_labels[latitude],
        )
    if first_liquid_age_myr is not None:
        profile_ax.axvline(
            first_liquid_age_myr,
            color="#1f2937",
            linewidth=1.2,
            linestyle="--",
            alpha=0.7,
        )
    profile_ax.set_xlim(ages_myr[0], ages_myr[-1])
    profile_ax.set_ylabel("Temperature (C)", color="#1f2937")
    profile_ax.set_title(
        "05 Surface Temperature: Zonal Thermal Bands",
        loc="left",
        color="#1f2937",
        fontsize=18,
        pad=14,
    )
    profile_ax.grid(True, axis="y", color="#d7d2c8", linewidth=0.8, alpha=0.8)
    for spine in profile_ax.spines.values():
        spine.set_color("#d7d2c8")
    profile_ax.tick_params(colors="#6b7280")
    profile_ax.legend(frameon=False, ncol=3, loc="upper right")

    band_order = (
        "molten_extreme",
        "steamhouse_hot",
        "hot",
        "temperate",
        "cold",
        "frozen",
    )
    cmap = ListedColormap([TEMPERATURE_BAND_COLORS[band] for band in band_order])
    norm = BoundaryNorm(
        [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5],
        cmap.N,
    )
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
    if first_liquid_age_myr is not None:
        heatmap_ax.axvline(
            first_liquid_age_myr,
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

    legend_handles = [
        Patch(color=TEMPERATURE_BAND_COLORS[band], label=TEMPERATURE_BAND_LABELS[band])
        for band in band_order
    ]
    fig.legend(
        handles=legend_handles,
        frameon=False,
        ncol=3,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.055),
    )

    fig.text(
        0.125,
        0.02,
        (
            "Zonal-only projection: local latitude bands are derived from the "
            "modeled mean surface temperature plus the simulated equator-to-pole "
            "contrast. No longitude-resolved surface geometry is implied at this layer."
        ),
        ha="left",
        va="bottom",
        fontsize=10,
        color="#6b7280",
    )
    fig.subplots_adjust(left=0.08, right=0.97, top=0.93, bottom=0.16, hspace=0.30)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output_path


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
        ("early_atmosphere_source", "04_early_atmosphere.py"),
        ("primary_crust_source", "03_primary_crust.py"),
        ("interior_source", "02_interior.py"),
        ("planet_source", "01_planet.py"),
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


def print_table(states: Sequence[SurfaceTemperatureState]) -> None:
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

    for state in states:
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


def print_present_day_summary(states: Sequence[SurfaceTemperatureState]) -> None:
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

    states = simulate(criteria)
    if not states:
        raise SystemExit("Surface temperature simulation produced no timestep states.")

    print_input_criteria(criteria)
    print_table(states)
    print_present_day_summary(states)

    try:
        write_zonal_temperature_bands_png(states, __file__)
    except (ImportError, OSError, ValueError) as exc:
        raise SystemExit(
            f"Failed to write zonal temperature visualization: {exc}"
        ) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
