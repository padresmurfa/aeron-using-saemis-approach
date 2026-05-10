# TODO: Continent Canon (Foundation for Downstream Population)

**Created:** 2026-05-02T00:00:00Z
**Supersedes prior plan:** `2026-05-01_celestials_beasts_domains_framework.md` is fully landed; this is the next foundational dependency.

## Context

The mythic-hierarchy framework canon is fully landed (see prior TODO). Many tier-5 (Vorothar dwelling sites), tier-4 (pantheon-to-continent primary affiliation), and tier-6 (mortal-tier population per region) Canon Boundaries are gated on continent canon. This TODO opens that work.

## Design Direction (Locked in This TODO)

**Continent count: seven.** Not five (too few — would crowd Vorothar dwellings); not twelve (too many — would not afford each continent meaningful narrative weight). Seven gives an average of two `Vorothar` per continent and allows distinct climatic/cultural identities without redundancy.

**Naming convention.** Each continent's primal-language name extends an existing root family (no new roots are coined for continents themselves; `Athr-`, `Keth-`, `Mira-`, `Phae-`, `Sera-`, `Tav-`, `Orae-` all already established) with a continent-naming ending. Class headword: `Athralin` (continent; great-structural-extent).

**The seven continents** (working names; primal-language locked in this TODO):

| # | Primal | English Gloss | Character |
| --- | --- | --- | --- |
| 1 | `Athralorn` | The Heartland | Central, stable, multi-kingdom civilization |
| 2 | `Kethrarvel` | The Frostbound North | Northern, cold, fortified, frost-aspected |
| 3 | `Miravarath` | The Burning South | Southern, desert/volcanic, harsh |
| 4 | `Phaeravar` | The Eastern Ancient | Eastern, mythic, deeply-historied, exotic |
| 5 | `Seralinor` | The Sea-Threading | Archipelago/ocean-spanning, distinct from main landmasses |
| 6 | `Tavorath` | The High Crown | High-altitude, mountainous, sky-temple culture |
| 7 | `Oraevenel` | The Lost Verge | Small, liminal, half-mapped, dangerous |

**Vorothar dwelling distribution** (each continent hosts two Vorothar; locked in this TODO):

| Continent | Vorothar (1) | Vorothar (2) |
| --- | --- | --- |
| `Athralorn` | `Drathalon` (Colossus) | `Aelvorath` (Stormwing) |
| `Kethrarvel` | `Skaelmorath` (Wraith-Sovereign) | `Velkoraen` (Wyrm-Sire) |
| `Miravarath` | `Vorthalen` (Hellspawn-Sire) | `Khoramor` (Maw-Eternal) |
| `Phaeravar` | `Vothorisk` (Eldritch-Eye) | `Phaelvenor` (Swarm-Voice) |
| `Seralinor` | `Drovenrath` (Leviathan-Deep) | `Krevoraen` (Bloodborn-Sire) |
| `Tavorath` | `Mirathven` (Chimera-Mother) | `Vesselrath` (Plague-Mother) |
| `Oraevenel` | `Khaethorom` (Form-Thief) | `Athravenel` (Wild-Heart — the entire continent IS her body) |

**Pantheon-to-continent mapping is deferred.** Pantheons are universal entities; their primary worship-affiliation per continent will be set when pantheons are named (downstream).

## Hard Canon Constraints

- Continents are **not** equivalent to Aeron's tectonic plates; Aeron's plate-allocation is a planetary-physics concern (see `cosmology/aeron.md`), and continent canon is a mythopedia concern. The two layers run in parallel.
- Continents are universal as places (every continent exists for every Aeronian observer), continent-local in their inhabited content (different races, kingdoms, mage-orders, mythic traditions).
- The geocentric-round geometry of Aeron places continents on a globe, not a flat plane.
- No continent is "the canonical center" in mortal moral terms; `Athralorn`'s "Heartland" name is geographic, not hierarchical.
- Vorothar dwelling assignments are locked. Lesser-kin populations per continent are downstream.

## Steps

- [x] **Step C1 -- Foundation page and class word.** Produce `Aeron/mythopedia/places/continents.md` with the seven canonical continents, the structural rule for continent canon, the Vorothar dwelling distribution, the universal-vs-positional position. Coin `Athralin` (class headword for continent) at `Aeron/primal_language/structural_principles/athralin.md`.

- [x] **Step C2 -- Per-continent canon (7 entries).** One canon entry per continent at `Aeron/mythopedia/places/<primal_name>.md` covering: geographical character, climate/biome, cultural/civilizational families (sketched, not populated), hosted Vorothar, mythic role, prior-tier-defining historical events (sketched). Plus seven primal-language headwords at `Aeron/primal_language/structural_principles/<primal_name>.md`.

- [x] **Step C3 -- Wire dwelling-continent into each Vorothar canon entry.** Update `Aeron/mythopedia/legendary_beasts/<vorothar>.md` for all 14 Vorothar to specify dwelling-continent (replacing "(specific continent open canon)" placeholders).

- [x] **Step C4 -- Update mythopedia indexes.** Update `Aeron/mythopedia/places/README.md` and other relevant indexes to reflect the new continent canon.

- [x] **Step C5 -- Update AGENTS.md.** Add continent inventory to the orientation file.

## Routing

All steps route through `team-aeron-narrative` + `role-aeron-narrative-astrologer` (continents touch sky-aspect through gaze-resolution-by-region) + `team-aeron-primal-language` (one class headword + seven continent headwords) + `role-aeron-narrative-mythopedia-consistency-editor` (multiple existing canon files are edited).

Devil's Advocate must clear before acceptance.

## What This TODO Does Not Do

- **Pantheon naming and population.** Deferred to a separate TODO.
- **Lesser legendary beast catalog.** Deferred to a separate TODO; per-continent populations of lesser kin are downstream.
- **Per-continent kingdom/mage-order/civilization population.** Deferred to per-continent saga and history canon.
- **Continent-level tectonic/climate physics.** Lives in `cosmology/aeron.md` and the simulator track, not here.
- **Saga prose for continents.** Deferred to narrative work.
