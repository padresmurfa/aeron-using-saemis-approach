# Reality Team Report

REALITY TEAM REPORT
===================

Scope: define the primary crust formation layer that follows interior structure and thermal evolution

Domain Truth:
- This layer must import and tick `interior.py`, which itself ticks `planet.py`, because crust stability depends on Aeron's evolving radius, heat budget, cooling state, solid fraction, and primordial crust formation.
- The layer should answer the transition from molten world to solid world by reporting when the first stable crust appears, how thick that crust approximately becomes, what primary crust regime dominates, where weak zones persist, and whether the surface is mostly molten, mixed, or mostly solid.
- At this layer, the crust should be treated as a first-pass planetary lid, not yet as a full plate map or continent model.

Canonical Boundaries:
- The crust regime may be classified coarsely as `undifferentiated`, `oceanic_like`, or `continental_like`, but this layer should default to primary-lid realism rather than prematurely inventing continent-scale structure.
- Weak zones should be described as global or patterned fracture domains, proto-rifts, or mobile belts, not as exact geographic coordinates.
- Later tectonics and continent layers should inherit this crustal baseline rather than bypassing it.

Simulation Handoff:
- Build a separate primary crust simulation that imports and ticks `interior.py`.
- Report both the full time series and the present-day summary, including the first stable-crust appearance marker.

Verdict: Accept. The layer boundary is clear and ready for implementation.
