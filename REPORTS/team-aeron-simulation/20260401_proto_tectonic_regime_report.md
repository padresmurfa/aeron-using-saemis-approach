# Simulation Team Report

SIMULATION TEAM REPORT
======================

Scope: implement the proto-tectonic regime layer on top of `surface_temperature.py`

Reality Inputs:
- `surface_temperature.py` remains the source of surface thermal band, surface-liquid state, crustal thermal stability, and thermal cycling over time.
- The new layer must derive lithosphere rigidity, fracture potential, plate mobility, regime classification, and broad fracture/spreading/recycling-zone organization from that evolving base state.
- The output must stay deterministic and make the first meaningful plate-adjacent regime legible before later tectonic-map and continent-generation work begins.

Implementation:
- Added `Aeron/code/world_building/proto_tectonics.py` as a coupled simulation that imports and ticks `surface_temperature.py`, which in turn depends on the atmosphere, crust, interior, and bulk-planet layers.
- The script now reports lithosphere rigidity, fracture potential, plate mobility, whether fracture is possible, whether plates exist yet, tectonic regime, and broad planetary patterns for major fractures, spreading zones, and recycling zones.
- The script prints criteria first, one row per iteration, and then a present-day summary that includes the first fracture-capable and first plate-like ages.

Escalations:
- A resolved plate inventory, geographic ridge map, subduction geometry, and continent shapes remain out of scope for this layer.
- Later tectonic and continental simulations should consume `proto_tectonics.py` rather than re-deriving first-order tectonic behavior from scratch.

Verdict: Accept. The proto-tectonic layer now exists as a deterministic follow-up to the surface temperature, atmosphere, crust, interior, and bulk-planet simulations.
