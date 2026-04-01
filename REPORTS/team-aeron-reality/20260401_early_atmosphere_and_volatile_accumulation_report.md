# Reality Team Report

REALITY TEAM REPORT
===================

Scope: define the early atmosphere and volatile accumulation layer that follows primary crust formation

Domain Truth:
- This layer must import and tick `primary_crust.py`, which itself depends on `interior.py` and `planet.py`, because volatile behavior depends on crust sealing, weak zones, internal outgassing, planetary retention, and surface state together.
- The layer should answer outgassing, gas retention or loss, pressure trends, broad atmospheric composition, rough greenhouse behavior, and whether liquid precipitation is possible at all.
- At this layer, the atmosphere should remain coarse and physically legible. The purpose is to know whether Aeron's surface is effectively lava, steam, naked rock, wet rock, ice, or a dry rocky world, not yet to run a full climate circulation model.

Canonical Boundaries:
- Atmospheric composition may remain broad and categorical rather than chemically exhaustive.
- Greenhouse intensity may remain a coarse index rather than a resolved radiative transfer calculation.
- Precipitation should be modeled as a phase-possibility question, not yet as a hydrological cycle or climate map.

Simulation Handoff:
- Build a separate atmospheric layer that imports and ticks `primary_crust.py`.
- Report both the time series and a present-day summary, including the first point at which liquid precipitation becomes possible.

Verdict: Accept. The layer boundary is clear and ready for implementation.
