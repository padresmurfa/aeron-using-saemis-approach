# World Building Code

This directory holds deterministic simulation scripts for Aeron's physical development.
The numbered filenames define the execution order of the pipeline, and each script writes its artifacts into a matching folder under `Aeron/mapping/NN_layer_name/`, with `output.json`, layer-specific PNGs, and any geometry/state sidecar files living together.

## Current Contents

- `01_planet.py`: deterministic planet-scale simulation from formation to present, with timestep tables, a present-world summary, and a concentric radius-growth PNG
- `02_interior.py`: deterministic interior structure and thermal evolution simulation that imports and ticks `01_planet.py`, with timestep tables, a present-interior summary, and a present-state cutaway PNG
- `03_primary_crust.py`: deterministic primary crust formation simulation that imports and ticks `02_interior.py`, with timestep tables, a present-crust summary, and a zonal solidification PNG
- `04_early_atmosphere.py`: deterministic early atmosphere and volatile accumulation simulation that imports and ticks `03_primary_crust.py`
- `05_surface_temperature.py`: deterministic surface temperature regime simulation that imports and ticks `04_early_atmosphere.py`, with a zonal thermal-band PNG
- `06_proto_tectonics.py`: deterministic proto-tectonic regime simulation that imports and ticks `05_surface_temperature.py`, with the first coarse surface-cell field PNG
- `07_plate_system.py`: deterministic plate-system simulation that imports and ticks `06_proto_tectonics.py`
- `08_large_scale_topography.py`: deterministic large-scale topography generation that imports and ticks `07_plate_system.py`
- `09_volcanic_impact_resurfacing.py`: deterministic volcanic and impact resurfacing simulation that imports and ticks `08_large_scale_topography.py`
- `10_basic_regolith_weathering.py`: deterministic basic regolith and weathering simulation that imports and ticks `09_volcanic_impact_resurfacing.py`
- `11_hydrology_before_life.py`: deterministic hydrology-before-life simulation that imports and ticks `10_basic_regolith_weathering.py`

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
- The hydrology-before-life layer builds on the regolith/weathering layer and exists to determine when barren Aeron already supports stable seas, inland water, glacier zones, runoff pathways, and basin filling before biology appears.
- These scripts do not yet generate finalized continent maps, refined coastlines, climate fields, ocean circulation, GIS-ready terrain, or biologically shaped landscapes.
- The large-scale topography layer already establishes first-order proto-continents, basins, ridges, arcs, uplifts, rifts, highlands, and lowlands that later continent and terrain work should inherit rather than re-derive.
- The current library-on-library import chain is intentional because each layer depends on the prior physical state, but later additions should avoid ad hoc deep coupling and prefer explicit shared state contracts when the stack grows.

## Visualization Geometry Policy

- `01_planet.py` and `02_interior.py` own global and radial structure only, so their custom visuals stay timeline-based, radial, or cutaway-based rather than pretending to know surface geography.
- `03_primary_crust.py`, `04_early_atmosphere.py`, and `05_surface_temperature.py` may use zonal geometry such as latitude bands when the layer actually models pole-to-equator differences, but they should not invent longitude-resolved world maps.
- `06_proto_tectonics.py` is the first layer allowed to introduce a true coarse planetary surface grid because it is the first layer that owns localized fracture, spreading, and recycling structure in a meaningful way.
- `07_plate_system.py` defines the authoritative coarse tectonic mesh for the rest of the pipeline.
- `08_large_scale_topography.py` is the first layer allowed to refine that tectonic mesh by deterministic subdivision.
- `09_volcanic_impact_resurfacing.py`, `10_basic_regolith_weathering.py`, and `11_hydrology_before_life.py` must keep consuming and mutating the inherited refined terrain mesh rather than inventing disconnected one-off plotting schemes.

## Shared Mesh Contract

- `07_plate_system.py` owns the authoritative `tectonic_mesh`: stable coarse cell IDs, lat/lon bounds, neighbors, `plate_id`, motion vectors, and tectonic boundary state.
- `08_large_scale_topography.py` creates the first `terrain_mesh` by deterministic lat/lon quadrisection of each tectonic cell.
- The current refinement rule is fixed:
  - split each tectonic cell into four children
  - child `0` = `south_west`
  - child `1` = `south_east`
  - child `2` = `north_west`
  - child `3` = `north_east`
- Child IDs inherit deterministically from the parent tectonic cell, for example `lat_12_lon_033.0`.
- Every refined cell carries:
  - `cell_id`
  - `parent_cell_id`
  - `root_tectonic_cell_id`
  - inherited `plate_id`
  - inherited motion vector and tectonic boundary context
- `09–11` add process fields to that same `terrain_mesh`; they do not regenerate a new incompatible geometry family.
- Coarse tectonic identity stays rooted in `07`, while elevation, resurfacing, regolith, and hydrology fields are allowed to diverge between refined children.

## Bulk Evolution Outputs

`01_planet.py` now answers:

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
- a deterministic concentric-circle radius-growth visualization written to `Aeron/mapping/01_planet/radius_growth.png`
- two deterministic upper-right-quadrant radius projections written to `Aeron/mapping/01_planet/radius_quadrant_time_linear.png` and `Aeron/mapping/01_planet/radius_quadrant_radius_linear.png`

At this layer, exact numeric obliquity and detailed orbital ephemerides remain explicitly pending rather than being invented.
The radius-growth PNG uses one full circle per timestep centered at `(0, 0)`, with circle radius equal to the simulated radius in kilometers. Inner rings are earlier states, outer rings are later states, and the warm-to-cool palette is a deterministic era encoding from earlier/hotter visual states to later/cooler visual states.
The two quadrant projections derive from the same concentric-circle geometry but keep only the upper-right quadrant of each timestep. The time-linear view maps each quadrant's local horizontal fraction linearly onto that state's simulation age, while the radius-linear view preserves radius on the vertical axis and converts the same local horizontal fraction back into age through the inverse deterministic growth law. Both reuse the same thermal color encoding as the concentric plot.

## Interior And Thermal Outputs

`02_interior.py` answers:

- cooling over time
- solidification state
- formation of core, mantle, and primordial crust
- internal convection potential
- heat-source split across residual formation heat, radioactive decay, and low-amplitude tidal heating
- tectonic readiness for later land-shaping layers
- a deterministic present-state cutaway visualization written to `Aeron/mapping/02_interior/cutaway_present.png`

The interior cutaway shows the actual coarse layers this model distinguishes: primordial crust, mantle, differentiated core, and any remaining residual melt at the center. The crust thickness is derived from the current radius and `primordial_crust_fraction`; the core radius is derived from the relative core-versus-mantle formation fractions; and the residual-melt center is derived from the unsolidified fraction. Because the crust is too thin to read cleanly at true scale, the cutaway applies a deterministic minimum display thickness for crust only and notes that exaggeration in the figure footer while keeping all summary values at true simulated scale.

## Primary Crust Outputs

`03_primary_crust.py` answers:

- when the first stable crust appears
- approximate gross and stable crust thickness
- whether the primary crust is mostly oceanic-like, continental-like, or undifferentiated
- where weak zones persist as fracture or proto-rift patterns
- whether the surface is mostly molten, mixed, or mostly solid
- a deterministic zonal solidification visualization written to `Aeron/mapping/03_primary_crust/zonal_solidification.png`

The zonal solidification PNG is intentionally latitude-only. This layer does not resolve real surface geography yet, so the figure shows molten, mixed, and solid-crust bands across latitude and time using a symmetric pole-to-equator cooling relief applied to the real global crust state.

## Early Atmosphere Outputs

`04_early_atmosphere.py` answers:

- outgassing strength from the coupled interior and crust state
- retention or loss tendency for gases
- atmospheric pressure trends
- broad atmospheric composition class
- rough greenhouse intensity
- whether liquid precipitation is possible at all
- whether the surface reads as lava, steam, naked rock, wet rock, ice, or dry rock

## Surface Temperature Outputs

`05_surface_temperature.py` answers:

- average surface temperature band
- coarse equator-to-pole thermal contrast
- whether surface liquids can exist as absent, transient, frozen, or stable
- whether the crust remains thermally disrupted, fragile, stressed, or stable
- how much thermal cycling the surface experiences
- whether the world reads as hot volcanic rock, cold dead rock, dry wind-scoured rock, steam-shrouded rock, ice-rock, or temperate wet rock
- a deterministic zonal thermal-band visualization written to `Aeron/mapping/05_surface_temperature/zonal_bands.png`

The zonal thermal-band PNG projects each timestep's modeled mean surface temperature and equator-to-pole contrast into latitude bands only. It preserves the simulated global mean and the exact modeled equator-pole delta, but it does not claim longitude-resolved climate structure.

## Proto-Tectonic Outputs

`06_proto_tectonics.py` answers:

- whether the lithosphere is rigid enough to fracture
- whether plates exist yet
- whether the world is in a stagnant-lid, episodic-overturn, or plate-like regime
- where the first major fracture belts appear
- where spreading and recycling zones first organize in broad planetary terms
- a deterministic coarse surface-cell field visualization written to `Aeron/mapping/06_proto_tectonics/surface_fields.png`

The proto-tectonic surface-field PNG is the first honest map-like view in the pipeline. It uses a deterministic coarse lat/lon cell grid to visualize lithosphere rigidity, thermal stress, fracture susceptibility, proto-rift tendency, upwelling influence, and recycling tendency derived from the layer's real global indices and named zone patterns.

## Plate-System Outputs

`07_plate_system.py` answers:

- how many coherent plate regions exist
- how many of those regions count as active plates
- motion vectors for each active region
- first-order spreading, collision, recycling, and transform rates
- crust creation and destruction rates
- the present-day discrete plate-region structure that later continental work can inherit
- the authoritative coarse `tectonic_mesh` written into the layer JSON and `.npz` state artifact

## Large-Scale Topography Outputs

`08_large_scale_topography.py` answers:

- first-order proto-continents
- ocean basins
- spreading ridges
- volcanic arcs
- collision-driven uplifts
- major rifts
- highlands and lowlands
- planetary-scale relief contrast before erosion modeling begins
- continent-adjacent relief scaffolding before finalized continent maps, shorelines, and erosion-shaped landmasses exist
- the first deterministic `terrain_mesh`, obtained by subdividing the authoritative `07` tectonic mesh without recomputing `plate_id` from scratch

## Volcanic And Impact Resurfacing Outputs

`09_volcanic_impact_resurfacing.py` answers:

- hotspot tracks and hotspot activity
- flood basalt events and trap provinces
- aggregate volcanic province coverage
- major crater formation rate and crater persistence
- resurfacing fraction and resurfacing rate
- how much old crust survives into the present surface
- whether the barren world reads as heavily reworked, transitional, or ancient and scarred
- volcanic, impact, resurfacing-age, and lava/crater overprint fields on the inherited refined terrain mesh

## Basic Regolith And Weathering Outputs

`10_basic_regolith_weathering.py` answers:

- how strongly surface rock fractures under thermal cycling, impact scarring, and volcanic reworking
- how much dust the barren world generates
- whether atmosphere and surface liquids permit rough chemical weathering at all
- how much crude talus and sediment accumulates
- how much regolith mantles the surface and how thick that mantle becomes
- how much bedrock remains exposed
- whether the barren world reads as pristine magmatic rock, fractured bare rock, dusty scars, rubble-talused barrens, or weathered regolith barrens
- regolith, weathering, dust, transport, and exposed-bedrock fields on the inherited refined terrain mesh

## Hydrology Before Life Outputs

`11_hydrology_before_life.py` answers:

- how much of the world supports stable oceans
- whether inland seas persist in lowlands and rifts
- whether glacier zones exist on the barren world
- how many first-order runoff pathways connect relief to basins
- how far the major basins have filled with water and sediment
- whether prebiotic Aeron reads as dry, steam-condensate, fragmentary wet barrens, or a true rain-sea-ice world
- water depth, runoff receivers, basin fill, glacier presence, and inland-sea masks on the inherited refined terrain mesh

## Usage

Install visualization dependencies first:

```bash
python3 -m pip install -r requirements.txt
```

```bash
python3 Aeron/code/world_building/01_planet.py
python3 Aeron/code/world_building/01_planet.py --step-years 900000000
python3 Aeron/code/world_building/02_interior.py
python3 Aeron/code/world_building/02_interior.py --step-years 900000000
python3 Aeron/code/world_building/03_primary_crust.py
python3 Aeron/code/world_building/03_primary_crust.py --step-years 900000000
python3 Aeron/code/world_building/04_early_atmosphere.py
python3 Aeron/code/world_building/04_early_atmosphere.py --step-years 900000000
python3 Aeron/code/world_building/05_surface_temperature.py
python3 Aeron/code/world_building/05_surface_temperature.py --step-years 900000000
python3 Aeron/code/world_building/06_proto_tectonics.py
python3 Aeron/code/world_building/06_proto_tectonics.py --surface-grid-resolution 96x48
python3 Aeron/code/world_building/06_proto_tectonics.py --step-years 900000000
python3 Aeron/code/world_building/07_plate_system.py
python3 Aeron/code/world_building/07_plate_system.py --step-years 900000000
python3 Aeron/code/world_building/08_large_scale_topography.py
python3 Aeron/code/world_building/08_large_scale_topography.py --step-years 900000000
python3 Aeron/code/world_building/09_volcanic_impact_resurfacing.py
python3 Aeron/code/world_building/09_volcanic_impact_resurfacing.py --step-years 900000000
python3 Aeron/code/world_building/10_basic_regolith_weathering.py
python3 Aeron/code/world_building/10_basic_regolith_weathering.py --step-years 900000000
python3 Aeron/code/world_building/11_hydrology_before_life.py
python3 Aeron/code/world_building/11_hydrology_before_life.py --step-years 900000000
```

## Current Rules

- The simulation span is fixed at `5.4` billion years from planetary formation to today.
- `--step-years` must evenly divide the full simulation duration so the loop stays fixed-step.
- Internal calculations use exact deterministic scaling relations and then round only for display, so prose-rounded canon values can remain human-readable while the present-day simulated state still lands exactly on today's canon.
- Each script prints input criteria first, then one time-series row per iteration, then a present-world summary for the final state of that layer, and also writes its JSON, PNGs, and any sidecar geometry/state files into `Aeron/mapping/NN_layer_name/`.
- `01_planet.py` always writes `Aeron/mapping/01_planet/radius_growth.png` and, unless `--no-plot-radius-quadrant` is passed, also writes `Aeron/mapping/01_planet/radius_quadrant_time_linear.png` and `Aeron/mapping/01_planet/radius_quadrant_radius_linear.png`.
- `02_interior.py` always writes `Aeron/mapping/02_interior/cutaway_present.png` in addition to its existing JSON export and default interior-layer charts.
- `03_primary_crust.py` always writes `Aeron/mapping/03_primary_crust/zonal_solidification.png`.
- `05_surface_temperature.py` always writes `Aeron/mapping/05_surface_temperature/zonal_bands.png`.
- `06_proto_tectonics.py` always writes `Aeron/mapping/06_proto_tectonics/surface_fields.png` and supports `--surface-grid-resolution` for deterministic coarse-grid density.
- `02_interior.py` uses `01_planet.py` as a library and advances both layers together on the same timestep so the thermal model follows Aeron's changing bulk state.
- `03_primary_crust.py` uses `02_interior.py` as a library, which in turn uses `01_planet.py`, so the crustal-lid model stays coupled to Aeron's changing bulk and thermal state.
- `04_early_atmosphere.py` uses `03_primary_crust.py` as a library, which in turn uses `02_interior.py` and `01_planet.py`, so volatile accumulation stays coupled to Aeron's structural and thermal evolution.
- `05_surface_temperature.py` uses `04_early_atmosphere.py` as a library, which in turn uses `03_primary_crust.py`, `02_interior.py`, and `01_planet.py`, so the thermal regime stays coupled to Aeron's atmospheric, crustal, and interior history.
- `06_proto_tectonics.py` uses `05_surface_temperature.py` as a library, which in turn uses the atmosphere, crust, interior, and bulk-planet layers, so proto-plate behavior only appears once the earlier physical prerequisites are already in place.
- Up to and including `05_surface_temperature.py`, custom surface visuals should remain global, radial, or zonal unless a layer truly computes longitude-resolved structure.
- Starting in `06_proto_tectonics.py`, the pipeline may use a deterministic coarse surface grid for map-like visuals, and later layers should build on that shared spatial substrate rather than inventing unrelated geometry.
- `07_plate_system.py` uses `06_proto_tectonics.py` as a library, which in turn uses all earlier layers, so discrete plate motions only emerge after the lithosphere, atmosphere, crust, and thermal regime have already crossed the required thresholds.
- `08_large_scale_topography.py` uses `07_plate_system.py` as a library, deterministically subdivides the authoritative coarse tectonic mesh into the first refined terrain mesh, and only then computes first-order relief.
- `09_volcanic_impact_resurfacing.py` uses `08_large_scale_topography.py` as a library and mutates that inherited refined terrain mesh rather than regenerating geometry.
- `10_basic_regolith_weathering.py` uses `09_volcanic_impact_resurfacing.py` as a library, keeps the same refined terrain mesh, and only adds regolith and weathering fields on top of it.
- `11_hydrology_before_life.py` uses `10_basic_regolith_weathering.py` as a library, keeps the same refined terrain mesh, and computes water routing from inherited refined elevation rather than from abstract scalars alone.
