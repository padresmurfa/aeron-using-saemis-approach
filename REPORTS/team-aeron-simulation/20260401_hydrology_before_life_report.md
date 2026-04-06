# Team Aeron Simulation Report: Hydrology Before Life Layer

Date: 2026-04-01
Team: `team-aeron-simulation`

## Scope

Implement the hydrology-before-life layer as the next deterministic simulation in the world-building chain.

## Implementation Guidance

- The layer must import and tick `basic_regolith_weathering.py`.
- It may also consult the already-coupled atmosphere, surface-temperature, and topography states to derive coarse hydrology.
- Outputs should include stable ocean fraction, inland sea fraction, glacier fraction, runoff pathway count, basin filling fraction, and a present-day hydrology feature table.
- The model should remain province-scale and deterministic rather than becoming a full fluid or circulation simulation.

## Follow-On Boundary

Detailed rivers, shoreline migration, erosion, drainage capture, sediment routing, ocean circulation, and climate-grid hydrology belong to later terrain and climate layers.
