# Agent Orientation

This file is for AI agents starting a session in this repository. Read it before doing work.

## What this repo is

Two related things live here:

1. **Aeron** — a top-down fantasy world under active construction. Lives in `Aeron/`. **This is the active project.**
2. **The Lead Producer skill pack** — the AI routing system this repo was forked from. Lives in `.claude/`. The 524-line `README.md` at repo root documents the pack, not Aeron.

If a request mentions worldbuilding, mythopedia, sagas, the simulator, primal language, or "the project," it means **Aeron**.

## How to start any task

Always invoke Lead Producer first:

```
/lead-producer <your task>
```

LP routes to specialist roles, teams, or workflows. Do not bypass it, even when the request looks like an obvious match for one specialist. See `.claude/CLAUDE.md` for the full host protocol and `.claude/skills/lead-producer/SKILL.md` for the canonical routing table.

## What Aeron is

Aeron is a created fantasy world being built **top-down** — from the Creator and the Big Bang downward toward mundane foliage and insects. The intended end-state is a complete fantasy setting suitable for short stories, light novels, novels, book series, manga, anime, tabletop RPGs, and single- and multi-player video games.

**North star:** myth and physics must align. The cosmology was created; everything that follows must be consistent with that act of creation.

**Core architectural constraint:** different continents may host entirely different mythic hierarchies — different pantheons, different gods, different demi-gods, different heroes, different mundane races. But **fundamental laws of reality are universal across the whole world**.

**Cosmological geometry.** Aeron is geocentric but **round** (see `Aeron/mythopedia/cosmology/aeron.md`). The sun, moons, celestials (planet-like bodies), stars, constellations, and galaxies all rotate around Aeron. The same sky is **not** visible everywhere on Aeron at the same time — visibility is positional. Celestials are universal as entities but positional as observed phenomena. They mostly follow fixed paths but are **above physics** and may deviate, with rarity scaling with the entity's scale.

**Tier framework (top-down, "directness from Creator").** The active design direction (see active plan) treats the mythic stack as:

1. Creator (`Aru`/`Loran`)
2. Moons (`Seravel`) — raw Creator-derived powers
3. Celestials (planet-like) — primal forces between moons and gods
4. Galaxies and patterns within them — pantheons and individual gods
5. Constellations (`Tavirath`) — legendary beasts (each constellation **is** a beast)
6. Aeron's inhabitants — humanic, demonic, mundane races, monsters, magic, heroes, demi-gods, angels, spirits

Stars (`Taviloren`) are a **transverse lexical witness tier**, not a rank between others — every primal-language word has a corresponding star (per `Aeron/mythopedia/astrology/stars.md`).

**Gaze-resolution mechanic.** Legendary beasts (and per the same rule, galaxies/gods) are seen as faint outlines by default. Resolution scales with the viewer's mana, attunement to the beast's aspects, and time spent focusing. At peak mortal attunement the viewer perceives the beast in full detail, positioned between viewer and constellation. The beast is aware of being gazed upon and may interact based on connection strength.

The intended mythic taxonomy at tier 6 includes: **monsters, magic, gods, demi-gods, pantheons, angels, heroes, spirits, mundane races**. Where the universal-vs-continent-specific seam falls inside the stack is open (see the active plan).

**Existing definitions are not set in stone.** Hard canon (geocentric round, `Aru`/`Loran` identity, primal-language conventions, every-word-has-a-star) is locked. Tier roles, domains, and content at every other level are open to refinement.

## Where things live

| Path | Contents |
|---|---|
| `Aeron/mythopedia/` | Canonical reference. `cosmology/` (era doctrine), `astrology/` (sky law), `entities/` (named beings), `events/`, `timeline/eras/`. |
| `Aeron/sagas/` | Narrative prose. `tales_of_creation/` (era stories), `celestials/` (named celestial beings). |
| `Aeron/primal_language/` | The invented primal language. `dictionary/`, `grammar/`, `era_names/`, `high_abstractions/`, `structural_principles/` (~115 root words), `threshold_events/`. |
| `Aeron/code/world_building/` | Deterministic Python simulator, layers `01_planet.py` through `11_hydrology_before_life.py`. **Side project. Currently deprioritized.** |
| `Aeron/mapping/` | Simulator output (PNG and JSON artifacts per layer). |
| `REPORTS/` | Specialist team reports, organized by team. **Read existing reports before re-deriving prior decisions.** |
| `TODO/` | Active TODOs. Use `TODO/TODO_TEMPLATE.md`; ISO-date the filename. See `whenupdating.md`. |
| `.claude/skills/` | LP pack skill content. Do not modify when working on Aeron. |
| `whenupdating.md` | Repo-maintenance checklist (LP-pack-facing). |

## Current scope and stuck points

**In scope right now:**
- Producing a unified tier-framework canon that codifies Creator → moons → celestials → galaxies/gods → constellations/legendary beasts → mortals.
- Resolving the open questions surfaced in the active plan (above-physics scaling rule, universal-vs-positional seam below celestials, origin of humanic/demonic, mana/magic placement, calendar timescales by tier, star-tier transversality detail).
- Improving definitions at every tier; the user has invited "better patterns and definitions at all levels," especially for legendary beasts.

**Deferred:**
- Extending the world-building simulator beyond `11_hydrology_before_life.py`.

See `TODO/2026-05-01_celestials_beasts_domains_framework.md` for the active plan and pre-decided routing for each step.

## Repo conventions

- **TODOs**: one Markdown file per TODO under `TODO/`, ISO date in filename, follow `TODO_TEMPLATE.md`. See `whenupdating.md` for full TODO requirements.
- **Reports**: live under `REPORTS/<team-name>/`, ISO-prefixed filenames (e.g. `20260501_topic_report.md`).
- **Primal-language usage**: every entity introduced should have a primal-language headword. After first introduction, prefer the primal name alone or `PrimalWord (English gloss)`, not the English gloss in isolation.
- **Canon boundaries**: most `mythopedia/*` documents end with a "Canon Boundaries" section that lists what is and is not yet canon. Respect them; don't silently expand canon without routing through `team-aeron-narrative`.
- **Geocentric frame**: `Aeron/mythopedia/cosmology/aeron.md` and `astrology/luminaries.md` define a geocentric sky. Any proposal that breaks this is a foundational canon revision and must be flagged.

## Branches

Active development for this orientation work happens on `claude/setup-fantasy-world-docs-iIKDJ`. Future feature branches should use the same `claude/<topic>-<id>` pattern when assigned.

## Quick links

- Active plan: `TODO/2026-05-01_celestials_beasts_domains_framework.md`
- LP host guide: `.claude/CLAUDE.md`
- LP routing canon: `.claude/skills/lead-producer/SKILL.md`
- Aeron geocentric reference: `Aeron/mythopedia/cosmology/aeron.md`
- Existing moon canon: `Aeron/mythopedia/astrology/moons_of_aeron.md`
- Existing constellation doctrine: `Aeron/mythopedia/astrology/constellations.md`
- Existing celestial beings: `Aeron/sagas/celestials/`
- Top-tier entities so far: `Aeron/mythopedia/entities/aru.md`, `Aeron/mythopedia/entities/loran.md`
