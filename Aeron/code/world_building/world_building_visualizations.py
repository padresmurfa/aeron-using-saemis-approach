"""Matplotlib visualization support for ordered world-building layers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

try:
    from .world_building_paths import step_output_dir, step_output_path
except ImportError:
    from world_building_paths import step_output_dir, step_output_path  # type: ignore

try:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.patches import Patch
except ImportError as exc:  # pragma: no cover - import-time dependency guard
    raise ImportError(
        "Visualization support requires matplotlib. Install dependencies with "
        "`python3 -m pip install -r requirements.txt`."
    ) from exc


BACKGROUND = "#f6f1e8"
PANEL = "#fffdf8"
TEXT = "#1f2937"
MUTED = "#6b7280"
GRID = "#d7d2c8"
BAR_FILL = "#c46a2f"

PALETTE = (
    "#0f4c5c",
    "#e36414",
    "#6b8f71",
    "#7a5c61",
    "#4a6fa5",
    "#b56576",
    "#6d597a",
    "#8f5d2c",
    "#4d908e",
    "#bc4749",
    "#577590",
    "#9c6644",
)

Accessor = Callable[[Any], Any]


@dataclass(frozen=True)
class NumericSeriesSpec:
    label: str
    getter: Accessor
    color: str


@dataclass(frozen=True)
class LineChartSpec:
    suffix: str
    title: str
    y_label: str
    series: tuple[NumericSeriesSpec, ...]


@dataclass(frozen=True)
class StateRowSpec:
    label: str
    getter: Callable[[Any], str]


@dataclass(frozen=True)
class StateTimelineSpec:
    suffix: str
    title: str
    rows: tuple[StateRowSpec, ...]


@dataclass(frozen=True)
class BarChartSpec:
    suffix: str
    title: str
    value_label: str
    collection_getter: Callable[[Any], Iterable[Any]]
    label_getter: Callable[[Any], str]
    value_getter: Callable[[Any], Any]
    fill: str = BAR_FILL
    max_items: int = 8


VisualizationSpec = LineChartSpec | StateTimelineSpec | BarChartSpec


def pretty_label(value: str) -> str:
    return value.replace("_", " ").strip()


def numeric_value(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def age_myr(state: Any) -> float:
    return numeric_value(state.age_years) / 1_000_000.0


def visualizations_dir(current_file: str) -> Path:
    return step_output_dir(current_file)


def visualization_output_path(current_file: str, suffix: str) -> Path:
    return step_output_path(current_file, suffix, default_extension=".png")


def base_figure(figsize: tuple[float, float]) -> tuple[Any, Any]:
    fig, ax = plt.subplots(figsize=figsize, facecolor=BACKGROUND)
    ax.set_facecolor(PANEL)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.grid(True, axis="y", color=GRID, linewidth=0.8, alpha=0.8)
    return fig, ax


def save_figure(fig: Any, output_path: Path) -> None:
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def render_line_chart(output_path: Path, states: Sequence[Any], spec: LineChartSpec) -> None:
    fig, ax = base_figure((12.5, 7.5))
    ages = [age_myr(state) for state in states]

    for series in spec.series:
        values = [numeric_value(series.getter(state)) for state in states]
        ax.plot(
            ages,
            values,
            label=series.label,
            color=series.color,
            linewidth=2.4,
            marker="o",
            markersize=4.5,
        )

    ax.set_title(spec.title, loc="left", color=TEXT, fontsize=18, pad=14)
    ax.set_xlabel("Age (Myr)", color=TEXT)
    ax.set_ylabel(spec.y_label, color=TEXT)
    ax.legend(frameon=False, ncol=min(4, len(spec.series)), loc="best")
    save_figure(fig, output_path)


def age_bin_edges(states: Sequence[Any]) -> list[float]:
    ages = [age_myr(state) for state in states]
    if len(ages) == 1:
        return [ages[0] - 0.5, ages[0] + 0.5]

    midpoints = [(ages[index] + ages[index + 1]) / 2 for index in range(len(ages) - 1)]
    first_edge = ages[0] - (midpoints[0] - ages[0])
    last_edge = ages[-1] + (ages[-1] - midpoints[-1])
    return [first_edge, *midpoints, last_edge]


def state_runs(values: Sequence[str]) -> list[tuple[int, int, str]]:
    runs: list[tuple[int, int, str]] = []
    if not values:
        return runs

    start = 0
    current = values[0]
    for index, value in enumerate(values[1:], start=1):
        if value != current:
            runs.append((start, index - 1, current))
            start = index
            current = value
    runs.append((start, len(values) - 1, current))
    return runs


def render_state_timeline(
    output_path: Path, states: Sequence[Any], spec: StateTimelineSpec
) -> None:
    fig_height = max(4.8, 1.3 * len(spec.rows) + 2.6)
    fig, ax = base_figure((12.5, fig_height))
    ax.grid(True, axis="x", color=GRID, linewidth=0.8, alpha=0.8)
    ax.grid(False, axis="y")

    edges = age_bin_edges(states)
    legend_values: list[str] = []
    row_values: list[list[str]] = []
    for row in spec.rows:
        values = [pretty_label(str(row.getter(state))) for state in states]
        row_values.append(values)
        for value in values:
            if value not in legend_values:
                legend_values.append(value)

    color_map = {
        value: PALETTE[index % len(PALETTE)] for index, value in enumerate(legend_values)
    }

    y_positions = list(range(len(spec.rows)))[::-1]
    for y_pos, row, values in zip(y_positions, spec.rows, row_values):
        for start, end, value in state_runs(values):
            left = edges[start]
            width = edges[end + 1] - edges[start]
            ax.broken_barh(
                [(left, width)],
                (y_pos - 0.38, 0.76),
                facecolors=color_map[value],
                edgecolors=PANEL,
                linewidth=1.2,
            )

    ax.set_title(spec.title, loc="left", color=TEXT, fontsize=18, pad=14)
    ax.set_xlabel("Age (Myr)", color=TEXT)
    ax.set_yticks(y_positions)
    ax.set_yticklabels([row.label for row in spec.rows], color=TEXT)
    ax.set_ylim(-0.7, len(spec.rows) - 0.3)
    ax.set_xlim(edges[0], edges[-1])

    handles = [Patch(color=color_map[value], label=value) for value in legend_values]
    ax.legend(
        handles=handles,
        frameon=False,
        ncol=min(3, max(1, len(handles))),
        loc="upper left",
        bbox_to_anchor=(0, -0.16),
    )
    save_figure(fig, output_path)


def render_bar_chart(output_path: Path, states: Sequence[Any], spec: BarChartSpec) -> None:
    items = list(spec.collection_getter(states[-1]))
    ranked_items = sorted(
        items,
        key=lambda item: numeric_value(spec.value_getter(item)),
        reverse=True,
    )[: spec.max_items]
    labels = [pretty_label(str(spec.label_getter(item))) for item in ranked_items]
    values = [numeric_value(spec.value_getter(item)) for item in ranked_items]

    fig_height = max(4.5, 1.0 * len(labels) + 2.4)
    fig, ax = base_figure((12.5, fig_height))
    ax.grid(True, axis="x", color=GRID, linewidth=0.8, alpha=0.8)
    ax.grid(False, axis="y")

    y_positions = list(range(len(labels)))[::-1]
    ax.barh(y_positions, values, color=spec.fill, edgecolor=PANEL, height=0.72)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, color=TEXT)
    ax.set_xlabel(spec.value_label, color=TEXT)
    ax.set_title(spec.title, loc="left", color=TEXT, fontsize=18, pad=14)

    max_value = max(values, default=0.0)
    offset = max(max_value * 0.015, 0.02)
    for y_pos, value in zip(y_positions, values):
        ax.text(value + offset, y_pos, f"{value:.3f}", va="center", ha="left", color=TEXT)

    save_figure(fig, output_path)


def active_plate_state_label(state: Any) -> str:
    return "active plates present" if state.active_plate_count > 0 else "no active plates"


def crust_balance_state_label(state: Any) -> str:
    if numeric_value(state.net_crust_balance_km2_per_yr) > 0:
        return "net crust growth"
    if numeric_value(state.net_crust_balance_km2_per_yr) < 0:
        return "net crust loss"
    return "crust balance neutral"


DEFAULT_VISUALIZATION_SPECS: dict[str, tuple[VisualizationSpec, ...]] = {
    "01_planet": (
        LineChartSpec(
            suffix="growth",
            title="01 Planet: Bulk Growth Toward Present-Day Scale",
            y_label="fraction of present-day scale",
            series=(
                NumericSeriesSpec("mass", lambda state: state.mass_earth, "#0f4c5c"),
                NumericSeriesSpec(
                    "radius",
                    lambda state: numeric_value(state.radius_km) / 6371.0,
                    "#e36414",
                ),
                NumericSeriesSpec(
                    "crust thickness",
                    lambda state: numeric_value(state.crust_thickness_km) / 35.0,
                    "#6b8f71",
                ),
                NumericSeriesSpec(
                    "internal heat",
                    lambda state: numeric_value(state.internal_heat_tw) / 47.0,
                    "#7a5c61",
                ),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="01 Planet: Structural And Retention State Timeline",
            rows=(
                StateRowSpec("core", lambda state: state.core_state),
                StateRowSpec("mantle", lambda state: state.mantle_state),
                StateRowSpec("crust", lambda state: state.crust_state),
                StateRowSpec("magnetic field", lambda state: state.magnetic_field),
                StateRowSpec(
                    "atmosphere retention", lambda state: state.atmosphere_retention
                ),
            ),
        ),
    ),
    "02_interior": (
        LineChartSpec(
            suffix="heat_budget",
            title="02 Interior: Heat Budget Evolution",
            y_label="heat (TW)",
            series=(
                NumericSeriesSpec("total", lambda state: state.total_internal_heat_tw, "#0f4c5c"),
                NumericSeriesSpec("residual", lambda state: state.residual_heat_tw, "#e36414"),
                NumericSeriesSpec("radiogenic", lambda state: state.radiogenic_heat_tw, "#6b8f71"),
                NumericSeriesSpec("tidal", lambda state: state.tidal_heat_tw, "#7a5c61"),
            ),
        ),
        LineChartSpec(
            suffix="structure",
            title="02 Interior: Structural Progress Indices",
            y_label="fraction / index",
            series=(
                NumericSeriesSpec("solid fraction", lambda state: state.solid_fraction, "#0f4c5c"),
                NumericSeriesSpec("core formation", lambda state: state.core_formation_fraction, "#e36414"),
                NumericSeriesSpec("mantle formation", lambda state: state.mantle_formation_fraction, "#6b8f71"),
                NumericSeriesSpec("primordial crust", lambda state: state.primordial_crust_fraction, "#7a5c61"),
                NumericSeriesSpec("convection", lambda state: state.convection_index, "#4a6fa5"),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="02 Interior: Thermal State Timeline",
            rows=(
                StateRowSpec("solidification", lambda state: state.solidification_state),
                StateRowSpec("convection", lambda state: state.convection_state),
                StateRowSpec("tectonic readiness", lambda state: state.tectonic_readiness),
            ),
        ),
    ),
    "03_primary_crust": (
        LineChartSpec(
            suffix="thickness",
            title="03 Primary Crust: Gross Versus Stable Crust Thickness",
            y_label="thickness (km)",
            series=(
                NumericSeriesSpec("gross crust", lambda state: state.gross_crust_thickness_km, "#0f4c5c"),
                NumericSeriesSpec("stable crust", lambda state: state.stable_crust_thickness_km, "#e36414"),
            ),
        ),
        LineChartSpec(
            suffix="readiness",
            title="03 Primary Crust: Surface Stabilization Signals",
            y_label="fraction / index",
            series=(
                NumericSeriesSpec("stable crust fraction", lambda state: state.stable_crust_fraction, "#0f4c5c"),
                NumericSeriesSpec("weak zone fraction", lambda state: state.weak_zone_fraction, "#e36414"),
                NumericSeriesSpec("surface solid index", lambda state: state.surface_solid_index, "#6b8f71"),
                NumericSeriesSpec("convection index", lambda state: state.convection_index, "#7a5c61"),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="03 Primary Crust: Crust Regime Timeline",
            rows=(
                StateRowSpec("stable crust state", lambda state: state.stable_crust_state),
                StateRowSpec("crust regime", lambda state: state.crust_regime),
                StateRowSpec("weak zone pattern", lambda state: state.weak_zone_pattern),
                StateRowSpec("surface state", lambda state: state.surface_state),
            ),
        ),
    ),
    "04_early_atmosphere": (
        LineChartSpec(
            suffix="indices",
            title="04 Early Atmosphere: Volatile Balance Indices",
            y_label="index / fraction",
            series=(
                NumericSeriesSpec("outgassing", lambda state: state.outgassing_index, "#0f4c5c"),
                NumericSeriesSpec("gas loss", lambda state: state.gas_loss_index, "#e36414"),
                NumericSeriesSpec("greenhouse", lambda state: state.greenhouse_index, "#6b8f71"),
                NumericSeriesSpec("stable crust fraction", lambda state: state.stable_crust_fraction, "#7a5c61"),
            ),
        ),
        LineChartSpec(
            suffix="pressure_flux",
            title="04 Early Atmosphere: Pressure And Flux History",
            y_label="bar or bar per Gyr",
            series=(
                NumericSeriesSpec("pressure", lambda state: state.atmospheric_pressure_bar, "#0f4c5c"),
                NumericSeriesSpec(
                    "outgassing flux",
                    lambda state: state.outgassing_flux_bar_per_gyr,
                    "#e36414",
                ),
                NumericSeriesSpec(
                    "loss flux",
                    lambda state: state.gas_loss_flux_bar_per_gyr,
                    "#6b8f71",
                ),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="04 Early Atmosphere: Surface Envelope Timeline",
            rows=(
                StateRowSpec("retention", lambda state: state.retention_potential),
                StateRowSpec("composition", lambda state: state.atmospheric_composition),
                StateRowSpec("precipitation", lambda state: state.precipitation_state),
                StateRowSpec("surface environment", lambda state: state.surface_environment),
            ),
        ),
    ),
    "05_surface_temperature": (
        LineChartSpec(
            suffix="temperature",
            title="05 Surface Temperature: Thermal Regime History",
            y_label="temperature delta or amplitude (C)",
            series=(
                NumericSeriesSpec("mean temperature", lambda state: state.mean_surface_temp_c, "#0f4c5c"),
                NumericSeriesSpec("equator-pole delta", lambda state: state.equator_to_pole_delta_c, "#e36414"),
                NumericSeriesSpec(
                    "thermal cycling amplitude",
                    lambda state: state.thermal_cycling_amplitude_c,
                    "#6b8f71",
                ),
            ),
        ),
        LineChartSpec(
            suffix="controls",
            title="05 Surface Temperature: Coupled Surface Controls",
            y_label="pressure or index",
            series=(
                NumericSeriesSpec("pressure", lambda state: state.atmospheric_pressure_bar, "#0f4c5c"),
                NumericSeriesSpec("greenhouse", lambda state: state.greenhouse_index, "#e36414"),
                NumericSeriesSpec("stable crust fraction", lambda state: state.stable_crust_fraction, "#6b8f71"),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="05 Surface Temperature: Surface State Timeline",
            rows=(
                StateRowSpec("temperature band", lambda state: state.average_temperature_band),
                StateRowSpec("surface liquids", lambda state: state.surface_liquid_state),
                StateRowSpec("crust stability", lambda state: state.crust_stability_state),
                StateRowSpec("thermal regime", lambda state: state.surface_temperature_regime),
            ),
        ),
    ),
    "06_proto_tectonics": (
        LineChartSpec(
            suffix="indices",
            title="06 Proto-Tectonics: Fracture And Mobility Indices",
            y_label="index / fraction",
            series=(
                NumericSeriesSpec("rigidity", lambda state: state.lithosphere_rigidity_index, "#0f4c5c"),
                NumericSeriesSpec("fracture potential", lambda state: state.fracture_potential_index, "#e36414"),
                NumericSeriesSpec("plate mobility", lambda state: state.plate_mobility_index, "#6b8f71"),
                NumericSeriesSpec("stable crust fraction", lambda state: state.stable_crust_fraction, "#7a5c61"),
            ),
        ),
        LineChartSpec(
            suffix="surface_inputs",
            title="06 Proto-Tectonics: Surface Inputs To Fracture Behavior",
            y_label="temperature, amplitude, or fraction",
            series=(
                NumericSeriesSpec("mean surface temp", lambda state: state.mean_surface_temp_c, "#0f4c5c"),
                NumericSeriesSpec(
                    "thermal cycling amplitude",
                    lambda state: state.thermal_cycling_amplitude_c,
                    "#e36414",
                ),
                NumericSeriesSpec("stable crust fraction", lambda state: state.stable_crust_fraction, "#6b8f71"),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="06 Proto-Tectonics: Regime Transition Timeline",
            rows=(
                StateRowSpec("fracture capable", lambda state: state.rigid_enough_to_fracture),
                StateRowSpec("plates exist", lambda state: state.plates_exist),
                StateRowSpec("tectonic regime", lambda state: state.tectonic_regime),
                StateRowSpec("fracture belts", lambda state: state.major_fracture_zones),
                StateRowSpec("spreading pattern", lambda state: state.spreading_zones),
                StateRowSpec("recycling pattern", lambda state: state.recycling_zones),
                StateRowSpec("crust stability", lambda state: state.crust_stability_state),
            ),
        ),
    ),
    "07_plate_system": (
        LineChartSpec(
            suffix="kinematics",
            title="07 Plate System: Plate Motion And Boundary Rates",
            y_label="cm per year",
            series=(
                NumericSeriesSpec("mean speed", lambda state: state.mean_plate_speed_cm_per_yr, "#0f4c5c"),
                NumericSeriesSpec("spreading", lambda state: state.spreading_rate_cm_per_yr, "#e36414"),
                NumericSeriesSpec("collision", lambda state: state.collision_rate_cm_per_yr, "#6b8f71"),
                NumericSeriesSpec("recycling", lambda state: state.recycling_rate_cm_per_yr, "#7a5c61"),
                NumericSeriesSpec("transform", lambda state: state.transform_rate_cm_per_yr, "#4a6fa5"),
            ),
        ),
        LineChartSpec(
            suffix="crust_budget",
            title="07 Plate System: Crust Creation And Destruction Budget",
            y_label="km2 per year",
            series=(
                NumericSeriesSpec("creation", lambda state: state.crust_creation_rate_km2_per_yr, "#0f4c5c"),
                NumericSeriesSpec("destruction", lambda state: state.crust_destruction_rate_km2_per_yr, "#e36414"),
                NumericSeriesSpec("net balance", lambda state: state.net_crust_balance_km2_per_yr, "#6b8f71"),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="07 Plate System: Plate Activity Timeline",
            rows=(
                StateRowSpec("tectonic regime", lambda state: state.tectonic_regime),
                StateRowSpec("plate activity", active_plate_state_label),
                StateRowSpec("crust balance", crust_balance_state_label),
            ),
        ),
        BarChartSpec(
            suffix="regions",
            title="07 Plate System: Present-Day Plate Region Speeds",
            value_label="speed (cm per year)",
            collection_getter=lambda state: state.plate_regions,
            label_getter=lambda region: region.region_id,
            value_getter=lambda region: region.speed_cm_per_yr,
            fill="#8f5d2c",
        ),
    ),
    "08_large_scale_topography": (
        LineChartSpec(
            suffix="coverage",
            title="08 Topography: Proto-Continent And Basin Coverage",
            y_label="area fraction",
            series=(
                NumericSeriesSpec("proto-continent", lambda state: state.proto_continent_fraction, "#0f4c5c"),
                NumericSeriesSpec("ocean basin", lambda state: state.ocean_basin_fraction, "#e36414"),
            ),
        ),
        LineChartSpec(
            suffix="relief",
            title="08 Topography: First-Order Relief Evolution",
            y_label="relief or depth (m)",
            series=(
                NumericSeriesSpec("highest relief", lambda state: state.highest_relief_m, "#0f4c5c"),
                NumericSeriesSpec("deepest basin", lambda state: state.deepest_basin_m, "#e36414"),
                NumericSeriesSpec("relief contrast", lambda state: state.relief_contrast_m, "#6b8f71"),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="08 Topography: Relief Regime Timeline",
            rows=(
                StateRowSpec("tectonic regime", lambda state: state.tectonic_regime),
                StateRowSpec("topography state", lambda state: state.topography_state),
            ),
        ),
        BarChartSpec(
            suffix="features",
            title="08 Topography: Present-Day Feature Footprints",
            value_label="area fraction",
            collection_getter=lambda state: state.features,
            label_getter=lambda feature: feature.feature_id,
            value_getter=lambda feature: feature.area_fraction,
            fill="#4d908e",
        ),
    ),
    "09_volcanic_impact_resurfacing": (
        LineChartSpec(
            suffix="activity",
            title="09 Resurfacing: Volcanic And Crater Activity Signals",
            y_label="count, fraction, or index",
            series=(
                NumericSeriesSpec("hotspots", lambda state: state.hotspot_count, "#0f4c5c"),
                NumericSeriesSpec("hotspot activity", lambda state: state.hotspot_activity_index, "#e36414"),
                NumericSeriesSpec("flood basalt intensity", lambda state: state.flood_basalt_intensity_index, "#6b8f71"),
                NumericSeriesSpec("crater persistence", lambda state: state.crater_persistence_fraction, "#7a5c61"),
            ),
        ),
        LineChartSpec(
            suffix="surface_age",
            title="09 Resurfacing: Surface Reworking And Preservation",
            y_label="fraction or rate",
            series=(
                NumericSeriesSpec("volcanic province fraction", lambda state: state.volcanic_province_fraction, "#0f4c5c"),
                NumericSeriesSpec("resurfacing fraction per Gyr", lambda state: state.resurfacing_fraction_per_gyr, "#e36414"),
                NumericSeriesSpec("old crust survival", lambda state: state.old_crust_survival_fraction, "#6b8f71"),
                NumericSeriesSpec("crater rate per Gyr", lambda state: state.major_crater_rate_per_gyr, "#7a5c61"),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="09 Resurfacing: Surface Scar Timeline",
            rows=(
                StateRowSpec("tectonic regime", lambda state: state.tectonic_regime),
                StateRowSpec("scar state", lambda state: state.scar_state),
            ),
        ),
        BarChartSpec(
            suffix="features",
            title="09 Resurfacing: Present-Day Resurfacing Provinces",
            value_label="area fraction",
            collection_getter=lambda state: state.features,
            label_getter=lambda feature: feature.feature_id,
            value_getter=lambda feature: feature.area_fraction,
            fill="#bc4749",
        ),
    ),
    "10_basic_regolith_weathering": (
        LineChartSpec(
            suffix="indices",
            title="10 Regolith: Weathering And Dust Indices",
            y_label="index",
            series=(
                NumericSeriesSpec("rock fracture", lambda state: state.rock_fracture_index, "#0f4c5c"),
                NumericSeriesSpec("dust generation", lambda state: state.dust_generation_index, "#e36414"),
                NumericSeriesSpec("chemical weathering", lambda state: state.chemical_weathering_index, "#6b8f71"),
            ),
        ),
        LineChartSpec(
            suffix="cover",
            title="10 Regolith: Surface Cover Fractions",
            y_label="fraction",
            series=(
                NumericSeriesSpec("talus", lambda state: state.talus_accumulation_fraction, "#0f4c5c"),
                NumericSeriesSpec("sediment", lambda state: state.sediment_accumulation_fraction, "#e36414"),
                NumericSeriesSpec("regolith coverage", lambda state: state.regolith_coverage_fraction, "#6b8f71"),
                NumericSeriesSpec("exposed bedrock", lambda state: state.exposed_bedrock_fraction, "#7a5c61"),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="10 Regolith: Surface Texture Timeline",
            rows=(
                StateRowSpec("surface environment", lambda state: state.surface_environment),
                StateRowSpec("thermal regime", lambda state: state.surface_temperature_regime),
                StateRowSpec("tectonic regime", lambda state: state.tectonic_regime),
                StateRowSpec("texture state", lambda state: state.texture_state),
            ),
        ),
        BarChartSpec(
            suffix="features",
            title="10 Regolith: Present-Day Terrain Mantling",
            value_label="regolith fraction",
            collection_getter=lambda state: state.features,
            label_getter=lambda feature: feature.feature_id,
            value_getter=lambda feature: feature.regolith_fraction,
            fill="#9c6644",
        ),
    ),
    "11_hydrology_before_life": (
        LineChartSpec(
            suffix="water",
            title="11 Hydrology: Water And Ice Partitioning",
            y_label="fraction",
            series=(
                NumericSeriesSpec("stable oceans", lambda state: state.stable_ocean_fraction, "#0f4c5c"),
                NumericSeriesSpec("inland seas", lambda state: state.inland_sea_fraction, "#e36414"),
                NumericSeriesSpec("glaciers", lambda state: state.glacier_fraction, "#6b8f71"),
                NumericSeriesSpec("basin filling", lambda state: state.basin_filling_fraction, "#7a5c61"),
            ),
        ),
        LineChartSpec(
            suffix="counts",
            title="11 Hydrology: Organized Hydrology Counts",
            y_label="count",
            series=(
                NumericSeriesSpec("glacier zones", lambda state: state.glacier_zone_count, "#0f4c5c"),
                NumericSeriesSpec("runoff pathways", lambda state: state.runoff_pathway_count, "#e36414"),
            ),
        ),
        StateTimelineSpec(
            suffix="states",
            title="11 Hydrology: Prebiotic Hydrology Timeline",
            rows=(
                StateRowSpec("surface environment", lambda state: state.surface_environment),
                StateRowSpec("thermal regime", lambda state: state.surface_temperature_regime),
                StateRowSpec("tectonic regime", lambda state: state.tectonic_regime),
                StateRowSpec("hydrology state", lambda state: state.hydrology_state),
            ),
        ),
        BarChartSpec(
            suffix="features",
            title="11 Hydrology: Present-Day Hydrologic Feature Footprints",
            value_label="area fraction",
            collection_getter=lambda state: state.features,
            label_getter=lambda feature: feature.feature_id,
            value_getter=lambda feature: feature.area_fraction,
            fill="#4a6fa5",
        ),
    ),
}


def write_default_layer_visualizations(
    current_file: str, states: Sequence[Any]
) -> list[Path]:
    stem = Path(current_file).stem
    specs = DEFAULT_VISUALIZATION_SPECS.get(stem, ())
    paths: list[Path] = []
    for spec in specs:
        output_path = visualization_output_path(current_file, spec.suffix)
        if isinstance(spec, LineChartSpec):
            render_line_chart(output_path, states, spec)
        elif isinstance(spec, StateTimelineSpec):
            render_state_timeline(output_path, states, spec)
        else:
            render_bar_chart(output_path, states, spec)
        paths.append(output_path)
    return paths
