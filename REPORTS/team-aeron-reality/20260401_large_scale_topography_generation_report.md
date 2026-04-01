# Reality Team Report

REALITY TEAM REPORT
===================

Scope: define the large-scale topography generation layer that follows the plate-system simulation

Domain Truth:
- This layer must import and tick `plate_system.py`, because large-scale relief should only emerge once discrete plate regions, motions, and crustal creation and destruction rates already exist.
- The layer should generate first-order proto-continents, ocean basins, ridges, volcanic arcs, uplifts, rifts, highlands, and lowlands.
- At this layer, erosion is intentionally deferred. The purpose is to establish relief consequences of plate motion, not yet to smooth or dissect them.

Canonical Boundaries:
- Relief may be modeled as discrete topographic provinces rather than a resolved elevation raster.
- Ocean basins and proto-continents may remain first-order fractions and relief provinces rather than precise coastlines.
- Highlands and lowlands may overlap broader provinces so long as the first-order relief logic remains clear.

Simulation Handoff:
- Build a separate large-scale topography layer that imports and ticks `plate_system.py`.
- Report both the time series and the present-day summary, including a present-day feature table that later continental and drainage work can inherit.

Verdict: Accept. The layer boundary is clear and ready for implementation.
