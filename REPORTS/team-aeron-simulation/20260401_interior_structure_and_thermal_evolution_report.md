# Simulation Team Report

SIMULATION TEAM REPORT
======================

Scope: implement the interior structure and thermal evolution layer on top of `planet.py`

Reality Inputs:
- `planet.py` remains the source of bulk mass, radius, and internal heat budget over time.
- The new layer must derive cooling, solidification, differentiation, convection potential, and heat-source mix from that evolving base state.
- The output must stay deterministic and make tectonic readiness legible before continent-generation work begins.

Implementation:
- Added `Aeron/code/world_building/interior.py` as a coupled simulation that imports and ticks `planet.py` instead of re-implementing the bulk layer.
- The script now reports total internal heat, residual/radiogenic/tidal heat components, cooling index, solid fraction and state, core/mantle/primordial-crust formation fractions, convection index and state, and tectonic readiness.
- The script prints criteria first, one row per iteration, and then a present-day interior summary for the final state.

Escalations:
- Detailed radionuclide inventories, rheology, and full geodynamics remain out of scope for this first-pass thermal layer.
- Later tectonics work should consume `interior.py` rather than bypassing it.

Verdict: Accept. The interior layer now exists as a deterministic library-coupled follow-up to `planet.py`.
