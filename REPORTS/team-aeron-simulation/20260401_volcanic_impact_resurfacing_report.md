# Simulation Team Report

SIMULATION TEAM REPORT
======================

Scope: implement the volcanic and impact resurfacing layer on top of `large_scale_topography.py`

Reality Inputs:
- `large_scale_topography.py` remains the source of first-order relief provinces and tectonic structure over time.
- The new layer must derive hotspot activity, flood basalt provinces, volcanic province coverage, crater formation and retention, resurfacing rate, and old-crust survival from that evolving base state.
- The output must stay deterministic and make Aeron's ancient scarred surface legible before later erosion, drainage, and landscape-aging work begins.

Implementation:
- Added `Aeron/code/world_building/volcanic_impact_resurfacing.py` as a coupled simulation that imports and ticks `large_scale_topography.py`, which in turn depends on the full earlier planetary stack.
- The script now reports hotspot count and activity, flood basalt event count and intensity, volcanic province fraction, major crater formation rate, crater persistence, resurfacing fraction and rate, old crust survival, and a present-day resurfacing feature table.
- The script prints criteria first, one row per iteration, and then a present-day summary plus feature-level resurfacing results.

Escalations:
- Stochastic impact histories, exact lava-flow extents, and crater-by-crater catalogs remain out of scope for this layer.
- Later erosion and crust-age mapping should consume `volcanic_impact_resurfacing.py` rather than re-deriving first-order resurfacing from scratch.

Verdict: Accept. The volcanic and impact resurfacing layer now exists as a deterministic follow-up to large-scale topography and the full earlier world-building stack.
