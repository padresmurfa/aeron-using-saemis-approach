# Simulation Team Report

SIMULATION TEAM REPORT
======================

Scope: implement the primary crust formation layer on top of `interior.py`

Reality Inputs:
- `interior.py` remains the source of cooling, solidification, convection, and primordial crust formation over time.
- The new layer must derive surface state, stable crust thickness, crust regime, and weak-zone behavior from that evolving interior state.
- The output must stay deterministic and make the ball-to-solid-world transition legible before tectonic and continent-generation work begins.

Implementation:
- Added `Aeron/code/world_building/primary_crust.py` as a coupled simulation that imports and ticks `interior.py`, which in turn imports and ticks `planet.py`.
- The script now reports gross crust thickness, stable crust thickness and fraction, stable crust state, crust regime, weak-zone fraction and pattern, surface solid index, and surface state.
- The script prints criteria first, one row per iteration, and then a present-day summary that includes the first stable-crust appearance age.

Escalations:
- Full plate boundaries, crustal recycling, continent emergence, and geographic maps remain out of scope for this layer.
- Later tectonics work should consume `primary_crust.py` rather than re-deriving primary crust from scratch.

Verdict: Accept. The primary crust layer now exists as a deterministic follow-up to the interior and bulk-planet simulations.
