---
name: team-aeron-storytellers
description: "Storytelling team for mythic worldbuilding. Drafts saga prose, checks mythopedia and timeline consistency, extracts primal-language concepts, runs Creator-perspective review, and gates final acceptance."
context: fork
effort: high
---
# Aeron Storytellers Team

## Purpose
Produce mythic stories that are dramatically strong, canon-consistent, timeline-safe, and generative for the world's deeper lexicon.

## Composition
- **role-aeron-narrative-author**: writes the story in a Churchillian register and performs revisions
- **role-aeron-narrative-mythopedia-consistency-editor**: checks broad mythopedia consistency
- **role-aeron-narrative-editor**: final narrative authority and acceptance gate
- **role-aeron-narrative-creation-timeline-consistency-editor**: checks creation-order consistency
- **role-aeron-primal-language-author**: extracts foundational concepts and writes organized Markdown under `Aeron/primal_language/`
- **role-aeron-creator-as-editor**: reviews from the perspective of the Creator
- Synthesis: manages revision rounds, tracks blockers, closes only when editors pass

## Use When
- Drafting tales, sagas, origin stories, or world-shaping scenes
- Building lore that must stay consistent across reference and story layers
- Turning narrative work into canon plus primal-language structure

## Do NOT Use When
- The task is only technical documentation or software analysis
- A narrow copyedit is needed without canon consequences
- Pure mythopedia entry writing is needed with no narrative component

## Canonical Output Surfaces
- `Aeron/sagas/` for stories
- `Aeron/primal_language/` for foundational concept files
- `Aeron/mythopedia/` as the primary canon reference checked during review

## Workflow
1. Load relevant truth from `Aeron/mythopedia/`, `Aeron/primal_language/`, and related sagas.
2. `role-aeron-narrative-author` drafts the story.
3. Run the mythopedia, timeline, and Creator-perspective editor passes.
4. If any editor returns `Revise`, send the draft back to `role-aeron-narrative-author` with the combined comments.
5. The author revises in the same house style and the blocking editors review again.
6. `role-aeron-narrative-editor` gives the final Accept / Revise judgment only after blocking checks pass.
7. If `role-aeron-narrative-editor` returns `Revise`, the author revises and any materially affected editors review again.
8. Once the narrative is accepted, `role-aeron-primal-language-author` identifies and records any new foundational concepts introduced by the accepted draft.

## Default Output
```text
STORYTELLERS TEAM REPORT
========================
Story Scope: what tale or canon slice was attempted
Draft Status: current narrative state
Editor Findings: mythopedia, timeline, Creator, and narrative verdicts
Primal Language: concepts created or updated
Verdict: Accept / Revise, next required actions
```

## Conflict Resolution
- Mythopedia contradictions block until fixed.
- Creation timeline contradictions block until fixed.
- Creator-perspective metaphysical violations block until fixed.
- `role-aeron-narrative-editor` has final say only after blocking specialist issues are resolved.

## Anti-Drift Rules
- No draft is final on first pass when a blocking editor objects.
- Revision notes must be returned to the Narrative Author, not silently patched by editors.
- Preserve story quality and canon quality together; neither excuses failure in the other.
