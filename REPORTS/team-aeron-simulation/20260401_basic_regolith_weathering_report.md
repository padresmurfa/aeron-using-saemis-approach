# Team Aeron Simulation Report: Basic Regolith And Weathering Layer

Date: 2026-04-01
Team: `team-aeron-simulation`

## Scope

Implement the coarse regolith and weathering layer as the next deterministic simulation in the world-building chain.

## Implementation Guidance

- The layer must import and tick `volcanic_impact_resurfacing.py`.
- The model may consult the already-coupled atmosphere and surface-temperature state to gate dust transport and chemical weathering, but it should remain a coarse rules model.
- Outputs should include global fracture, dust, chemical weathering, talus, sediment, regolith coverage, regolith thickness, and exposed-bedrock metrics.
- The script should also emit a present-day terrain-texture table for the major resurfacing provinces so later terrain work inherits textured barren surfaces instead of featureless rock.
- The model must remain fixed-step, deterministic, and reproducible for any valid `--step-years` value.

## Follow-On Boundary

Detailed erosion, drainage integration, and true sediment routing belong to later terrain layers, not this one.
