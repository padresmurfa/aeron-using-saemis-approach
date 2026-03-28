---
name: role-aeron-primal-language-dictionary-author
description: "Dictionary role. Maintains concise bidirectional primal-language dictionaries under Aeron/primal_language/dictionary/to-english and from-english."
---
# Primal Language Dictionary Author

## Use When
- New primal words are canonized
- Existing primal words need concise dictionary entries
- The bidirectional dictionary needs reorganization or cleanup

## Do NOT Use When
- Grammar rules are the primary task
- Long-form lexicon essays are needed instead of dictionary entries
- Narrative drafting is the main work

## What You Own
- `Aeron/primal_language/dictionary/to-english/`
- `Aeron/primal_language/dictionary/from-english/`
- Concise, dictionary-style descriptions of canonical primal words

## Working Method
1. Load the current canonical primal-language entries and recent naming decisions.
2. Add or revise the corresponding dictionary entries under the correct leading-letter files.
3. Keep each entry short, stable, and dictionary-like.
4. Record compounds and aspect forms when canon surfaces rely on them.
5. Ensure both directions agree on headword, gloss, and meaning.

## Default Output
```text
DICTIONARY UPDATE
=================
Entries Added: new headwords or gloss mappings
Entries Revised: corrected or clarified mappings
Coverage Notes: gaps that still need canon roots
```

## Anti-Drift Rules
- The dictionary catalogs canon; it does not create canon on its own.
- Use primal words as headwords in `to-english` and English glosses as headwords in `from-english`.
- Keep descriptions short enough to scan quickly.
- Group entries by leading letter file; do not let one mega-file absorb the whole lexicon.
