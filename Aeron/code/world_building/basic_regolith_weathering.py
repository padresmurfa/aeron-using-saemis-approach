#!/usr/bin/env python3
"""Deterministic basic regolith and weathering simulation for Aeron."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Iterable

try:
    from . import early_atmosphere, planet, surface_temperature, volcanic_impact_resurfacing
except ImportError:
    import early_atmosphere  # type: ignore
    import planet  # type: ignore
    import surface_temperature  # type: ignore
    import volcanic_impact_resurfacing  # type: ignore

getcontext().prec = 50

VALIDATION_STEP_YEARS = 100_000_000


@dataclass(frozen=True)
class RegolithFeatureState:
    feature_id: str
    source_feature_id: str
    source_feature_type: str
    terrain_state: str
    fracture_index: Decimal
    dust_index: Decimal
    chemical_weathering_index: Decimal
    talus_sediment_fraction: Decimal
    regolith_fraction: Decimal
    regolith_thickness_m: Decimal


@dataclass(frozen=True)
class BasicRegolithWeatheringState:
    step_index: int
    age_years: int
    radius_km: Decimal
    surface_environment: str
    surface_temperature_regime: str
    tectonic_regime: str
    rock_fracture_index: Decimal
    dust_generation_index: Decimal
    chemical_weathering_index: Decimal
    talus_accumulation_fraction: Decimal
    sediment_accumulation_fraction: Decimal
    regolith_coverage_fraction: Decimal
    mean_regolith_thickness_m: Decimal
    exposed_bedrock_fraction: Decimal
    texture_state: str
    feature_count: int
    features: tuple[RegolithFeatureState, ...]
    world_class: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate Aeron's basic regolith and weathering layer by ticking the "
            "volcanic-and-impact resurfacing layer and deriving coarse barren-surface "
            "texture from it."
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


def pressure_factor_at(atmospheric_pressure_bar: Decimal) -> Decimal:
    return clamp_unit_interval(atmospheric_pressure_bar / Decimal("1.20"))


def solid_surface_factor_at(surface_environment: str) -> Decimal:
    if surface_environment == "lava":
        return Decimal("0.12")
    if surface_environment == "steam":
        return Decimal("0.45")
    return Decimal("1.0")


def surface_liquid_support_at(surface_liquid_state: str) -> Decimal:
    if surface_liquid_state == "stable":
        return Decimal("1.0")
    if surface_liquid_state == "transient":
        return Decimal("0.55")
    if surface_liquid_state == "frozen":
        return Decimal("0.20")
    return Decimal("0.0")


def moisture_factor_at(
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
) -> Decimal:
    liquid_support = surface_liquid_support_at(temperature_state.surface_liquid_state)
    if atmosphere_state.precipitation_state == "established":
        return liquid_support
    if atmosphere_state.precipitation_state == "possible":
        return clamp_unit_interval((Decimal("0.75") * liquid_support) + Decimal("0.10"))
    if atmosphere_state.precipitation_state == "transient":
        return clamp_unit_interval((Decimal("0.35") * liquid_support) + Decimal("0.05"))
    return Decimal("0.0")


def temperature_reaction_factor_at(mean_surface_temp_c: Decimal) -> Decimal:
    if mean_surface_temp_c <= Decimal("-15"):
        return Decimal("0.08")
    if mean_surface_temp_c <= Decimal("0"):
        return Decimal("0.18")
    if mean_surface_temp_c <= Decimal("45"):
        return Decimal("1.0")
    if mean_surface_temp_c <= Decimal("80"):
        return Decimal("0.55")
    if mean_surface_temp_c <= Decimal("140"):
        return Decimal("0.18")
    return Decimal("0.05")


def aeolian_transport_factor_at(
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
) -> Decimal:
    pressure = pressure_factor_at(atmosphere_state.atmospheric_pressure_bar)
    if atmosphere_state.surface_environment == "dry_rock":
        modifier = Decimal("1.0")
    elif atmosphere_state.surface_environment == "wet_rock":
        modifier = Decimal("0.72")
    elif atmosphere_state.surface_environment == "ice":
        modifier = Decimal("0.45")
    elif atmosphere_state.surface_environment == "steam":
        modifier = Decimal("0.25")
    elif atmosphere_state.surface_environment == "lava":
        modifier = Decimal("0.05")
    else:
        modifier = Decimal("0.35")
    return clamp_unit_interval(pressure * modifier)


def thermal_cycling_factor_at(
    temperature_state: surface_temperature.SurfaceTemperatureState,
) -> Decimal:
    return clamp_unit_interval(
        temperature_state.thermal_cycling_amplitude_c / Decimal("45")
    )


def impact_fracture_factor_at(
    resurfacing_state: volcanic_impact_resurfacing.VolcanicImpactResurfacingState,
) -> Decimal:
    return clamp_unit_interval(
        resurfacing_state.major_crater_rate_per_gyr / Decimal("22")
    )


def volcanic_reworking_factor_at(
    resurfacing_state: volcanic_impact_resurfacing.VolcanicImpactResurfacingState,
) -> Decimal:
    return clamp_unit_interval(
        resurfacing_state.volcanic_province_fraction / Decimal("0.16")
    )


def relief_memory_factor_at(
    resurfacing_state: volcanic_impact_resurfacing.VolcanicImpactResurfacingState,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.45") * resurfacing_state.crater_persistence_fraction)
        + (Decimal("0.35") * volcanic_reworking_factor_at(resurfacing_state))
        + (Decimal("0.20") * resurfacing_state.old_crust_survival_fraction)
    )


def weathering_environment_modifier_at(surface_environment: str) -> Decimal:
    if surface_environment == "wet_rock":
        return Decimal("1.0")
    if surface_environment == "dry_rock":
        return Decimal("0.45")
    if surface_environment == "ice":
        return Decimal("0.20")
    if surface_environment == "steam":
        return Decimal("0.08")
    return Decimal("0.0")


def rock_fracture_index_at(
    resurfacing_state: volcanic_impact_resurfacing.VolcanicImpactResurfacingState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
) -> Decimal:
    return clamp_unit_interval(
        solid_surface_factor_at(temperature_state.surface_environment)
        * (
            (Decimal("0.35") * thermal_cycling_factor_at(temperature_state))
            + (Decimal("0.25") * impact_fracture_factor_at(resurfacing_state))
            + (Decimal("0.20") * volcanic_reworking_factor_at(resurfacing_state))
            + (Decimal("0.20") * resurfacing_state.old_crust_survival_fraction)
        )
    )


def dust_generation_index_at(
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
    resurfacing_state: volcanic_impact_resurfacing.VolcanicImpactResurfacingState,
    rock_fracture_index: Decimal,
) -> Decimal:
    dryness = Decimal("1") - moisture_factor_at(atmosphere_state, temperature_state)
    return clamp_unit_interval(
        solid_surface_factor_at(temperature_state.surface_environment)
        * (
            (Decimal("0.35") * rock_fracture_index)
            + (Decimal("0.25") * resurfacing_state.crater_persistence_fraction)
            + (Decimal("0.20") * aeolian_transport_factor_at(atmosphere_state))
            + (Decimal("0.20") * dryness)
        )
    )


def chemical_weathering_index_at(
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
    rock_fracture_index: Decimal,
) -> Decimal:
    environment_modifier = weathering_environment_modifier_at(
        atmosphere_state.surface_environment
    )
    if environment_modifier == Decimal("0"):
        return Decimal("0")
    return clamp_unit_interval(
        environment_modifier
        * (
            (Decimal("0.35") * moisture_factor_at(atmosphere_state, temperature_state))
            + (Decimal("0.25") * rock_fracture_index)
            + (Decimal("0.20") * pressure_factor_at(atmosphere_state.atmospheric_pressure_bar))
            + (
                Decimal("0.20")
                * temperature_reaction_factor_at(temperature_state.mean_surface_temp_c)
            )
        )
    )


def talus_accumulation_fraction_at(
    temperature_state: surface_temperature.SurfaceTemperatureState,
    resurfacing_state: volcanic_impact_resurfacing.VolcanicImpactResurfacingState,
    rock_fracture_index: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.40") * rock_fracture_index)
        + (Decimal("0.25") * relief_memory_factor_at(resurfacing_state))
        + (Decimal("0.20") * resurfacing_state.old_crust_survival_fraction)
        + (
            Decimal("0.15")
            * surface_liquid_support_at(temperature_state.surface_liquid_state)
        )
    )


def sediment_accumulation_fraction_at(
    dust_generation_index: Decimal,
    chemical_weathering_index: Decimal,
    talus_accumulation_fraction: Decimal,
    crater_persistence_fraction: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        (Decimal("0.40") * dust_generation_index)
        + (Decimal("0.30") * chemical_weathering_index)
        + (Decimal("0.20") * talus_accumulation_fraction)
        + (Decimal("0.10") * crater_persistence_fraction)
    )


def regolith_coverage_fraction_at(
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    rock_fracture_index: Decimal,
    dust_generation_index: Decimal,
    chemical_weathering_index: Decimal,
    talus_accumulation_fraction: Decimal,
    sediment_accumulation_fraction: Decimal,
) -> Decimal:
    return clamp_unit_interval(
        solid_surface_factor_at(atmosphere_state.surface_environment)
        * (
            (Decimal("0.30") * rock_fracture_index)
            + (Decimal("0.25") * dust_generation_index)
            + (Decimal("0.20") * chemical_weathering_index)
            + (Decimal("0.15") * talus_accumulation_fraction)
            + (Decimal("0.10") * sediment_accumulation_fraction)
        )
    )


def mean_regolith_thickness_m_at(
    regolith_coverage_fraction: Decimal,
    dust_generation_index: Decimal,
    chemical_weathering_index: Decimal,
    talus_accumulation_fraction: Decimal,
    sediment_accumulation_fraction: Decimal,
) -> Decimal:
    accumulation_index = clamp_unit_interval(
        (Decimal("0.35") * dust_generation_index)
        + (Decimal("0.30") * talus_accumulation_fraction)
        + (Decimal("0.20") * sediment_accumulation_fraction)
        + (Decimal("0.15") * chemical_weathering_index)
    )
    return Decimal("0.03") + (
        Decimal("4.20") * regolith_coverage_fraction * accumulation_index
    )


def exposed_bedrock_fraction_at(
    regolith_coverage_fraction: Decimal,
    resurfacing_state: volcanic_impact_resurfacing.VolcanicImpactResurfacingState,
) -> Decimal:
    resurfacing_exposure = clamp_unit_interval(
        resurfacing_state.resurfacing_fraction_per_gyr / Decimal("1.60")
    )
    return clamp_unit_interval(
        (Decimal("1") - regolith_coverage_fraction)
        + (Decimal("0.15") * resurfacing_exposure)
    )


def texture_state_at(
    surface_environment: str,
    rock_fracture_index: Decimal,
    dust_generation_index: Decimal,
    chemical_weathering_index: Decimal,
    talus_accumulation_fraction: Decimal,
    sediment_accumulation_fraction: Decimal,
    regolith_coverage_fraction: Decimal,
) -> str:
    if surface_environment == "lava":
        return "pristine_magmatic_surface"
    if regolith_coverage_fraction < Decimal("0.20"):
        return "fractured_bare_rock"
    if (
        chemical_weathering_index >= Decimal("0.40")
        and regolith_coverage_fraction >= Decimal("0.45")
    ):
        return "weathered_regolith_barrens"
    if (
        talus_accumulation_fraction >= Decimal("0.48")
        and rock_fracture_index >= Decimal("0.50")
    ):
        return "rubble_talus_barrens"
    if (
        dust_generation_index >= Decimal("0.55")
        and sediment_accumulation_fraction >= Decimal("0.45")
    ):
        return "dust_mantled_barrens"
    if dust_generation_index >= Decimal("0.40"):
        return "scarred_dusty_barrens"
    return "thin_regolith_scars"


def feature_area_support_at(area_fraction: Decimal) -> Decimal:
    return clamp_unit_interval(area_fraction / Decimal("0.06"))


def feature_fracture_index_at(
    feature: volcanic_impact_resurfacing.ResurfacingFeatureState,
    rock_fracture_index: Decimal,
) -> Decimal:
    local_support = feature_area_support_at(feature.area_fraction)
    base = rock_fracture_index * (Decimal("0.65") + (Decimal("0.35") * local_support))
    if feature.feature_type == "crater_field":
        base += Decimal("0.10") * feature.preserved_fraction
    else:
        base += Decimal("0.10") * feature.activity_index
    return clamp_unit_interval(base)


def feature_dust_index_at(
    feature: volcanic_impact_resurfacing.ResurfacingFeatureState,
    dust_generation_index: Decimal,
) -> Decimal:
    local_support = feature_area_support_at(feature.area_fraction)
    base = dust_generation_index * (Decimal("0.65") + (Decimal("0.35") * local_support))
    if feature.feature_type == "crater_field":
        base += Decimal("0.12") * feature.preserved_fraction
    elif feature.feature_type == "flood_basalt_province":
        base += Decimal("0.08") * feature.activity_index
    return clamp_unit_interval(base)


def feature_chemical_weathering_index_at(
    feature: volcanic_impact_resurfacing.ResurfacingFeatureState,
    chemical_weathering_index: Decimal,
) -> Decimal:
    local_support = feature_area_support_at(feature.area_fraction)
    if feature.feature_type == "flood_basalt_province":
        modifier = Decimal("1.10")
    elif feature.feature_type == "crater_field":
        modifier = Decimal("0.85")
    else:
        modifier = Decimal("1.0")
    return clamp_unit_interval(
        chemical_weathering_index * modifier * (Decimal("0.70") + (Decimal("0.30") * local_support))
    )


def feature_talus_sediment_fraction_at(
    feature: volcanic_impact_resurfacing.ResurfacingFeatureState,
    talus_accumulation_fraction: Decimal,
    sediment_accumulation_fraction: Decimal,
) -> Decimal:
    local_support = feature_area_support_at(feature.area_fraction)
    combined = (Decimal("0.55") * talus_accumulation_fraction) + (
        Decimal("0.45") * sediment_accumulation_fraction
    )
    if feature.feature_type == "volcanic_province":
        combined += Decimal("0.08") * feature.activity_index
    if feature.feature_type == "crater_field":
        combined += Decimal("0.06") * feature.preserved_fraction
    return clamp_unit_interval(combined * (Decimal("0.70") + (Decimal("0.30") * local_support)))


def feature_regolith_fraction_at(
    feature: volcanic_impact_resurfacing.ResurfacingFeatureState,
    regolith_coverage_fraction: Decimal,
    feature_talus_sediment_fraction: Decimal,
) -> Decimal:
    local_support = feature_area_support_at(feature.area_fraction)
    return clamp_unit_interval(
        (
            regolith_coverage_fraction * (Decimal("0.60") + (Decimal("0.40") * local_support))
        )
        + (Decimal("0.12") * feature_talus_sediment_fraction)
    )


def feature_regolith_thickness_m_at(
    mean_regolith_thickness_m: Decimal,
    feature_regolith_fraction: Decimal,
) -> Decimal:
    return mean_regolith_thickness_m * (
        Decimal("0.60") + (Decimal("0.40") * feature_regolith_fraction)
    )


def feature_terrain_state_at(
    feature: volcanic_impact_resurfacing.ResurfacingFeatureState,
    feature_dust_index: Decimal,
    feature_chemical_weathering_index: Decimal,
    feature_talus_sediment_fraction: Decimal,
    feature_regolith_fraction: Decimal,
) -> str:
    if feature.feature_type == "crater_field":
        if feature_dust_index >= Decimal("0.55"):
            return "dusty_impact_regolith"
        if feature_regolith_fraction >= Decimal("0.35"):
            return "impact_regolith_plain"
        return "fresh_impact_scars"
    if feature.feature_type == "flood_basalt_province":
        if feature_chemical_weathering_index >= Decimal("0.35"):
            return "weathered_basalt_traps"
        if feature_talus_sediment_fraction >= Decimal("0.40"):
            return "basalt_rubble_fields"
        return "fresh_basalt_flows"
    if feature.feature_type == "volcanic_province":
        if feature_talus_sediment_fraction >= Decimal("0.45"):
            return "talus_volcanic_highlands"
        return "scoriaceous_volcanics"
    if feature_talus_sediment_fraction >= Decimal("0.42"):
        return "rubble_hotspot_track"
    if feature_regolith_fraction >= Decimal("0.35"):
        return "ash_dusted_hotspot_track"
    return "juvenile_hotspot_track"


def regolith_features_at(
    resurfacing_state: volcanic_impact_resurfacing.VolcanicImpactResurfacingState,
    rock_fracture_index: Decimal,
    dust_generation_index: Decimal,
    chemical_weathering_index: Decimal,
    talus_accumulation_fraction: Decimal,
    sediment_accumulation_fraction: Decimal,
    regolith_coverage_fraction: Decimal,
    mean_regolith_thickness_m: Decimal,
) -> tuple[RegolithFeatureState, ...]:
    features: list[RegolithFeatureState] = []
    for feature in resurfacing_state.features:
        fracture_index = feature_fracture_index_at(feature, rock_fracture_index)
        dust_index = feature_dust_index_at(feature, dust_generation_index)
        local_chemical_weathering = feature_chemical_weathering_index_at(
            feature, chemical_weathering_index
        )
        local_talus_sediment = feature_talus_sediment_fraction_at(
            feature, talus_accumulation_fraction, sediment_accumulation_fraction
        )
        regolith_fraction = feature_regolith_fraction_at(
            feature, regolith_coverage_fraction, local_talus_sediment
        )
        features.append(
            RegolithFeatureState(
                feature_id=feature.feature_id,
                source_feature_id=feature.source_feature_id,
                source_feature_type=feature.source_feature_type,
                terrain_state=feature_terrain_state_at(
                    feature,
                    dust_index,
                    local_chemical_weathering,
                    local_talus_sediment,
                    regolith_fraction,
                ),
                fracture_index=fracture_index,
                dust_index=dust_index,
                chemical_weathering_index=local_chemical_weathering,
                talus_sediment_fraction=local_talus_sediment,
                regolith_fraction=regolith_fraction,
                regolith_thickness_m=feature_regolith_thickness_m_at(
                    mean_regolith_thickness_m, regolith_fraction
                ),
            )
        )
    return tuple(features)


def basic_regolith_weathering_state_from_inputs(
    resurfacing_state: volcanic_impact_resurfacing.VolcanicImpactResurfacingState,
    atmosphere_state: early_atmosphere.EarlyAtmosphereState,
    temperature_state: surface_temperature.SurfaceTemperatureState,
) -> BasicRegolithWeatheringState:
    rock_fracture_index = rock_fracture_index_at(resurfacing_state, temperature_state)
    dust_generation_index = dust_generation_index_at(
        atmosphere_state, temperature_state, resurfacing_state, rock_fracture_index
    )
    chemical_weathering_index = chemical_weathering_index_at(
        atmosphere_state, temperature_state, rock_fracture_index
    )
    talus_accumulation_fraction = talus_accumulation_fraction_at(
        temperature_state, resurfacing_state, rock_fracture_index
    )
    sediment_accumulation_fraction = sediment_accumulation_fraction_at(
        dust_generation_index,
        chemical_weathering_index,
        talus_accumulation_fraction,
        resurfacing_state.crater_persistence_fraction,
    )
    regolith_coverage_fraction = regolith_coverage_fraction_at(
        atmosphere_state,
        rock_fracture_index,
        dust_generation_index,
        chemical_weathering_index,
        talus_accumulation_fraction,
        sediment_accumulation_fraction,
    )
    mean_regolith_thickness_m = mean_regolith_thickness_m_at(
        regolith_coverage_fraction,
        dust_generation_index,
        chemical_weathering_index,
        talus_accumulation_fraction,
        sediment_accumulation_fraction,
    )
    features = regolith_features_at(
        resurfacing_state,
        rock_fracture_index,
        dust_generation_index,
        chemical_weathering_index,
        talus_accumulation_fraction,
        sediment_accumulation_fraction,
        regolith_coverage_fraction,
        mean_regolith_thickness_m,
    )
    return BasicRegolithWeatheringState(
        step_index=resurfacing_state.step_index,
        age_years=resurfacing_state.age_years,
        radius_km=resurfacing_state.radius_km,
        surface_environment=atmosphere_state.surface_environment,
        surface_temperature_regime=temperature_state.surface_temperature_regime,
        tectonic_regime=resurfacing_state.tectonic_regime,
        rock_fracture_index=rock_fracture_index,
        dust_generation_index=dust_generation_index,
        chemical_weathering_index=chemical_weathering_index,
        talus_accumulation_fraction=talus_accumulation_fraction,
        sediment_accumulation_fraction=sediment_accumulation_fraction,
        regolith_coverage_fraction=regolith_coverage_fraction,
        mean_regolith_thickness_m=mean_regolith_thickness_m,
        exposed_bedrock_fraction=exposed_bedrock_fraction_at(
            regolith_coverage_fraction, resurfacing_state
        ),
        texture_state=texture_state_at(
            atmosphere_state.surface_environment,
            rock_fracture_index,
            dust_generation_index,
            chemical_weathering_index,
            talus_accumulation_fraction,
            sediment_accumulation_fraction,
            regolith_coverage_fraction,
        ),
        feature_count=len(features),
        features=features,
        world_class=resurfacing_state.world_class,
    )


def simulate(
    criteria: planet.SimulationCriteria,
) -> Iterable[BasicRegolithWeatheringState]:
    resurfacing_states = volcanic_impact_resurfacing.simulate(criteria)
    atmosphere_states = early_atmosphere.simulate(criteria)
    temperature_states = surface_temperature.simulate(criteria)
    for resurfacing_state, atmosphere_state, temperature_state in zip(
        resurfacing_states,
        atmosphere_states,
        temperature_states,
    ):
        yield basic_regolith_weathering_state_from_inputs(
            resurfacing_state, atmosphere_state, temperature_state
        )


def first_textured_surface_state(
    states: Iterable[BasicRegolithWeatheringState],
) -> BasicRegolithWeatheringState | None:
    for state in states:
        if (
            state.texture_state != "pristine_magmatic_surface"
            and state.regolith_coverage_fraction >= Decimal("0.15")
        ):
            return state
    return None


def validate_model() -> None:
    volcanic_impact_resurfacing.validate_model()
    reference_criteria = planet.build_criteria(VALIDATION_STEP_YEARS)
    states = list(simulate(reference_criteria))
    initial_state = states[0]
    present_state = states[-1]
    first_textured_state = first_textured_surface_state(states)
    present_terrain_states = {feature.terrain_state for feature in present_state.features}

    if initial_state.texture_state != "pristine_magmatic_surface":
        raise ValueError("The earliest regolith state should still be pristine and magmatic.")
    if present_state.rock_fracture_index <= Decimal("0.45"):
        raise ValueError("Present-day Aeron should have substantial rock fracturing.")
    if present_state.dust_generation_index <= Decimal("0.35"):
        raise ValueError("Present-day Aeron should generate meaningful dust.")
    if present_state.chemical_weathering_index <= Decimal("0.25"):
        raise ValueError("Present-day Aeron should permit rough chemical weathering.")
    if present_state.talus_accumulation_fraction <= Decimal("0.35"):
        raise ValueError("Present-day Aeron should accumulate crude talus.")
    if present_state.sediment_accumulation_fraction <= Decimal("0.35"):
        raise ValueError("Present-day Aeron should accumulate crude sediment.")
    if present_state.regolith_coverage_fraction <= Decimal("0.40"):
        raise ValueError("Present-day Aeron should sustain broad regolith coverage.")
    if present_state.mean_regolith_thickness_m <= Decimal("0.75"):
        raise ValueError("Present-day Aeron should sustain a meaningful regolith mantle.")
    if first_textured_state is None:
        raise ValueError("A textured barren-surface state must emerge within the span.")
    if not {
        "dusty_impact_regolith",
        "weathered_basalt_traps",
        "talus_volcanic_highlands",
    } & present_terrain_states:
        raise ValueError("Present-day regolith features should show distinct textured terrains.")


def print_input_criteria(criteria: planet.SimulationCriteria) -> None:
    fields = [
        ("layer_name", "basic_regolith_and_weathering"),
        ("resurfacing_source", "volcanic_impact_resurfacing.py"),
        ("large_scale_topography_source", "large_scale_topography.py"),
        ("surface_temperature_source", "surface_temperature.py"),
        ("early_atmosphere_source", "early_atmosphere.py"),
        ("primary_crust_source", "primary_crust.py"),
        ("interior_source", "interior.py"),
        ("planet_source", "planet.py"),
        ("coupled_resurfacing_layer", "true"),
        ("coupled_topography_layer", "true"),
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
            planet.format_decimal(
                Decimal(criteria.step_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
        ("fracture_model", "thermal_plus_impact_plus_volcanic_scaling"),
        ("dust_model", "mechanical_fragment_plus_aeolian_support"),
        ("chemical_weathering_model", "atmosphere_gated_coarse_reaction_index"),
        ("sediment_model", "talus_plus_dust_plus_crude_weathering"),
        (
            "dynamic_fields",
            "rock_fracture_index, dust_generation_index, chemical_weathering_index, "
            "talus_accumulation_fraction, sediment_accumulation_fraction, "
            "regolith_coverage_fraction, mean_regolith_thickness_m, "
            "exposed_bedrock_fraction, texture_state",
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
        ("env", 12),
        ("regime", 20),
        ("fract", 8),
        ("dust", 8),
        ("chem", 8),
        ("talus", 8),
        ("sed", 8),
        ("reg_f", 8),
        ("thick_m", 9),
        ("texture_state", 27),
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
            f"{state.surface_environment:>12} "
            f"{state.tectonic_regime:>20} "
            f"{planet.format_decimal(state.rock_fracture_index, 3):>8} "
            f"{planet.format_decimal(state.dust_generation_index, 3):>8} "
            f"{planet.format_decimal(state.chemical_weathering_index, 3):>8} "
            f"{planet.format_decimal(state.talus_accumulation_fraction, 3):>8} "
            f"{planet.format_decimal(state.sediment_accumulation_fraction, 3):>8} "
            f"{planet.format_decimal(state.regolith_coverage_fraction, 3):>8} "
            f"{planet.format_decimal(state.mean_regolith_thickness_m, 3):>9} "
            f"{state.texture_state:>27}"
        )


def print_present_day_summary(criteria: planet.SimulationCriteria) -> None:
    states = list(simulate(criteria))
    final_state = states[-1]
    first_textured_state = first_textured_surface_state(states)

    assert first_textured_state is not None

    fields = [
        ("world_class", final_state.world_class),
        ("surface_environment", final_state.surface_environment),
        ("surface_temperature_regime", final_state.surface_temperature_regime),
        ("tectonic_regime", final_state.tectonic_regime),
        (
            "rock_fracture_index",
            planet.format_decimal(final_state.rock_fracture_index, 6),
        ),
        (
            "dust_generation_index",
            planet.format_decimal(final_state.dust_generation_index, 6),
        ),
        (
            "chemical_weathering_index",
            planet.format_decimal(final_state.chemical_weathering_index, 6),
        ),
        (
            "talus_accumulation_fraction",
            planet.format_decimal(final_state.talus_accumulation_fraction, 6),
        ),
        (
            "sediment_accumulation_fraction",
            planet.format_decimal(final_state.sediment_accumulation_fraction, 6),
        ),
        (
            "regolith_coverage_fraction",
            planet.format_decimal(final_state.regolith_coverage_fraction, 6),
        ),
        (
            "mean_regolith_thickness_m",
            planet.format_decimal(final_state.mean_regolith_thickness_m, 6),
        ),
        (
            "exposed_bedrock_fraction",
            planet.format_decimal(final_state.exposed_bedrock_fraction, 6),
        ),
        ("texture_state", final_state.texture_state),
        ("first_textured_surface_step", str(first_textured_state.step_index)),
        (
            "first_textured_surface_age_myr",
            planet.format_decimal(
                Decimal(first_textured_state.age_years) / planet.YEARS_PER_MYR, 6
            ),
        ),
    ]

    key_width = max(len(key) for key, _ in fields)
    print()
    print("PRESENT REGOLITH SUMMARY")
    print("========================")
    for key, value in fields:
        print(f"{key:<{key_width}}  {value}")

    print()
    print("PRESENT REGOLITH FEATURES")
    print("=========================")
    headers = (
        ("feature", 30),
        ("terrain", 26),
        ("fracture", 9),
        ("dust", 8),
        ("chem", 8),
        ("accum_f", 9),
        ("reg_f", 8),
        ("thick_m", 9),
    )
    header_line = " ".join(f"{label:>{width}}" for label, width in headers)
    divider_line = " ".join("-" * width for _, width in headers)
    print(header_line)
    print(divider_line)
    for feature in final_state.features:
        print(
            f"{feature.feature_id:>30} "
            f"{feature.terrain_state:>26} "
            f"{planet.format_decimal(feature.fracture_index, 3):>9} "
            f"{planet.format_decimal(feature.dust_index, 3):>8} "
            f"{planet.format_decimal(feature.chemical_weathering_index, 3):>8} "
            f"{planet.format_decimal(feature.talus_sediment_fraction, 3):>9} "
            f"{planet.format_decimal(feature.regolith_fraction, 3):>8} "
            f"{planet.format_decimal(feature.regolith_thickness_m, 3):>9}"
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
