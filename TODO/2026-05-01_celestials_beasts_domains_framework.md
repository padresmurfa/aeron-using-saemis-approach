# TODO: Mythic Hierarchy and Cosmological Tier Framework

**Created:** 2026-05-01T00:00:00Z
**Revised:** 2026-05-02 (folded in user design direction; supersedes the original "five framework options" framing).

## Context

Aeron's mythic hierarchy needs a unified framework spanning **Creator -> mortals**. The user has provided design direction that fixes the tier structure, the gaze-resolution mechanic for legendary beasts and gods, and the above-physics rule. Existing definitions at every tier are now treated as drafts to be improved -- except for the hard canon listed below.

### User design direction (2026-05-02)

**Geometry.** Aeron is geocentric but **round**, not flat. Sun, moons, celestials (planet-like), stars, constellations, and galaxies all rotate around Aeron. The same sky is **not** visible everywhere on Aeron at the same time; visibility is positional. Celestials are universal as entities but positional as observed phenomena.

**Above-physics rule.** Celestials mostly follow fixed paths but are above physics. They can deviate in ways that would be impossible in our world. **Rarity of deviation scales with the scale of the entity.** (Open question: does *scale* mean physical size, metaphysical seniority, or both? See open questions below.)

**Tier mapping (top-down "directness to the Creator").**

| Tier | Class | Represents | Status |
| --- | --- | --- | --- |
| 1 | Creator (`Aru`/`Loran`) | The Source. `Loran` is `Aru` after the First Pulse, in oscillating harmonic state -- not a second being. | Hard canon. |
| 2 | Moons (`Seravel`) | Raw powers most directly derived from the Creator. | Existing names locked; tier role and domains open to refinement. |
| 3 | Celestials (planet-like bodies in the sky) | Primal forces between moons and gods. | Open: not yet catalogued. |
| 4 | Galaxies and patterns within them | Pantheons and individual gods within those pantheons. | Open: not yet catalogued. |
| 5 | Constellations (`Tavirath`) | **Legendary beasts.** Each constellation is a beast. | Names like `Phaemorath`, `Taviron` exist as doctrine; full beast catalog is empty. |
| -- | Stars (`Taviloren`) | **Lexical witness tier (transverse, not stacked).** Every primal-language word has a corresponding star; the sky is the visible lexicon of creation. | Hard canon (per `astrology/stars.md` and `astrology/primal_stars.md`). |
| 6 | Aeron's inhabitants | Humanic, demonic, mundane races, monsters, magic, heroes, demi-gods, angels, spirits. | Mostly open. |

Stars are not a "rank" between tiers 5 and 6; they are a **transverse witness tier** that accompanies the entire stack. A moon-tier word will have a moon-tier star; a god-tier word will have a god-tier star; and so on.

**Gaze-resolution mechanic** (legendary beasts at tier 5; the user has confirmed the same mechanic applies to galaxies/gods at tier 4).

- A humanic/demonic viewer glancing at a constellation sees the faint outline of the beast. These outlines are not imaginary lines; they have no real-world equivalent.
- Resolution increases with: time spent focusing, viewer's mana, and the viewer's attunement to the beast's aspects.
- At the highest mortal level, a fully attuned viewer with sufficient mana focuses and sees the beast as if watching from above and afar, **positioned between the viewer and the constellation**, with detail down to the slightest movement.
- The beast is **aware** of being gazed upon. Depending on the strength of the connection, the beast can interact with the viewer.
- Each legendary beast is visually distinct, with form derived from its primal powers.

**Existing definitions are not set in stone.** The user has explicitly invited better patterns and definitions at every tier between Creator and inhabitants, especially for legendary beasts.

### Hard canon that must not be broken

- Aeron is geocentric but round. The sky rotates around Aeron and visibility is positional.
- `Solaryth` and `Nyxorys` counter-orbit Aeron every 24 hours in permanent diametric opposition. Both are `Taviran` (luminaries), not moons.
- The seven `Seravel` (moons) orbit Aeron. Existing primal-language headwords for them are locked.
- `Loran` is not a second being. `Loran` is `Aru` after `Orun` (the First Pulse), the same singular Creator in dynamic oscillation. The Aru/Loran polarity is **not** good-vs-evil; the canon explicitly rejects ethical opposition there.
- Constellations are `Tavirath`: lawful patterns of relation and memory.
- Every primal-language word has a corresponding `Taviloren` (star). Stars are not ornamental.
- Every named entity must have a primal-language headword. After first introduction, prefer the primal name alone or `PrimalWord (English gloss)`.
- Existing canon files in `Aeron/mythopedia/cosmology/` and `Aeron/mythopedia/astrology/` cannot be silently contradicted; revisions must be routed through `team-aeron-narrative`.

### What is open and needs design work

- **Tier 2 (moons):** existing domain catalog is partial and largely planet-era flavored. Needs reframing as "raw Creator-derived powers" rather than as elemental matrix.
- **Tier 3 (celestials/planets):** the celestial layer between moons and gods is not yet populated. What primal forces does it host? How many bodies? How do they relate to moons (above) and to gods (below)?
- **Tier 4 (galaxies/pantheons):** how many pantheons? Are pantheons structurally similar across continents (single mother-pattern) or distinct (each continent's pantheon is its own galaxy)? How are individual gods identified within a galaxy's "patterns"?
- **Tier 5 (legendary beasts):** the constellation catalog is empty. Needs: enumeration, primal-language naming, aspect/domain assignment, visual identity rules, gaze-mechanic specifics, awareness/interaction rules.
- **Tier 6 (mortals):** humanic/demonic split has been used twice by the user but has no canonical origin. Where does the demonic side come from, given that neither Aru/Loran nor Solaryth/Nyxorys is a moral axis? Mundane races, monsters, heroes, angels, spirits, demi-gods, magic-as-substance all need slotted roles.
- **Cross-cutting: above-physics deviation rules.** When does a celestial deviate? What in-world causes it? What does deviation look like at each tier?

### What is explicitly out of scope

- Extending the world-building simulator (`Aeron/code/world_building/`).
- Changing the geocentric reference frame.
- Splitting `Loran` from `Aru` into separate beings.
- Renaming existing primal-language headwords for moons, luminaries, constellations, or stars.

## Open questions for the user

These need answers (or explicit "specialists decide") before the next routing step:

1. **Above-physics scaling** -- does *scale* mean: (a) physical size (galaxy > celestial > moon), (b) metaphysical seniority (closer to Creator = rarer deviation), or (c) both, with the scaling rule TBD? An example for each tier (one canonical deviation event per tier) would lock this.
2. **Universal-vs-positional seam below celestials.** Celestials are universal but positional. Below them: are pantheons (galaxies) universal-but-positional too, or is each continent's pantheon a different galaxy in the sky? Are legendary beasts universal but seen from different angles, or does each continent inherit a different sky-slice that gives them different beasts?
3. **Origin of humanic/demonic.** With Aru/Loran and Solaryth/Nyxorys both confirmed non-moral, where does the moral split that produces "humanic" vs "demonic" come from? Three plausible origins: (a) at the pantheon tier (some pantheons are demonic, some humanic); (b) at the legendary-beast tier (some beasts are demonic in nature); (c) at the mortal tier (the split is a mortal-only categorization, not a cosmic one).
4. **Mana / magic.** Referenced by the gaze mechanic but undefined. Is mana its own substance/tier, or transverse like stars (every tier has a mana correspondence)? Specialists will need a one-line position before drafting beast-interaction rules.
5. **Calendar timescales by tier.** Existing canon: 24-hour day for `Solaryth`/`Nyxorys`; 28-day cycle for `Serenel`/`Seramor`; 3/5/8/9/15-month cycles for the secondary moons. What are the natural timescales for celestials (annual?), galaxies (epochal?), constellations (generational?)? Some tiers may not have rotational cycles in the conventional sense.
6. **Star-tier transversality detail.** If every primal-language word has a star, do *higher tiers* (gods, beasts) each have their own star bearing their own name? Existing canon supports this (foundational words = brighter stars), but it needs to be restated within the new tier framework.

## Checklist

Each step names the LP routing that should run when that step is taken. Specialists are not invoked until the user confirms the open questions or explicitly delegates them. Each substantive step requires Devil's Advocate per LP rules.

- [ ] **Step 1 -- Resolve open questions.** User answers (or delegates) the six items above. LP synthesizes the answers into the framework before any specialist routing. *(LP-side, no specialist routing.)*

- [ ] **Step 2 -- Draft the unifying tier-framework canon page.** Produce `Aeron/mythopedia/cosmology/mythic_hierarchy.md` (or equivalent path) that codifies: tier table, above-physics rule, gaze-resolution mechanic, star-tier transversality, hard-canon list, and where the universal-vs-positional seam falls. This is the keystone document; everything below depends on it.
  - Route: `team-aeron-narrative` with mandatory `role-aeron-narrative-astrologer` overlay.
  - Devil's Advocate must stress-test against the open questions and the hard canon.

- [ ] **Step 3 -- Refine moon canon (tier 2).** Reframe `Aeron/mythopedia/astrology/moons_of_aeron.md` from "balanced elemental matrix" toward "raw Creator-derived powers." Keep all primal-language names; revisit domains if the new framework demands it. Audit each celestial saga in `Aeron/sagas/celestials/` for the seven moons.
  - Route: `team-aeron-narrative` + `role-aeron-narrative-astrologer` + `role-aeron-narrative-mythopedia-consistency-editor`.

- [ ] **Step 4 -- Define celestial (planet-like) tier 3.** Decide what bodies populate this tier. Coin primal-language names with `team-aeron-primal-language`. Define what "primal forces between moons and gods" means concretely (one paragraph per body).
  - Route: `team-aeron-narrative` + `role-aeron-narrative-astrologer` + `team-aeron-primal-language`.

- [ ] **Step 5 -- Define galaxy / pantheon tier 4.** Decide pantheon structure: how many pantheons; whether they share a common skeleton; what "patterns within a galaxy" means for individual god identification; how gaze-resolution works on gods. Hold off on naming individual gods until the structural rule is set.
  - Route: `team-aeron-narrative` + `role-aeron-narrative-astrologer`.

- [ ] **Step 6 -- Draft the legendary beast catalog (tier 5).** Produce the first cohort of legendary beasts -- recommended starting size: seven beasts, enough to populate distinct visual identities and aspect domains without overcommitting. Each beast needs: primal-language headword, constellation it occupies, aspects/domains, visual rules from primal powers, gaze-resolution specifics, awareness/interaction rules, and a one-paragraph mythic role.
  - Route: `team-aeron-narrative` + `role-aeron-narrative-astrologer` + `team-aeron-primal-language` + `role-aeron-narrative-mythopedia-consistency-editor`.
  - Output home: `Aeron/mythopedia/legendary_beasts/` (new directory) and primal-language entries under `Aeron/primal_language/structural_principles/`.

- [ ] **Step 7 -- Slot the mortal tier (tier 6).** Sketch the slots: monsters, magic-as-substance, gods (if any are mortal-bound rather than galaxy-bound), demi-gods, pantheons (if continent-local), angels, heroes, spirits, mundane races (humanic, demonic, others). For each slot, mark: where it inherits from above; whether it is universal or continent-local; one-paragraph intent. Do not populate; just slot.
  - Route: `team-aeron-narrative` + `role-aeron-narrative-astrologer`.

- [ ] **Step 8 -- Reconcile existing celestial sagas with the new framework.** Audit the eleven existing celestial sagas under `Aeron/sagas/celestials/` for contradictions with the unified tier framework. Flag and rewrite where needed.
  - Route: `role-aeron-narrative-mythopedia-consistency-editor` audits; `team-aeron-narrative` rewrites.

- [ ] **Step 9 -- Update mythopedia indexes.** Update READMEs across `Aeron/mythopedia/cosmology/`, `Aeron/mythopedia/astrology/`, and any new directories so cross-links reflect the new tier framework.
  - Route: `team-documentation` reviews after `team-aeron-narrative` drafts.

## Additional Notes

- **Sequencing rationale.** Step 1 (resolve open questions) is now the keystone. Step 2 produces the unifying canon page that every later step depends on. Steps 3-7 walk the tiers top-down (the user's "top-down" requirement). Step 8 reconciles legacy content. Step 9 fixes indexes.
- **Devil's Advocate red flags.**
  - Any framework that contradicts the Aru/Loran identity (treating Loran as a separate being) breaks hard canon.
  - Any framework that places stars *between* moons and constellations as a power tier (rather than as a transverse lexical tier) breaks `astrology/stars.md`.
  - Any framework that lets one continent claim exclusive ownership of a celestial breaks the geocentric universality (a celestial may be unseen from one continent at a given time but is not absent).
  - "Humanic/demonic" must not be smuggled back into the Aru/Loran or Solaryth/Nyxorys axis as moral content -- those are explicitly non-moral.
  - "Above physics" must not become a license for arbitrary deviation; the rule needs scaling, frequency, and consequence rules so it stays narratively coherent.
- **Future follow-ups, intentionally not in this TODO.**
  - Continent-by-continent pantheon canon (gated to follow steps 5 and 7).
  - Magic / mana system canonization (gated to follow open question 4).
  - A possible `12_celestial_clockwork.py` simulator layer if the framework eventually wants deterministic moon, constellation, and galaxy positions over time. **Currently deprioritized per user.**

## References

### Hard canon
- `Aeron/mythopedia/cosmology/aeron.md` -- geocentric world frame
- `Aeron/mythopedia/cosmology/divine_oscillation.md` -- `Loran` as oscillating `Aru`
- `Aeron/mythopedia/entities/aru.md`, `Aeron/mythopedia/entities/loran.md` -- Creator identity
- `Aeron/mythopedia/astrology/luminaries.md` -- `Solaryth`/`Nyxorys`
- `Aeron/mythopedia/astrology/stars.md`, `Aeron/mythopedia/astrology/primal_stars.md` -- star-as-lexical-witness doctrine
- `Aeron/mythopedia/astrology/moons_of_aeron.md` -- the seven `Seravel`
- `Aeron/mythopedia/astrology/constellations.md` -- `Tavirath` doctrine

### Existing partial content
- `Aeron/sagas/celestials/` -- saga prose for eleven celestial beings
- `Aeron/primal_language/structural_principles/` -- primal-language headwords
- `Aeron/mythopedia/events/first_pulse.md` -- `Orun` event
- `Aeron/mythopedia/cosmology/divine_oscillation.md`

### Prior specialist work
- `REPORTS/team-aeron-narrative/20260329_celestial_enrichment_report.md`
- `REPORTS/team-aeron-narrative/20260329_astrology_review_report.md`
- `REPORTS/team-aeron-narrative/20260328_primal_language_alignment_report.md`
