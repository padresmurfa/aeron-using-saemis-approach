# Reality Team Report

REALITY TEAM REPORT
===================

Scope: define the next layer after bulk planetary evolution: interior structure and thermal evolution

Domain Truth:
- This layer must be coupled to `planet.py`, because Aeron's mass, radius, and total heat budget change over time under the expanding-world model.
- The layer should answer whether Aeron cools into a differentiated, convecting rocky world capable of later tectonics rather than only listing bulk scalar properties.
- The required outputs at this layer are cooling state, solidification state, formation of core, mantle, and primordial crust, convection potential, and a heat-source split across residual formation heat, radioactive decay, and low-amplitude tidal heating.

Canonical Boundaries:
- The first-pass model may use coarse deterministic thermal-shape functions so long as it does not pretend to lock isotope inventories, full rheology, or high-resolution geodynamics.
- Tidal heating should remain secondary. It may contribute, but it must not replace interior heat as the primary engine of later tectonics.
- This layer exists to establish whether Aeron is thermally alive enough for later tectonics, not yet to simulate plate motion itself.

Simulation Handoff:
- Build a separate interior-thermal simulation that imports and ticks `planet.py`.
- Report both the time-series evolution and the present-day interior summary needed to judge tectonic readiness.

Verdict: Accept. The layer boundary is clear and ready for implementation.
