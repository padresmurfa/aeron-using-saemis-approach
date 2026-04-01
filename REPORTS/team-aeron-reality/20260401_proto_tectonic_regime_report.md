# Reality Team Report

REALITY TEAM REPORT
===================

Scope: define the proto-tectonic regime layer that follows the surface temperature regime

Domain Truth:
- This layer must import and tick `surface_temperature.py`, which itself depends on the atmosphere, crust, interior, and bulk-planet layers, because the first meaningful fracture and plate-adjacent behavior depends on lid rigidity, surface liquids, crustal stability, and thermal stress together.
- The layer should answer whether the lithosphere is rigid enough to fracture, whether plates exist yet, whether the world is best described as stagnant-lid, episodic-overturn, or plate-like, and where the first major fracture, spreading, and recycling zones organize in broad planetary terms.
- This is the first layer where plate movement becomes meaningful, but it is still not yet a resolved tectonic-map simulation.

Canonical Boundaries:
- Zone locations may remain broad belt or margin patterns rather than exact coordinates.
- Plate existence may remain coarse and thresholded rather than requiring a full plate inventory.
- Recycling and spreading may remain proto-behavior classes rather than a full subduction and ridge mechanics model.

Simulation Handoff:
- Build a separate proto-tectonic layer that imports and ticks `surface_temperature.py`.
- Report both the time series and the present-day summary, including when fracture-capable lithosphere and plate-like behavior first appear.

Verdict: Accept. The layer boundary is clear and ready for implementation.
