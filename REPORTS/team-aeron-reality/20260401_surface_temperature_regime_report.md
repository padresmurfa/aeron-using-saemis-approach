# Reality Team Report

REALITY TEAM REPORT
===================

Scope: define the surface temperature regime layer that follows early atmosphere and volatile accumulation

Domain Truth:
- This layer must import and tick `early_atmosphere.py`, which itself depends on the crust, interior, and bulk-planet layers, because broad surface temperature depends on atmospheric pressure, greenhouse loading, volatile state, and crustal stability together.
- The layer should answer average temperature band, coarse equator-to-pole thermal contrast, whether surface liquids can exist, whether crust remains thermally stable, and how much thermal cycling the surface experiences.
- The purpose of this layer is not to resolve full climate. It is to classify whether Aeron at a given time reads as hot volcanic rock, cold dead rock, dry wind-scoured rock, steam-shrouded rock, ice-rock, or a precipitation-bearing wet-rock world.

Canonical Boundaries:
- Temperature may remain coarse and derived from coupled surface-envelope states rather than from radiative transfer.
- Latitudinal contrast may remain a broad damping metric rather than a true circulation solution.
- Thermal cycling should remain a coarse surface-stress signal rather than a diurnal and seasonal climate model.

Simulation Handoff:
- Build a separate surface temperature layer that imports and ticks `early_atmosphere.py`.
- Report both the time series and the present-day summary, including the first point where surface liquids become thermally viable.

Verdict: Accept. The layer boundary is clear and ready for implementation.
