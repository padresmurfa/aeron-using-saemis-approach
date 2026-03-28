# TODO: Populate Timeline Directory with Existing Events

**Created:** 2026-03-28T00:00:00Z

## Context
- The timeline structure has been created under `/Aeron/mythopedia/timeline/eras/` with folders for each major era and a `timeline.md` in each.
- A new role, `aeron-narrative-timeline-author`, is responsible for assigning events to eras and maintaining the ordered timeline.
- Existing mythopedia and saga content may contain events that need to be indexed in the timeline.

## Checklist
- [ ] Review all existing mythopedia and saga entries for events with temporal relevance
- [ ] Assign each event to the correct era folder
- [ ] Add each event to the appropriate `timeline.md` in ordered form
- [ ] Flag any ambiguous or unclear event timing for review
- [ ] Ensure timeline structure remains strictly ordered and non-duplicative

## Additional Notes
- See `/Aeron/mythopedia/timeline/eras/` for the timeline structure
- See `.claude/skills/role-aeron-narrative-timeline-author/SKILL.md` for the new role's responsibilities
