# Aeron (The World)

`Aeron` is the central world of the current mythopedia corpus: a stable, layered terrestrial place produced during [Kethralen (Planetary Formation Era)](planetary_formation_era.md) and further articulated during [Athralen (Continental Differentiation Era)](continental_differentiation_era.md). Its defining trait is not only material structure, but lawful continuity: gravity-like pull, atmosphere, thermal interior, oceans, and rotational rhythms all endure as stable systems rather than as temporary spectacle.

World-binding doctrine treats planetary formation as an ontological shift from luminous realms into persistent places. In that framework, `Aeron` is a deliberately sustained environment in which long-duration processes can accumulate: geology records memory, climate establishes cycles, and later ecosystems become possible before full life-history unfolds.

Primary references:
- [Aeron](../../primal_language/structural_principles/aeron.md)
- [Kethralen (Planetary Formation Era)](planetary_formation_era.md)
- [Athralen (Continental Differentiation Era)](continental_differentiation_era.md)
- [Luminaries](../astrology/luminaries.md)
- [Moons of Aeron](../astrology/moons_of_aeron.md)

## Primal Status

- `Aeron` is itself a primal-language headword and the canonical proper name of the world.
- In current canon, `Aeron` names this specific world rather than the generic class of all planets or all realms.
- The world-name must not be back-formed into an English placeholder inside primal-language canon.

## World-Centered Celestial Frame

`Aeron` sits within a geocentric luminary arrangement in which [Solaryth](../../primal_language/structural_principles/solaryth.md) and [Nyxorys](../../primal_language/structural_principles/nyxorys.md) counter-orbit in permanent opposition, while the [Seravel](../../primal_language/structural_principles/seravel.md) act as balancing regulators. This makes `Aeron` the reference frame for cosmology, astrology, theology, calendar doctrine, and tidal interpretation across the current mythopedia.

## Planetary Structural Ratios

`Aeron` is canonically treated as a rock-dominant terrestrial world. On conceptual volume scale:

- Solid rock and metal: about `99%+`
- Hydrosphere: about `0.1-0.2%`
- Atmosphere (effective volume): less than `0.5%`
- Active magma or melt fraction: small and regionally variable, not a global magma ocean

These are structural assumptions rather than rigid accounting targets. They establish that:

- Oceans are thin skin-layers over a deep rocky body.
- Atmosphere is shallow and physically fragile relative to planetary radius.
- Magma is dynamic and geologically powerful without becoming the planet's dominant bulk state.

Worldbuilding consequences:

- Supports tectonic realism in continental and basin development.
- Keeps elemental interactions physically anchored during celestial stress windows.
- Explains why coastline, shelf, and intertidal geographies are sensitive to lunar forcing.

Cross-reference: lunar forcing rules and multi-moon resonance are defined in [Moons of Aeron](../astrology/moons_of_aeron.md).

## Planet-Scale Physical Model (Simulation Baseline)

This section combines:

1. Canonical planet-scale constraints from the era documents.
2. Explicit numeric simulation values from the current worldbuilding directive: `Aeron` began at `1/7` Earth radius, expanded exponentially for `5.4` billion years, and is now Earth-sized.

## Source Provenance

- Canonical-era documents establish layered structure, active tectonics, interior heat continuity, long-duration climatic recurrence, and world-centered celestial regulation.
- Expansion specifics, including initial radius, exponential growth law, and plate-allocation tolerance, are treated here as the current simulation directive and canon-locked baseline.

## Earth Reference Values Used

For transparent derivation, this page uses the following Earth baseline constants:

- Earth mean radius: `R_earth = 6371 km`
- Earth mean crust thickness for simple global models: `D_crust,earth = 35 km`
- Earth-like normalized mantle convection strength: `C_mantle,earth = 1.0`
- Earth present-day internal heat output proxy for this model: `Q_core+interior,earth = 47 TW`

## Aeron Radius Growth Law

Let `t = 0` at the start of expansion and `t = 5.4e9 years` at present.

- Initial radius: `R0 = R_earth / 7 = 910.142857 km`
- Present radius: `R_now = R_earth = 6371 km`
- Exponential form: `R(t) = R0 * exp(k t)`
- Growth constant: `k = ln(R_now / R0) / 5.4e9 = ln(7) / 5.4e9 = 3.6035e-10 yr^-1`
- Equivalent form in Gyr units: `k = 0.36035 Gyr^-1`

## Planetary Parameters For Simulation

| Parameter | Initial (`t=0`) | Present (`t=5.4 Gyr`) | Derivation rule |
| --- | ---: | ---: | --- |
| Radius `R_p` | `910.143 km` | `6371 km` | Given by directive plus exponential law |
| Crust thickness `D_crust` | `5.000 km` | `35.000 km` | Length-scale fraction held constant: `D_crust proportional to R` |
| Mantle convection strength `C_mantle` | `1.0` | `1.0` | Earth-normalized coefficient for first-pass model |
| Core/internal heat output `Q_core` | `0.137 TW` | `47.000 TW` | Same volumetric heat production class: `Q proportional to R^3` |

## Notes On Derived Values

- Crust thickness scales as `D0 = 35 / 7 = 5 km` under fixed geometric similarity.
- Heat output scales as `Q0 = 47 * (1/7)^3 = 47 / 343 = 0.1370 TW`.
- This thermal rule can be replaced later with a more detailed rheology or radiogenic partition model if canon requires non-self-similar evolution.

## Plate Growth And Mass Allocation Rule

As `Aeron` expands, new planetary mass is assigned to tectonic plates approximately evenly:

- Target share per plate at each allocation step: `1 / N_plates`
- Realized per-plate share allowed variation: `plus or minus 3%` around target
- Conservation requirement: the sum of all plate allocations equals total added mass for the step

This keeps long-term plate growth near-uniform while still permitting tectonic asymmetry.

## Data Contract For Simulation

```yaml
aeron_planetary_physics:
  reference_earth:
    radius_km: 6371
    crust_effective_thickness_km: 35
    mantle_convection_relative: 1.0
    internal_heat_output_tw: 47
  expansion_model:
    type: exponential
    duration_years: 5.4e9
    initial_radius_km: 910.142857
    present_radius_km: 6371
    k_per_year: 3.6035e-10
    k_per_gyr: 0.36035
  crust_thickness_km:
    initial: 5.0
    present: 35.0
    scaling_rule: proportional_to_radius
  mantle_convection:
    initial_relative_to_earth: 1.0
    present_relative_to_earth: 1.0
  core_heat_output_tw:
    initial: 0.1370
    present: 47.0
    scaling_rule: proportional_to_radius_cubed
  plate_mass_distribution:
    mode: near_equal
    tolerance_percent: 3
```

## References In Current Canon

- [Kethralen (Planetary Formation Era)](planetary_formation_era.md): world-binding orders and layered planetary continuity
- [Athralen (Continental Differentiation Era)](continental_differentiation_era.md): surface structuring, plate identity, and tectonic memory
- [Luminaries](../astrology/luminaries.md): the geocentric `Solaryth`-`Nyxorys` axis
- [Moons of Aeron](../astrology/moons_of_aeron.md): lunar forcing rules and multi-moon resonance

## Canon Boundaries

- `Aeron` names the world itself, not a generic term for all worlds.
- This page canonizes a first-pass physical model for setting simulation and continuity; it does not close later refinements in rheology, atmospheric chemistry, or precise orbital ephemerides.
- The world remains a created, lawful place, not a soul-bearing planetary mind or self-authored divine intelligence.
- Climate-bearing development downstream of `Athralen` may elaborate this page further, but must not break the structural ratios and continuity rules defined here without an explicit canon revision.
