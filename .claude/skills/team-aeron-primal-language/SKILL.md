---
name: team-aeron-primal-language
description: "Primal-language team for lexicon, grammar, and dictionary canon. Coins roots, maintains linguistic tendencies, catalogs entries, and pushes naming fixes back into saga, mythopedia, and timeline surfaces."
context: fork
effort: high
---
# Aeron Primal Language Team

## Purpose
Maintain Aeron's primal language as a living canon: coined roots, tracked grammatical tendencies, dictionary coverage, and consistent first introduction across the repo.

## Composition
- **role-aeron-primal-language-author**: coins or revises canonical roots and updates foundational lexicon files
- **role-aeron-primal-language-linguist**: maintains grammar guidance, root-family tendencies, and naming coherence
- **role-aeron-primal-language-dictionary-author**: catalogs primal words in concise dictionary form to and from English
- Synthesis: reconciles naming choices and returns blocking canon fixes when narrative or reference layers drift

## Use When
- Canon terms need primal-language roots
- Existing roots need grammar review or family alignment
- English-first cosmological labels need to be paired with primal canon terms
- The primal-language dictionary or grammar must be extended

## Do NOT Use When
- Primary work is story drafting
- Only a narrow prose edit is needed with no lexicon consequences
- No canon terminology is being introduced or revised

## Canonical Output Surfaces
- `Aeron/primal_language/` for canonical root files, grammar, and dictionary
- `Aeron/mythopedia/`, `Aeron/sagas/`, and `Aeron/mythopedia/timeline/` when first-introduction or naming fixes are required

## Workflow
1. Load the accepted or in-flight canon surfaces that introduce the concept.
2. `role-aeron-primal-language-author` identifies foundational concepts and proposes or revises primal roots.
3. `role-aeron-primal-language-linguist` reviews the proposals against current grammar tendencies, family resemblance, and naming drift.
4. If a proposed root fights the language too sharply, revise the form before canonizing it.
5. `role-aeron-primal-language-dictionary-author` records the accepted roots and approved compounds in the bidirectional dictionary.
6. Apply required naming or first-introduction fixes across saga, mythopedia, and timeline surfaces.
7. Close only when the root files, grammar notes, dictionary entries, and touched canon surfaces agree.

## Default Output
```text
PRIMAL LANGUAGE TEAM REPORT
===========================
Scope: concepts or terms reviewed
Roots: coined or revised canonical words
Grammar: tendencies affirmed, added, or corrected
Dictionary: entries added or updated
Verdict: Accept / Revise, next required actions
```

## Conflict Resolution
- Established canon meaning outranks aesthetic preference.
- Grammar tendencies guide naming, but they do not overrule metaphysical accuracy.
- Dictionary entries mirror canonized usage; they do not invent canon independently.

## Anti-Drift Rules
- English gloss is explanatory only; it is never the canonical primal headword.
- Once a primal headword is live, narrative surfaces should prefer the primal word alone or `PrimalWord (English gloss)`; English gloss by itself should be treated as a drift bug unless the context is explicitly dictionary-like.
- Grammar rules are tendencies, not algorithms, and should be trusted only when they describe at least half the living corpus.
- When a later specialization descends from an earlier root, preserve audible or visual family relation unless there is a strong reason not to.
- Compound forms must remain legible in their parts: primary root, quoted infix, and suffix.
- If a word is canonical enough to steer story, mythopedia, or timeline prose, it must be recorded in the dictionary.
