# Reality Team Report

REALITY TEAM REPORT
===================

Scope: define the volcanic and impact resurfacing layer that follows large-scale topography generation

Domain Truth:
- This layer must import and tick `large_scale_topography.py`, because hotspots, flood basalts, crater retention, and resurfacing only make sense once tectonic relief provinces already exist.
- The layer should simulate hotspots, flood basalt events, volcanic provinces, crater formation and persistence, resurfacing rates, and how much old crust survives.
- At this layer, the barren world should begin to feel ancient and scarred rather than only structured.

Canonical Boundaries:
- Hotspots, trap provinces, and crater fields may remain province-scale rather than rasterized maps.
- Impacts may remain a deterministic time-decay flux rather than a stochastic bombardment catalog.
- Old-crust survival may remain a first-order surface-survival fraction rather than a full crustal-age grid.

Simulation Handoff:
- Build a separate resurfacing layer that imports and ticks `large_scale_topography.py`.
- Report both the time series and the present-day summary, including a present-day resurfacing feature table.

Verdict: Accept. The layer boundary is clear and ready for implementation.
