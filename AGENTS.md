# Herdr customizations

This repository is the source of truth for the personal Herdr layout, mods, themes, and sync tooling.
Read `../docs/decisions.md` and the installed `~/.config/herdr-app/AGENTS.md` before changing Herdr behavior.
Keep mockups, exploratory drafts, and personal notes in `../notes/`, outside this repository.
Edit source files here before syncing to the live Herdr configuration.
Use `python3 scripts/sync.py` to inspect drift and `python3 scripts/sync.py --apply` to publish local changes.
Never edit Herdr's generated files, its shipped mods, or its application-managed layout state.
Validate changed mods with `herdr-app check` and inspect the result in the app.
Maintain compatibility with Codex and Claude Code where the provider exposes reliable data.
Never push to a real remote or a default branch.
