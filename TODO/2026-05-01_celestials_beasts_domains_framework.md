# TODO: Celestials, Legendary Beasts, and Mythic-Hierarchy Mapping Framework

**Created:** 2026-05-01T00:00:00Z

## Context

Aeron has rich celestial canon (seven `Seravel`, two `Taviran`, and a constellation doctrine) but the relationship between celestials and the rest of the mythic hierarchy is underspecified. The user's framing: "Somewhere along the line we have moons, celestials, and constellations. They need to map to something very significant. That's where the legendary beasts come in. But I don't know how to map them well, what domains they should cover, etc."

The full intended mythic taxonomy is: **monsters, magic, gods, demi-gods, pantheons, angels, heroes, spirits, mundane races**. Legendary beasts are a proposed bridge tier between celestials and the rest, but the *complete* tier structure also needs to be slotted.

### Three open architectural questions

1. **The mapping framework.** Five plausible options for celestial -> legendary beast relation, each with different downstream consequences. None pre-decided.
   - **A. 1:1 direct.** One legendary beast per celestial body (each moon, each luminary, each named constellation has one beast).
   - **B. Domain-based.** Celestials define domains (forge, dream, oath, secret-passage, etc.); legendary beasts embody domains. Multiple beasts can share a celestial's domain refracted through different cultures.
   - **C. Hierarchical emanation.** Beasts are aspects or emanations of celestials. Continents see different beasts that all derive from the same celestial principle.
   - **D. Constellation-as-zodiac.** Constellations *are* the legendary-beast catalog (real-world zodiac analogue). Moons remain forces, not beasts. Luminaries remain a separate axis.
   - **E. Layered.** Moons = forces, luminaries = primary axis, constellations = beast catalog with cross-references; legendary beasts live on the constellation tier and inherit moon-domain influence.

2. **Domains.** What domains should legendary beasts cover? Existing partial moon-domain canon (from `Aeron/mythopedia/astrology/moons_of_aeron.md`):
   - `Tavrekal` (Ash Moon): fire and forge
   - `Taviril` (Blue Moon): air, distance, far sight
   - `Kethorel` (Iron Moon): earth, oath, war-metal
   - `Oraemor` (Pale Moon): threshold, dream, ruin-memory
   - `Serathil` (Veiled Moon): secrets, masked passage, spirit crossing
   - `Serenel`/`Seramor`: water axis (light/depth)
   - `Solaryth`/`Nyxorys`: light/darklight axis (luminaries, not moons)

   Constellation domains are not yet defined. The `mythopedia/astrology/constellations.md` page is doctrinal only and explicitly notes: "Named planet-era constellations, zodiacal houses, and their divisions are not yet canonized." That catalog is empty.

3. **Universal vs continent-specific seam.** Aeron is geocentric (per `cosmology/aeron.md`); every continent sees the same celestials. So:
   - Celestials are universal by construction.
   - The keystone question: where below celestials does the universal/continent-specific seam fall?
     - Seam above legendary beasts -> beasts are universal; gods/pantheons vary
     - Seam below legendary beasts -> each continent has its own legendary beasts that derive from shared celestials
     - Hybrid -> some legendary beasts are universal (cosmic), others are continent-specific (terrestrial)

### What is already decided and must not be broken

- Aeron is geocentric. `Solaryth` and `Nyxorys` counter-orbit Aeron every 24 hours in permanent opposition. The seven `Seravel` orbit Aeron.
- Constellations are `Tavirath`: lawful patterns of relation and memory, not arbitrary star pictures.
- The primary water axis (`Serenel`/`Seramor`) is the calendar backbone; other moons are dramatic, not apocalyptic.
- Every named entity must have a primal-language headword.
- Existing canon files in `Aeron/mythopedia/astrology/` and `Aeron/mythopedia/cosmology/` are authoritative.

### What is explicitly out of scope

- Extending the world-building simulator (`Aeron/code/world_building/`). Side project.
- Changing the geocentric reference frame.
- Renaming existing primal-language headwords for moons, luminaries, or constellations.

## Checklist

Each step names the LP routing that should run when that step is taken. Do not invoke specialists ahead of the step. Each substantive step requires Devil's Advocate per LP rules.

- [ ] **Step 1 -- Define the universal-vs-continent-specific seam.** This is the keystone decision. Until it is settled, every later step risks ratifying a framework that collapses. Produce a one-page canon doc that names which mythic tiers are universal across all continents and which are continent-local. Place under `Aeron/mythopedia/cosmology/` (likely `mythic_hierarchy.md`) or a new `Aeron/mythopedia/hierarchy/` directory.
  - Route: `team-aeron-narrative` with mandatory `role-aeron-narrative-astrologer` overlay (celestial work).
  - Devil's Advocate must stress-test: does the chosen seam admit demi-gods that span continents? does it allow a continent's pantheon to claim a celestial as exclusively theirs without breaking universality?

- [ ] **Step 2 -- Compare 3+ mapping framework options side-by-side.** Adapt `workflow-design-interface-options` to lore design. For each of options A--E (or others surfaced during step 1), produce: what it canonizes, what it forecloses, narrative payoff, naming-language load, integration cost with existing canon, reversibility.
  - Route: `workflow-design-interface-options` orchestrated by LP, executed by `team-aeron-narrative` + `role-aeron-narrative-astrologer`.
  - Output: a comparison report under `REPORTS/team-aeron-narrative/`.

- [ ] **Step 3 -- Choose and ratify the framework.** User decision after reviewing step 2. LP synthesizes; `team-aeron-narrative` writes the canon page (likely `Aeron/mythopedia/astrology/celestial_beast_framework.md` or similar). Devil's Advocate must stress-test before acceptance.

- [ ] **Step 4 -- Catalog domains.** Once the framework is chosen, complete the domain catalog:
  - Confirm and refine the seven moon domains.
  - Define a starter set of constellation domains (zodiacal houses or `Phaemorath`/`Taviron` subdivisions, depending on framework).
  - If the framework introduces cross-celestial domains (combinations of moon plus constellation, etc.), define those too.
  - Route: `role-aeron-narrative-astrologer` owns drafting; `team-aeron-primal-language` reviews any new domain names for root-family coherence.

- [ ] **Step 5 -- First pass at legendary beasts.** Draft the first three to seven legendary beasts under the chosen framework, each with primal-language headword, domain, celestial relation, and a one-paragraph mythic role.
  - Route: `team-aeron-narrative` drafts; `team-aeron-primal-language` coins or reviews names; `role-aeron-narrative-mythopedia-consistency-editor` checks against existing canon.
  - Output: new files under `Aeron/mythopedia/entities/` (or a new `Aeron/mythopedia/legendary_beasts/` directory if the framework warrants its own home), plus optional saga prose under `Aeron/sagas/`.

- [ ] **Step 6 -- Sketch the full tier structure.** Even if not fully populated, produce a single page that slots every intended tier: monsters, magic, gods, demi-gods, pantheons, angels, heroes, spirits, mundane races. For each tier, mark: universal / continent-specific / hybrid; relation to celestials; one paragraph of intent.
  - Route: `team-aeron-narrative` with `role-aeron-narrative-astrologer` overlay. Treat as a structural canon page, not finished content.
  - This step is gated to follow step 1 but should be at least sketched before step 3 ratifies a framework, so the framework choice does not foreclose later tiers.

- [ ] **Step 7 -- Reconcile existing celestial sagas.** Audit the eleven existing celestial sagas under `Aeron/sagas/celestials/` (`kethorel`, `nyxorys`, `oraemor`, `phaemorath`, `seramor`, `serathil`, `serenel`, `solaryth`, `taviril`, `taviron`, `tavrekal`) for consistency with the new framework. Flag any contradictions; route corrections through `team-aeron-narrative`.
  - Route: `role-aeron-narrative-mythopedia-consistency-editor` audits; `team-aeron-narrative` rewrites where needed.

- [ ] **Step 8 -- Update mythopedia indexes.** Update `Aeron/mythopedia/astrology/README.md` and any new hierarchy/legendary-beast index README to point at the new canon, with cross-links into existing moon, luminary, and constellation pages.
  - Route: `team-documentation` reviews after `team-aeron-narrative` drafts.

## Additional Notes

- **Sequencing rationale.** Step 1 is a keystone: until the universal/continent-specific seam is set, every framework option in step 2 risks asking the wrong question. Step 6 is intentionally pulled forward as a "sketch" so the framework choice in step 3 does not paint downstream tiers into a corner.
- **Devil's Advocate red-flags to watch for.**
  - A framework that gives one continent exclusive ownership of a celestial breaks geocentric universality.
  - A framework where legendary beasts are continent-local but celestials are universal must explain *why* the same sky produces different beasts in different lands -- cultural refraction is one answer, but it needs to be canonical.
  - Any framework that requires the simulator to do new work is not viable right now (simulator is deprioritized).
- **Future follow-ups, intentionally not in this TODO.**
  - A `12_celestial_clockwork.py` simulator layer that emits deterministic moon and constellation positions over time, if step 4 produces precise enough orbital and zodiacal canon to drive it.
  - A `13_*` layer for biology and magic onset.
  - Continent-by-continent pantheon canon, gated to follow steps 1, 3, and 6.

## References

- `Aeron/mythopedia/cosmology/aeron.md` -- geocentric reference frame
- `Aeron/mythopedia/astrology/luminaries.md` -- `Solaryth` and `Nyxorys`
- `Aeron/mythopedia/astrology/moons_of_aeron.md` -- the seven `Seravel` and their domains
- `Aeron/mythopedia/astrology/constellations.md` -- `Tavirath` doctrine and the empty-catalog admission
- `Aeron/mythopedia/entities/` -- existing top-tier entities (`aru`, `loran`)
- `Aeron/sagas/celestials/` -- existing celestial saga prose for the eleven named celestials
- `Aeron/primal_language/structural_principles/` -- existing primal-language headwords for celestials
- `REPORTS/team-aeron-narrative/20260329_celestial_enrichment_report.md` -- prior celestial review
- `REPORTS/team-aeron-narrative/20260329_astrology_review_report.md` -- prior astrology review
