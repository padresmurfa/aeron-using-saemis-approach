---
name: team-aeron-narrative
description: "Narrative team for mythic worldbuilding. Drafts saga prose, checks mythopedia, timeline, and celestial canon consistency, coordinates with the primal-language team, runs Creator-perspective review, and gates final acceptance."
context: fork
effort: high
---
# Aeron Narrative Team

## Purpose
Produce mythic stories that are dramatically strong, canon-consistent, timeline-safe, and ready for downstream primal-language canonization.

## Composition
- **role-aeron-narrative-author**: writes the story in a Churchillian register and performs revisions
- **role-aeron-narrative-mythopedia-consistency-editor**: checks broad mythopedia consistency
- **role-aeron-narrative-astrologer**: reviews celestial canon, omen doctrine, and astrology-facing sky law whenever stars, constellations, luminaries, moons, or related events are in scope
- **role-aeron-narrative-editor**: final narrative authority and acceptance gate
- **role-aeron-narrative-creation-timeline-consistency-editor**: checks creation-order consistency
- **role-aeron-narrative-timeline-author**: keeps era placement and timeline indexing aligned with canon
- **role-aeron-creator-as-editor**: reviews from the perspective of the Creator
- Synthesis: manages revision rounds, tracks blockers, closes only when editors pass

## Use When
- Drafting tales, sagas, origin stories, or world-shaping scenes
- Building lore that must stay consistent across reference and story layers
- Building celestial or astrology-facing lore that must stay consistent across cosmology, mythopedia, calendars, and omen systems
- Preparing narrative work for canon acceptance and primal-language follow-through

## Do NOT Use When
- The task is only technical documentation or software analysis
- A narrow copyedit is needed without canon consequences
- Primal-language grammar, dictionary, or lexicon work is the primary task

## Canonical Output Surfaces
- `Aeron/sagas/` for stories
- `Aeron/mythopedia/` as the primary canon reference checked during review
- `Aeron/mythopedia/astrology/` for celestial canon, omen doctrine, and astrology-facing sky law
- `Aeron/mythopedia/timeline/` for era indexing and sequence integrity

## Workflow
1. Load relevant truth from `Aeron/mythopedia/`, `Aeron/mythopedia/astrology/` when celestial topics are in scope, `Aeron/primal_language/`, and related sagas.
2. `role-aeron-narrative-author` drafts the story.
3. Run the mythopedia, timeline, and Creator-perspective editor passes.
4. If the task touches celestials or astrology, run `role-aeron-narrative-astrologer` and treat its blocking sky-canon findings like any other editorial blocker.
5. If any editor returns `Revise`, send the draft back to `role-aeron-narrative-author` with the combined comments.
6. The author revises in the same house style and the blocking editors review again.
7. `role-aeron-narrative-editor` gives the final Accept / Revise judgment only after blocking checks pass.
8. If `role-aeron-narrative-editor` returns `Revise`, the author revises and any materially affected editors review again.
9. When accepted narrative introduces or revises canon terms, hand the resulting story, mythopedia, and timeline surfaces to `team-aeron-primal-language` for lexicon, grammar, and dictionary work.
10. Apply any returned naming or first-introduction fixes before closing the package.
11. Before final acceptance, verify that every newly canonized foundational concept has a primal root, that reports explicitly list coined roots with English left in gloss position only, that prose does not refer to canonized parent concepts by English gloss alone where a primal headword exists, that celestial canon is aligned across cosmology and astrology surfaces, and that no pre-soul material imports rebellion-against-`Aru`/`Loran` or good-versus-evil framing.

## Default Output
```text
NARRATIVE TEAM REPORT
=====================
Story Scope: what tale or canon slice was attempted
Draft Status: current narrative state
Editor Findings: mythopedia, timeline, Creator, and narrative verdicts
Primal Language Follow-Through: required handoff or returned naming edits
Verdict: Accept / Revise, next required actions
```

## Conflict Resolution
- Mythopedia contradictions block until fixed.
- Creation timeline contradictions block until fixed.
- Celestial or astrology-facing contradictions block until fixed when sky canon is in scope.
- Creator-perspective metaphysical violations block until fixed.
- `role-aeron-narrative-editor` has final say only after blocking specialist issues are resolved.

## Anti-Drift Rules
- No draft is final on first pass when a blocking editor objects.
- Revision notes must be returned to the Narrative Author, not silently patched by editors.
- Preserve story quality and canon quality together; neither excuses failure in the other.
- If a concept has a primal-language root, saga, mythopedia, and timeline surfaces must introduce the primal term and English gloss together rather than letting English masquerade as the canon name.
- After first introduction, saga, mythopedia, and timeline surfaces should prefer the primal word alone or `PrimalWord (English gloss)`; English gloss by itself is reserved for explicit glossing, dictionary, or index contexts.
- Team reports must name newly coined roots explicitly and must not present English placeholder labels as the authoritative canon term.
- Do not accept sibling sections that read as structural clones of one another; repeated stock phrasing and recycled cadence are editorial defects, not mere preferences.
- Do not accept sibling sections built on repeated template openings, recycled sentence skeletons, or one-note cadence; that is an editorial defect, not a stylistic quirk.
- If grammar or dictionary issues are discovered during review, route them to `team-aeron-primal-language` rather than improvising silent naming drift inside the story pass.
- Do not accept any draft that frames `Aru`, `Loran`, or similarly fundamental cosmological orders as possible targets of rebellion; such language is metaphysically false in Aeron.
- Before soul-bearing ethics exists, reject framing that imports biblical fall patterns, Luciferic foreshadowing, or intrinsic good/evil struggle into the cosmology.
- Do not close celestial, astrological, or omen-bearing lore work until `role-aeron-narrative-astrologer` has reviewed it.
