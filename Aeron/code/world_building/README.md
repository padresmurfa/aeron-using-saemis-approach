# World Building Code

This directory holds deterministic simulation scripts for Aeron's physical development.

## Current Contents

- `planet.py`: deterministic planet-scale simulation from formation to present
- `interior.py`: deterministic interior structure and thermal evolution simulation that imports and ticks `planet.py`
- `primary_crust.py`: deterministic primary crust formation simulation that imports and ticks `interior.py`
- `early_atmosphere.py`: deterministic early atmosphere and volatile accumulation simulation that imports and ticks `primary_crust.py`
- `surface_temperature.py`: deterministic surface temperature regime simulation that imports and ticks `early_atmosphere.py`
- `proto_tectonics.py`: deterministic proto-tectonic regime simulation that imports and ticks `surface_temperature.py`
- `plate_system.py`: deterministic plate-system simulation that imports and ticks `proto_tectonics.py`
- `large_scale_topography.py`: deterministic large-scale topography generation that imports and ticks `plate_system.py`
- `volcanic_impact_resurfacing.py`: deterministic volcanic and impact resurfacing simulation that imports and ticks `large_scale_topography.py`
- `basic_regolith_weathering.py`: deterministic basic regolith and weathering simulation that imports and ticks `volcanic_impact_resurfacing.py`

## Scope Boundaries

- The bulk layer models the planetary evolution scalars that establish what kind of world Aeron physically is before continent-generation work begins.
- The interior layer builds directly on the bulk layer and exists to determine whether Aeron cools into a differentiated, convecting world capable of later tectonics.
- The primary crust layer builds on the interior layer and exists to determine when Aeron stops being mostly a molten ball and starts being a stable solid world with a real crustal lid.
- The early atmosphere layer builds on the primary crust layer and exists to determine whether Aeron's surface presents as lava, bare rock, steam, ice, or precipitation-capable wet rock.
- The surface temperature layer builds on the atmosphere layer and exists to determine the world's average thermal band, broad latitudinal contrast, surface-liquid viability, crustal thermal stability, and whether the surface reads as volcanic, steam-shrouded, wind-scoured, icy, or wet rock.
- The proto-tectonic layer builds on the surface temperature layer and exists to determine whether the lithosphere is rigid enough to fracture, whether plates exist yet, which tectonic regime applies, and where the first major fracture, spreading, and recycling zones should appear in broad planetary terms.
- The plate-system layer builds on the proto-tectonic layer and exists to turn those broad tectonic conditions into discrete plate regions, motion vectors, boundary behaviors, and first-order crust creation and destruction rates.
- The large-scale topography layer builds on the plate-system layer and exists to turn plate motion into first-order relief: proto-continents, basins, ridges, arcs, uplifts, rifts, highlands, and lowlands.
- The volcanic and impact resurfacing layer builds on the large-scale topography layer and exists to determine how hotspots, flood basalts, volcanic provinces, impacts, and crater retention continually scar and rework that relief.
- The basic regolith and weathering layer builds on the resurfacing layer and exists to determine how barren rock breaks down into dust, chemically altered crust, talus, and crude sediment, so the surface gains age and texture before full erosion modeling begins.
- These scripts do not yet generate continents, tectonic maps, climate fields, ocean circulation, or GIS outputs.
- Later continent and terrain work should build on this layer rather than collapsing all world-building scope into one file.

## Bulk Evolution Outputs

`planet.py` now answers:

- mass
- radius
- density
- internal heat budget
- core, mantle, and crust differentiation state
- rotation rate
- axial-tilt state
- orbital-year regime
- magnetic field presence or absence
- rough atmospheric retention potential

At this layer, exact numeric obliquity and detailed orbital ephemerides remain explicitly pending rather than being invented.

## Interior And Thermal Outputs

`interior.py` answers:

- cooling over time
- solidification state
- formation of core, mantle, and primordial crust
- internal convection potential
- heat-source split across residual formation heat, radioactive decay, and low-amplitude tidal heating
- tectonic readiness for later land-shaping layers

## Primary Crust Outputs

`primary_crust.py` answers:

- when the first stable crust appears
- approximate gross and stable crust thickness
- whether the primary crust is mostly oceanic-like, continental-like, or undifferentiated
- where weak zones persist as fracture or proto-rift patterns
- whether the surface is mostly molten, mixed, or mostly solid

## Early Atmosphere Outputs

`early_atmosphere.py` answers:

- outgassing strength from the coupled interior and crust state
- retention or loss tendency for gases
- atmospheric pressure trends
- broad atmospheric composition class
- rough greenhouse intensity
- whether liquid precipitation is possible at all
- whether the surface reads as lava, steam, naked rock, wet rock, ice, or dry rock

## Surface Temperature Outputs

`surface_temperature.py` answers:

- average surface temperature band
- coarse equator-to-pole thermal contrast
- whether surface liquids can exist as absent, transient, frozen, or stable
- whether the crust remains thermally disrupted, fragile, stressed, or stable
- how much thermal cycling the surface experiences
- whether the world reads as hot volcanic rock, cold dead rock, dry wind-scoured rock, steam-shrouded rock, ice-rock, or temperate wet rock

## Proto-Tectonic Outputs

`proto_tectonics.py` answers:

- whether the lithosphere is rigid enough to fracture
- whether plates exist yet
- whether the world is in a stagnant-lid, episodic-overturn, or plate-like regime
- where the first major fracture belts appear
- where spreading and recycling zones first organize in broad planetary terms

## Plate-System Outputs

`plate_system.py` answers:

- how many coherent plate regions exist
- how many of those regions count as active plates
- motion vectors for each active region
- first-order spreading, collision, recycling, and transform rates
- crust creation and destruction rates
- the present-day discrete plate-region structure that later continental work can inherit

## Large-Scale Topography Outputs

`large_scale_topography.py` answers:

- first-order proto-continents
- ocean basins
- spreading ridges
- volcanic arcs
- collision-driven uplifts
- major rifts
- highlands and lowlands
- planetary-scale relief contrast before erosion modeling begins

## Volcanic And Impact Resurfacing Outputs

`volcanic_impact_resurfacing.py` answers:

- hotspot tracks and hotspot activity
- flood basalt events and trap provinces
- aggregate volcanic province coverage
- major crater formation rate and crater persistence
- resurfacing fraction and resurfacing rate
- how much old crust survives into the present surface
- whether the barren world reads as heavily reworked, transitional, or ancient and scarred

## Basic Regolith And Weathering Outputs

`basic_regolith_weathering.py` answers:

- how strongly surface rock fractures under thermal cycling, impact scarring, and volcanic reworking
- how much dust the barren world generates
- whether atmosphere and surface liquids permit rough chemical weathering at all
- how much crude talus and sediment accumulates
- how much regolith mantles the surface and how thick that mantle becomes
- how much bedrock remains exposed
- whether the barren world reads as pristine magmatic rock, fractured bare rock, dusty scars, rubble-talused barrens, or weathered regolith barrens

## Usage

```bash
python3 Aeron/code/world_building/planet.py
python3 Aeron/code/world_building/planet.py --step-years 900000000
python3 Aeron/code/world_building/interior.py
python3 Aeron/code/world_building/interior.py --step-years 900000000
python3 Aeron/code/world_building/primary_crust.py
python3 Aeron/code/world_building/primary_crust.py --step-years 900000000
python3 Aeron/code/world_building/early_atmosphere.py
python3 Aeron/code/world_building/early_atmosphere.py --step-years 900000000
python3 Aeron/code/world_building/surface_temperature.py
python3 Aeron/code/world_building/surface_temperature.py --step-years 900000000
python3 Aeron/code/world_building/proto_tectonics.py
python3 Aeron/code/world_building/proto_tectonics.py --step-years 900000000
python3 Aeron/code/world_building/plate_system.py
python3 Aeron/code/world_building/plate_system.py --step-years 900000000
python3 Aeron/code/world_building/large_scale_topography.py
python3 Aeron/code/world_building/large_scale_topography.py --step-years 900000000
python3 Aeron/code/world_building/volcanic_impact_resurfacing.py
python3 Aeron/code/world_building/volcanic_impact_resurfacing.py --step-years 900000000
python3 Aeron/code/world_building/basic_regolith_weathering.py
python3 Aeron/code/world_building/basic_regolith_weathering.py --step-years 900000000
```

## Current Rules

- The simulation span is fixed at `5.4` billion years from planetary formation to today.
- `--step-years` must evenly divide the full simulation duration so the loop stays fixed-step.
- Internal calculations use exact deterministic scaling relations and then round only for display, so prose-rounded canon values can remain human-readable while the present-day simulated state still lands exactly on today's canon.
- Each script prints input criteria first, then one time-series row per iteration, then a present-world summary for the final state of that layer.
- `interior.py` uses `planet.py` as a library and advances both layers together on the same timestep so the thermal model follows Aeron's changing bulk state.
- `primary_crust.py` uses `interior.py` as a library, which in turn uses `planet.py`, so the crustal-lid model stays coupled to Aeron's changing bulk and thermal state.
- `early_atmosphere.py` uses `primary_crust.py` as a library, which in turn uses `interior.py` and `planet.py`, so volatile accumulation stays coupled to Aeron's structural and thermal evolution.
- `surface_temperature.py` uses `early_atmosphere.py` as a library, which in turn uses `primary_crust.py`, `interior.py`, and `planet.py`, so the thermal regime stays coupled to Aeron's atmospheric, crustal, and interior history.
- `proto_tectonics.py` uses `surface_temperature.py` as a library, which in turn uses the atmosphere, crust, interior, and bulk-planet layers, so proto-plate behavior only appears once the earlier physical prerequisites are already in place.
- `plate_system.py` uses `proto_tectonics.py` as a library, which in turn uses all earlier layers, so discrete plate motions only emerge after the lithosphere, atmosphere, crust, and thermal regime have already crossed the required thresholds.
- `large_scale_topography.py` uses `plate_system.py` as a library, which in turn uses all earlier layers, so first-order relief only appears once plate regions, motions, and crust budgets already exist.
- `volcanic_impact_resurfacing.py` uses `large_scale_topography.py` as a library, which in turn uses all earlier layers, so resurfacing and surface scarring only appear once tectonic structure and relief already exist.
- `basic_regolith_weathering.py` uses `volcanic_impact_resurfacing.py` as a library and consults the coupled atmosphere and temperature states, so barren-surface texture only emerges once the world already has crust, atmosphere, thermal cycling, tectonic relief, and resurfacing scars to work on.
